// What the built site must stay under. The host refuses a file over 25 MiB, and a version
// of more than 20,000 files on the free plan, so a deploy would fail; the build stops first,
// at 20 MiB a file and 18,000 files, naming what is over. Openspec open-data: "No built
// file near the host's limit" and "Built files counted against the host's limit".
import fs from "node:fs";
import path from "node:path";

export const FILE_LIMIT = 20 * 2 ** 20;
/** The most files a version may hold on the host's free plan. */
export const HOST_FILE_COUNT = 20_000;
/** Where the build stops. DIST_FILE_LIMIT raises it for a plan that allows more. */
export const FILE_COUNT_LIMIT = Number(process.env.DIST_FILE_LIMIT) || 18_000;
// A split release is counted after its claim files have been staged separately.
export const SPLIT_RELEASE = process.env.SITE_RELEASE_BUILD === "1";

// A claim emits its page, data record, feed, embed, oEmbed, and three card images.
// Search fragments and shared files add to this floor, so the final check still runs.
const CLAIM_ROUTE_FILES = 8;

export function assertClaimFilesFit(claims, limit = FILE_COUNT_LIMIT) {
  const floor = claims * CLAIM_ROUTE_FILES;
  if (floor > limit) {
    throw new Error(
      `The ${claims.toLocaleString("en-GB")} claims require at least ${floor.toLocaleString("en-GB")} files before search indexing. The build limit is ${limit.toLocaleString("en-GB")} files.`,
    );
  }
}

/** How many files are under the directory, in every folder. */
export function countFiles(directory) {
  return fs
    .readdirSync(directory, { withFileTypes: true, recursive: true })
    .filter((entry) => entry.isFile()).length;
}

/** Every file under the directory larger than the limit, by path relative to it, largest first. */
export function oversizedFiles(directory, limit = FILE_LIMIT) {
  const found = [];
  const walk = (current) => {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.isFile()) {
        const { size } = fs.statSync(full);
        if (size > limit) found.push({ file: path.relative(directory, full), bytes: size });
      }
    }
  };
  walk(directory);
  return found.sort((a, b) => b.bytes - a.bytes);
}
