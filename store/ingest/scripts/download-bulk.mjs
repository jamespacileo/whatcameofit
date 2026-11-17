// Brings the bulk tier back from the bucket and proves it is the file that was put there.
//
//   node scripts/download-bulk.mjs <build id> <out.sqlite> (--remote | --persist-to <dir>)
//
// Reads bulk/<build id>/manifest.json, fetches each part and checks its SHA-256, joins
// and decompresses them, and checks the whole file's size and SHA-256 against the
// manifest. The file is written under a name ending `.partial` and takes its name only
// when it has been proved. Exit 1 on anything missing or different.
import { createReadStream, createWriteStream, mkdtempSync, readFileSync, renameSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import { createZstdDecompress } from "node:zlib";
import { bucket, sha256 } from "./r2.mjs";

const argv = process.argv.slice(2);
const [build, out] = argv;
if (!build || !out || build.startsWith("--") || out.startsWith("--")) { console.error("usage: download-bulk.mjs <build id> <out.sqlite> (--remote | --persist-to <dir>) [--production <bucket>]"); process.exit(2); }
let from;
try { from = bucket(argv); } catch (error) { console.error(error.message); process.exit(2); }
const work = mkdtempSync(join(tmpdir(), "thenwhat-bulk-"));
const fail = (message) => { console.error(message); rmSync(work, { recursive: true, force: true }); rmSync(`${out}.partial`, { force: true }); process.exit(1); };

const started = Date.now();
if (!(await from.get(`bulk/${build}/manifest.json`, join(work, "manifest.json")))) fail(`no manifest for build ${build} in ${from.label}: the build is not there, or its upload did not finish`);
const manifest = JSON.parse(readFileSync(join(work, "manifest.json"), "utf8"));
for (const part of manifest.parts) {
  const path = join(work, part.name);
  if (!(await from.get(`bulk/${build}/${part.name}`, path))) fail(`MISSING bulk/${build}/${part.name}`);
  if (statSync(path).size !== part.bytes || (await sha256(path)) !== part.sha256) fail(`DIFFERS bulk/${build}/${part.name}: not the bytes the manifest says`);
}
async function* joined() { for (const part of manifest.parts) yield* createReadStream(join(work, part.name)); }
await pipeline(Readable.from(joined()), createZstdDecompress(), createWriteStream(`${out}.partial`));
if (statSync(`${out}.partial`).size !== manifest.bytes || (await sha256(`${out}.partial`)) !== manifest.sha256) fail("DIFFERS: the restored file is not the one the manifest describes");
renameSync(`${out}.partial`, out);
rmSync(work, { recursive: true, force: true });
console.log(`restored build ${manifest.build} of ${manifest.date}: ${manifest.parts.length} part(s), ${(manifest.bytes / 1e6).toFixed(1)} MB, sha256 as the manifest says, in ${((Date.now() - started) / 1000).toFixed(1)} s`);
