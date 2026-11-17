// Runs after every build. A page without the footer notices must never ship.
import fs from "node:fs";
import path from "node:path";
import { NOTICES } from "../src/lib/notices.ts";
import { FILE_LIMIT, oversizedFiles } from "./dist-size.mjs";

const DIST = path.resolve("dist");
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
// The host refuses a file over 25 MiB at deploy time; stop well before that, here.
for (const { file, bytes } of oversizedFiles(DIST, FILE_LIMIT)) {
  problems.push(
    `${file} is ${(bytes / 2 ** 20).toFixed(1)} MiB, over the ${FILE_LIMIT / 2 ** 20} MiB a built file may be`,
  );
}
if (problems.length > 0) {
  console.error(`Build check failed:\n  ${problems.join("\n  ")}`);
  process.exit(1);
}
console.log(
  `Build check passed: footer notices present on ${found.length} pages; no file over ${FILE_LIMIT / 2 ** 20} MiB.`,
);
