// Runs after every build. A page without the footer notices must never ship.
import fs from "node:fs";
import path from "node:path";
import { NOTICES } from "../src/lib/notices.ts";
import { canMoveLargeReleaseFile } from "../src/lib/release-paths.mjs";
import { FILE_COUNT_LIMIT, FILE_LIMIT, HOST_FILE_COUNT, SPLIT_RELEASE, countFiles, oversizedFiles } from "./dist-size.mjs";

const DIST = path.resolve(process.env.DIST_DIR ?? "dist");
const REQUIRED = [...NOTICES, "Data sources:", "Registries"];

function pages(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) return entry.name === "pagefind" ? [] : pages(full);
    return entry.name.endsWith(".html") ? [full] : [];
  });
}

const problems = [];
const found = pages(DIST);
for (const page of found) {
  const html = fs.readFileSync(page, "utf8");
  for (const text of REQUIRED) {
    if (!html.includes(text)) problems.push(`${path.relative(DIST, page)} lacks "${text}"`);
  }
}

if (found.length === 0) problems.push("no pages were built");
// The host refuses a file over 25 MiB at deploy time. A split release sends
// oversized topic and row files through the Worker and checks the static remainder.
const oversized = oversizedFiles(DIST, FILE_LIMIT);
let deferred = 0;
for (const { file, bytes } of oversized) {
  if (SPLIT_RELEASE && canMoveLargeReleaseFile(file)) {
    deferred += 1;
    continue;
  }
  problems.push(
    `${file} is ${(bytes / 2 ** 20).toFixed(1)} MiB, over the ${FILE_LIMIT / 2 ** 20} MiB a built file may be`,
  );
}
// The host refuses a version of more than 20,000 files on its free plan.
const files = countFiles(DIST);
if (!SPLIT_RELEASE && files > FILE_COUNT_LIMIT) {
  problems.push(
    `the build holds ${files.toLocaleString("en-GB")} files, over the ${FILE_COUNT_LIMIT.toLocaleString("en-GB")} a build may hold (the host's free plan allows ${HOST_FILE_COUNT.toLocaleString("en-GB")}; set DIST_FILE_LIMIT for a plan that allows more)`,
  );
}
if (problems.length > 0) {
  console.error(`Build check failed:\n  ${problems.join("\n  ")}`);
  process.exit(1);
}
const count = SPLIT_RELEASE
  ? `${files.toLocaleString("en-GB")} rendered files; ${deferred} oversized list files to stage separately`
  : `no file over ${FILE_LIMIT / 2 ** 20} MiB; ${files.toLocaleString("en-GB")} files of the ${FILE_COUNT_LIMIT.toLocaleString("en-GB")} a build may hold`;
console.log(`Build check passed: footer notices present on ${found.length} pages; ${count}.`);
