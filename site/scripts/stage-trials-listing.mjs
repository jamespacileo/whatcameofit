// Freeze the trial listing beside the published export, as stage-public-export.mjs
// freezes the export: GitHub builds from this file and never reads the private database.
// The listing is staged only if it matches its schema, is small enough to be one file,
// and names no claim the staged export does not publish.
import fs from "node:fs";
import path from "node:path";
import { listingProblems } from "./listing-checks.mjs";

const [source, destination, exportFile] = process.argv.slice(2);
if (!source || !destination || !exportFile) {
  console.error("Usage: node stage-trials-listing.mjs SOURCE DESTINATION STAGED_EXPORT");
  process.exit(1);
}
let temporary;
try {
  const data = JSON.parse(fs.readFileSync(exportFile, "utf8"));
  const { problems, listing, compact, size } = listingProblems({ text: fs.readFileSync(source, "utf8"), data });
  if (problems.length) throw new Error(problems.join("\n"));
  const claimAt = listing.columns.indexOf("claim");
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
