// Freeze the trial listing beside the published export, as stage-public-export.mjs
// freezes the export: GitHub builds from this file and never reads the private database.
// The listing is staged only if it matches its schema, is small enough to be one file,
// and names no claim the staged export does not publish.
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

// One file a reader's search fetches. Past this the listing is to be split by a rule the
// page can follow (openspec trial-pages); Cloudflare refuses a file over 25 MiB outright.
export const LISTING_LIMIT_BYTES = 8 * 1024 * 1024;

const [source, destination, exportFile] = process.argv.slice(2);
if (!source || !destination || !exportFile) {
  console.error("Usage: node stage-trials-listing.mjs SOURCE DESTINATION STAGED_EXPORT");
  process.exit(1);
}
let temporary;
try {
  const text = fs.readFileSync(source, "utf8");
  const listing = JSON.parse(text);
  const schemaFile = path.resolve(import.meta.dirname, "../trials-listing.schema.json");
  const ajv = new Ajv2020({ allErrors: false });
  addFormats(ajv);
  const validate = ajv.compile(JSON.parse(fs.readFileSync(schemaFile, "utf8")));
  if (!validate(listing)) {
    const [problem] = validate.errors ?? [];
    throw new Error(`The listing does not match trials-listing.schema.json: ${problem?.instancePath || "/"} ${problem?.message}`);
  }
  if (listing.trials.length === 0) throw new Error("The listing holds no trials. There is nothing to stage.");
  const compact = `${JSON.stringify(listing)}\n`;
  const size = Buffer.byteLength(compact);
  if (size > LISTING_LIMIT_BYTES) {
    throw new Error(`The listing is ${size.toLocaleString("en")} bytes, over the ${LISTING_LIMIT_BYTES.toLocaleString("en")} a single file may be. List a smaller set, or split it.`);
  }
  // Stale check: a listing written before or after another export names claims that
  // export does not publish. Write both again, together.
  const published = new Set(JSON.parse(fs.readFileSync(exportFile, "utf8")).claims.map((claim) => claim.slug));
  const claimAt = listing.columns.indexOf("claim");
  const unknown = [...new Set(listing.trials.map((row) => row[claimAt]).filter((slug) => slug && !published.has(slug)))];
  if (unknown.length) {
    throw new Error(`The listing names ${unknown.length} claim(s) the staged export does not publish (${unknown.slice(0, 3).join(", ")}${unknown.length > 3 ? ", …" : ""}). Write the export and the listing again together (make publish-data).`);
  }
  fs.mkdirSync(path.dirname(path.resolve(destination)), { recursive: true });
  temporary = `${destination}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, compact, { flag: "wx" });
  fs.renameSync(temporary, destination);
  const cited = listing.trials.filter((row) => row[claimAt]).length;
  console.log(`Staged ${listing.trials.length} listed trials of ${listing.set} (${cited} cited by a published claim, ${size.toLocaleString("en")} bytes) in ${destination}. Commit this file to publish them.`);
} catch (error) {
  if (temporary && fs.existsSync(temporary)) fs.unlinkSync(temporary);
  console.error(`Trial listing snapshot unchanged: ${error.message}`);
  process.exit(1);
}
