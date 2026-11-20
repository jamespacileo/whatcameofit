// What the built site must stay under. The host refuses a file over 25 MiB, and a version
// of more than 20,000 files on the free plan, so a deploy would fail; the build stops first,
// at 20 MiB a file and 18,000 files, naming what is over. Openspec open-data: "No built
// file near the host's limit" and "Built files counted against the host's limit".
import fs from "node:fs";
import path from "node:path";
import { gzipSync } from "node:zlib";

export const FILE_LIMIT = 20 * 2 ** 20;
/** The most files a version may hold on the host's free plan. */
export const HOST_FILE_COUNT = 20_000;
/** Where the build stops. DIST_FILE_LIMIT raises it for a plan that allows more. */
export const FILE_COUNT_LIMIT = Number(process.env.DIST_FILE_LIMIT) || 18_000;

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

// The two files the lookup box's word search downloads, each the first time a reader types or
// searches (never on page load). At 30,000 pairs, the size the design plans for, each comes
// to about 1 MB with gzip (openspec pairs-site, task 4.11). The build stops at 2 MiB each,
// about twice that, so a much heavier file is caught before it ships: then the search is
// split into parts (task 4.11) rather than the limit raised.
export const SEARCH_FILES = ["lookup/2.json", "search-detail.json"];
export const SEARCH_GZIP_LIMIT = 2 * 2 ** 20;

/** Each search file whose gzip size is over the limit, with that size. Missing files are skipped. */
export function heavySearchFiles(directory, limit = SEARCH_GZIP_LIMIT) {
  return SEARCH_FILES.flatMap((file) => {
    const full = path.join(directory, file);
    if (!fs.existsSync(full)) return [];
    const bytes = gzipSync(fs.readFileSync(full)).length;
    return bytes > limit ? [{ file, bytes }] : [];
  });
}
