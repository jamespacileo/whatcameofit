// What must be true of a trial listing before it is staged or deployed: it matches its
// schema, is small enough to be the one file a search fetches, and names no claim the
// export it stands beside does not publish. Used by stage-trials-listing.mjs, deploy.mjs
// and pr-preview.mjs, so a listing that could not be staged cannot be deployed either.
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

// Past this the listing is to be split by a rule the page can follow (openspec
// trial-pages); Cloudflare refuses a file over 25 MiB outright.
export const LISTING_LIMIT_BYTES = 8 * 1024 * 1024;

const SCHEMA_FILE = path.resolve(import.meta.dirname, "../trials-listing.schema.json");

/** Where an export's listing stands: beside it, under its name with "export" replaced by
 * "trials-listing". Null for an export under a name of its own. The site's build finds
 * it by the same rule (src/lib/trials-listing.ts). */
export function listingBeside(exportFile) {
  const name = path.basename(exportFile);
  const beside = name.replace(/export(?=\.json$)/, "trials-listing");
  return beside === name ? null : path.join(path.dirname(exportFile), beside);
}

/**
 * Why this listing must not be published beside this export: one sentence each. An empty
 * list means it may be. A listing with no trials is a problem only where `allowEmpty` is
 * not set: staging one publishes nothing, while a deployment may carry one.
 * @param {{ text: string, data: { claims?: { slug: string }[] }, allowEmpty?: boolean }} given
 * @returns {{ problems: string[], listing?: object, compact?: string, size?: number }}
 */
export function listingProblems({ text, data, allowEmpty = false }) {
  let listing;
  try {
    listing = JSON.parse(text);
  } catch {
    return { problems: ["The trial listing is not JSON."] };
  }
  const ajv = new Ajv2020({ allErrors: false });
  addFormats(ajv);
  const validate = ajv.compile(JSON.parse(fs.readFileSync(SCHEMA_FILE, "utf8")));
  if (!validate(listing)) {
    const [problem] = validate.errors ?? [];
    return { problems: [`The trial listing does not match trials-listing.schema.json: ${problem?.instancePath || "/"} ${problem?.message}`] };
  }
  const problems = [];
  if (listing.trials.length === 0 && !allowEmpty) problems.push("The trial listing holds no trials. There is nothing to stage.");
  const compact = `${JSON.stringify(listing)}\n`;
  const size = Buffer.byteLength(compact);
  if (size > LISTING_LIMIT_BYTES) {
    problems.push(`The trial listing is ${size.toLocaleString("en")} bytes, over the ${LISTING_LIMIT_BYTES.toLocaleString("en")} a single file may be. List a smaller set, or split it.`);
  }
  // Stale check: a listing written before or after another export names claims that
  // export does not publish. Write both again, together.
  const published = new Set((data?.claims ?? []).map((claim) => claim.slug));
  const claimAt = listing.columns.indexOf("claim");
  const unknown = [...new Set(listing.trials.map((row) => row[claimAt]).filter((slug) => slug && !published.has(slug)))];
  if (unknown.length) {
    problems.push(`The trial listing names ${unknown.length} claim(s) the export does not publish (${unknown.slice(0, 3).join(", ")}${unknown.length > 3 ? ", …" : ""}). Write the export and the listing again together (make publish-data).`);
  }
  return { problems, listing, compact, size };
}

/** The problems of the listing beside an export, for a deployment: none when there is no
 * listing, since a site built without one opens no page for an uncited trial. */
export function besideProblems(exportFile, data) {
  const file = process.env.TRIALS_LISTING_FILE ? path.resolve(process.env.TRIALS_LISTING_FILE) : listingBeside(exportFile);
  if (!file || !fs.existsSync(file)) return [];
  return listingProblems({ text: fs.readFileSync(file, "utf8"), data, allowEmpty: true }).problems;
}
