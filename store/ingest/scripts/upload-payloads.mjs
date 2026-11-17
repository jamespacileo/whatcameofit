// Puts the payload objects a store build wrote (`<folder>/payload/<sha256>`) into the
// PAYLOADS bucket under the same keys, `payload/<sha256>`, as the service and the export
// read them.
//
//   node scripts/upload-payloads.mjs <folder> --persist-to <dir>     the local engine
//   node scripts/upload-payloads.mjs <folder> --remote               the preview bucket, EU jurisdiction
//
// It uses Wrangler and its own login: no access key is made, and nothing secret is read
// or printed. Only the bucket this service is bound to in wrangler.jsonc, a preview one,
// is written to; production needs `--production <bucket name>` beside `--remote`.
//
//   --jobs N          objects at a time (4: twelve at a time were refused with 429 on the preview)
//   --batch N         objects a Wrangler process (500); what a stopped run sends again
//   --state <file>    where what was uploaded is noted (.upload-state/<bucket>.json, git-ignored)
//   --check-first     before uploading an object the notes do not have, read it back and
//                     skip it when it is already there with the same bytes
//   --only N          upload the first N objects only: a trial
//
// Resumable: an object noted as uploaded, with the same size, is skipped, so a run that
// stopped is run again as it was. Wrangler has no command that asks whether an object is
// there without fetching it, which is why the notes are kept; an object is only its
// checksum's bytes, so putting one twice changes nothing. A file whose bytes are not its
// name's checksum is refused. It ends with a count and reads 20 objects back at random,
// comparing each one's SHA-256 with its key. Exit 1 when an object failed or differed.
import { execFile } from "node:child_process";
import { createHash, randomInt } from "node:crypto";
import { createReadStream, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { bucket, sha256 } from "./r2.mjs";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const run = promisify(execFile);
const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const folder = argv[0];
const usage = () => { console.error("usage: upload-payloads.mjs <folder> (--remote | --persist-to <dir>) [--jobs N] [--state <file>] [--check-first] [--only N] [--production <bucket>]"); process.exit(2); };
if (!folder || folder.startsWith("--")) usage();
const remote = argv.includes("--remote");
if (!remote && !value("--persist-to")) usage();

const jobs = Math.min(Math.max(Number(value("--jobs")) || 4, 1), 32);
const batch = Math.min(Math.max(Number(value("--batch")) || 500, 1), 5000);
let to;
try { to = bucket(argv); } catch (error) { console.error(error.message); process.exit(2); }
const sha = sha256;

const from = existsSync(join(folder, "payload")) ? join(folder, "payload") : folder;
let names = readdirSync(from).filter((name) => /^[0-9a-f]{64}$/.test(name)).sort();
const strangers = readdirSync(from).filter((name) => !/^[0-9a-f]{64}$/.test(name) && !name.startsWith("."));
if (!names.length) { console.error(`no payload object in ${from}`); process.exit(2); }
if (value("--only")) names = names.slice(0, Number(value("--only")));

const statePath = value("--state") || here(`../.upload-state/${to.name}${remote ? "" : ".local"}.json`);
mkdirSync(dirname(statePath), { recursive: true });
const state = existsSync(statePath) ? JSON.parse(readFileSync(statePath, "utf8")) : {};
const note = () => writeFileSync(statePath, JSON.stringify(state));
const scratch = mkdtempSync(join(tmpdir(), "thenwhat-payloads-"));

// What the bucket holds under a key, as its SHA-256, or null when it holds nothing.
async function held(name, n) {
  const path = join(scratch, `${n}-${name}`);
  try { return (await to.get(`payload/${name}`, path)) ? await sha(path) : null; } finally { rmSync(path, { force: true }); }
}

const total = names.reduce((sum, name) => sum + statSync(join(from, name)).size, 0);
console.log(`${names.length} objects, ${(total / 1e6).toFixed(1)} MB, into ${to.label}, ${jobs} at a time`);
if (strangers.length) console.log(`${strangers.length} file(s) not named by a checksum are left alone`);
const done = { uploaded: 0, skipped: 0, there: 0, failed: [] };
const started = Date.now();
// What is still to go: not noted, its bytes its name's checksum, and with --check-first
// not already in the bucket.
const todo = [];
let next = 0;
await Promise.all(Array.from({ length: 8 }, async (_, n) => {
  for (;;) {
    const name = names[next]; next += 1;
    if (name === undefined) return;
    const path = join(from, name), size = statSync(path).size;
    if (state[name] === size) { done.skipped += 1; continue; }
    if ((await sha(path)) !== name) { done.failed.push([name, "the file's bytes are not its name's checksum"]); continue; }
    if (argv.includes("--check-first") && (await held(name, n)) === name) { state[name] = size; done.there += 1; continue; }
    todo.push([name, path, size]);
  }
}));
// Uploaded a batch at a time, each batch one Wrangler process, and noted when it is done:
// a run that stopped loses at most the batch it was in, which is sent again.
for (let at = 0; at < todo.length; at += batch) {
  const part = todo.slice(at, at + batch), list = join(scratch, `batch-${at}.json`);
  writeFileSync(list, JSON.stringify(part.map(([name, path]) => ({ key: `payload/${name}`, file: resolve(path) }))));
  try { await to.putMany(list, jobs); } catch (error) {
    for (const [name] of part) done.failed.push([name, error.message]);
    console.error(`FAILED a batch of ${part.length}: ${error.message}\nrun again to go on from here`);
    break;
  }
  for (const [name, , size] of part) state[name] = size;
  done.uploaded += part.length;
  note();
  console.log(`  ${done.uploaded} of ${todo.length} after ${((Date.now() - started) / 1000).toFixed(0)} s`);
}
note();
const seconds = (Date.now() - started) / 1000;
console.log(`uploaded ${done.uploaded}, already noted ${done.skipped}, already there ${done.there}, failed ${done.failed.length}, in ${seconds.toFixed(1)} s`);
for (const [name, why] of done.failed.slice(0, 5)) console.error(`FAILED payload/${name.slice(0, 12)}…: ${why}`);

// Twenty at random, read back, each one's checksum against its key.
const sure = names.filter((name) => state[name] !== undefined);
const picked = new Set();
while (picked.size < Math.min(20, sure.length)) picked.add(sure[randomInt(sure.length)]);
const wrong = [];
for (const [n, name] of [...picked].entries()) if ((await held(name, `check-${n}`)) !== name) wrong.push(name);
for (const name of wrong) { console.error(`READ BACK DIFFERS payload/${name.slice(0, 12)}…`); delete state[name]; }
if (wrong.length) note();
console.log(`read back ${picked.size} at random: ${picked.size - wrong.length} are what their keys say`);
rmSync(scratch, { recursive: true, force: true });
process.exit(done.failed.length || wrong.length ? 1 : 0);
