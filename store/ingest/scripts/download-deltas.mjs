// Brings a build's deltas back from the bucket, each proved against the build's list.
//
//   node scripts/download-deltas.mjs <build id> <out folder> (--remote | --persist-to <dir>)
//
// Writes deltas.json and each delta under its name. A restore of the bulk tier is
// `download-bulk.mjs`, this, then `thenwhat store apply-delta` for each delta in the
// list's order. A build with no delta yet gives an empty list. Exit 1 on a delta that is
// missing or is not the bytes the list says.
import { mkdirSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { bucket, sha256 } from "./r2.mjs";

const argv = process.argv.slice(2);
const [build, out] = argv;
if (!build || !out || build.startsWith("--") || out.startsWith("--")) { console.error("usage: download-deltas.mjs <build id> <out folder> (--remote | --persist-to <dir>) [--production <bucket>]"); process.exit(2); }
let from;
try { from = bucket(argv); } catch (error) { console.error(error.message); process.exit(2); }
mkdirSync(out, { recursive: true });
const listed = join(out, "deltas.json");
if (!(await from.get(`bulk/${build}/deltas.json`, listed))) { writeFileSync(listed, JSON.stringify({ build, deltas: [] }, null, 1) + "\n"); console.log(`build ${build} has no delta in ${from.label}`); process.exit(0); }
const { deltas } = JSON.parse(readFileSync(listed, "utf8"));
for (const delta of deltas) {
  const path = join(out, `${delta.name}.partial`);
  const fail = (message) => { console.error(message); rmSync(path, { force: true }); process.exit(1); };
  if (!(await from.get(`bulk/${build}/${delta.name}`, path))) fail(`MISSING bulk/${build}/${delta.name}`);
  if (statSync(path).size !== delta.bytes || (await sha256(path)) !== delta.sha256) fail(`DIFFERS bulk/${build}/${delta.name}: not the bytes the list says`);
  renameSync(path, join(out, delta.name));
}
console.log(`${deltas.length} delta(s) of build ${build}, each as the list says, in order: ${deltas.map((delta) => delta.name).join(", ")}`);
