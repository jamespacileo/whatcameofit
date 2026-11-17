// Puts a day's delta of the bulk tier (`thenwhat store fold-inbox` / `merge-bulk` write
// it) in the bucket beside its build, and adds it to the build's list of deltas.
//
//   node scripts/upload-delta.mjs <delta file> --build <id> [--through <seq>] (--remote | --persist-to <dir>)
//
//   bulk/<build id>/delta-<date>-<n><ext>    the delta, as it is; n counts the day's deltas
//   bulk/<build id>/deltas.json              every delta of the build, in the order to replay
//                                            them: name, date, bytes, sha256, through
//
// `--through` is the last inbox record the delta holds, when it came from a fold. The
// build must be there (its manifest is read). A delta already listed, by its SHA-256, is
// not uploaded again. The list is read, added to and written back, so one writer at a
// time: the daily job. It prints the object's key, which `POST /inbox/folded` is told
// before the inbox may be cleared. `--date YYYY-MM-DD` sets the day (today in UTC).
//
// Nothing listed is lost and nothing already in the bucket is written over:
//   * the list is "absent" only when Wrangler says the key does not exist; any other
//     failure to read it (503, a refused login) stops the run before anything is written;
//   * a list that is not a list of this build's deltas stops the run;
//   * the entries listed are written back as they were, names and all, in their order;
//   * a name is taken only when neither the list nor the bucket has it. An object found
//     there unlisted (an earlier run that stopped between the delta and the list) is
//     left alone, or, when it is these very bytes, listed as it is instead of sent again;
//   * the delta is read back and proved before it is listed; the list is read again just
//     before it is written and must not have changed, and is read back after.
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { WRANGLER_PUT_LIMIT_BYTES, bucket, sha256 } from "./r2.mjs";

const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const file = argv[0], build = value("--build");
if (!file || file.startsWith("--") || !existsSync(file) || !/^[A-Za-z0-9._-]{1,64}$/.test(build || "")) { console.error("usage: upload-delta.mjs <delta file> --build <id> [--through <seq>] [--date YYYY-MM-DD] (--remote | --persist-to <dir>) [--production <bucket>]"); process.exit(2); }
let to;
try { to = bucket(argv); } catch (error) { console.error(error.message); process.exit(2); }
const date = value("--date") || new Date().toISOString().slice(0, 10);
const through = value("--through") === null ? null : Number(value("--through"));
if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || (through !== null && !(Number.isInteger(through) && through >= 0))) { console.error("--date is YYYY-MM-DD and --through a whole number"); process.exit(2); }

// The most names tried for one day before giving up: each one tried is an object in the
// bucket that is not this delta.
const MOST_TRIED = 100;
const indexKey = `bulk/${build}/deltas.json`;

// The list as the bucket holds it, proved to be a list of this build's deltas, with its
// text (to see whether it changed); null when the bucket has no list.
async function readList(path) {
  if (!(await to.get(indexKey, path))) return null;
  const text = readFileSync(path, "utf8");
  let list;
  try { list = JSON.parse(text); } catch { throw new Error(`${indexKey} is not JSON: it is left as it is`); }
  if (!list || typeof list !== "object" || !Array.isArray(list.deltas)) throw new Error(`${indexKey} has no list of deltas: it is left as it is`);
  if (list.build !== undefined && list.build !== build) throw new Error(`${indexKey} is the list of build ${list.build}, not ${build}: it is left as it is`);
  const names = new Set();
  for (const delta of list.deltas) {
    if (!delta || typeof delta.name !== "string" || !/^[A-Za-z0-9._-]{1,200}$/.test(delta.name) || names.has(delta.name)) throw new Error(`${indexKey} lists a delta without a name of its own: it is left as it is`);
    names.add(delta.name);
  }
  return { list, text };
}
const stem = (name) => /^(delta-\d{4}-\d{2}-\d{2}-\d+)(?=\.|$)/.exec(name)?.[1] ?? null;

const work = mkdtempSync(join(tmpdir(), "thenwhat-delta-"));
try { await upload(); } catch (error) { console.error(`FAILED: ${error.message}`); process.exitCode = 1; } finally { rmSync(work, { recursive: true, force: true }); }

async function upload() {
  const bytes = statSync(file).size;
  if (bytes > WRANGLER_PUT_LIMIT_BYTES) throw new Error(`the delta is ${bytes} bytes, over Wrangler's ${WRANGLER_PUT_LIMIT_BYTES} an upload`);
  if (!(await to.get(`bulk/${build}/manifest.json`, join(work, "manifest.json")))) throw new Error(`no build ${build} in ${to.label}: a delta is kept beside its build`);
  const held = await readList(join(work, "deltas.json"));
  const list = held?.list ?? { build, deltas: [] };
  const sum = await sha256(file);
  const known = list.deltas.find((delta) => delta.sha256 === sum);
  if (known) return void console.log(`already there: bulk/${build}/${known.name}`);

  // The day's next number: past every one the list has for the day, and past every
  // object the bucket holds under a name not listed.
  const ext = /(\.[a-z0-9]+){1,2}$/i.exec(basename(file))?.[0] || "";
  const listed = new Set(list.deltas.map((delta) => stem(delta.name)).filter(Boolean));
  const ofDay = list.deltas.filter((delta) => delta.date === date);
  let n = Math.max(ofDay.length, ...list.deltas.map((delta) => (delta.name.startsWith(`delta-${date}-`) ? Number(/^delta-\d{4}-\d{2}-\d{2}-(\d+)/.exec(delta.name)?.[1] || 0) : 0))) + 1;
  let name = null, sent = false;
  for (let tried = 0; !name; n += 1) {
    const candidate = `delta-${date}-${n}${ext}`;
    if (listed.has(stem(candidate))) continue;
    if (++tried > MOST_TRIED) throw new Error(`${MOST_TRIED} names for ${date} are taken by objects not in the list: look at bulk/${build}/`);
    const there = join(work, "there");
    if (!(await to.get(`bulk/${build}/${candidate}`, there))) { name = candidate; break; }
    if (statSync(there).size === bytes && (await sha256(there)) === sum) {
      // An earlier run sent these bytes and stopped before the list: listed as it is.
      console.log(`bulk/${build}/${candidate} is already these bytes, from a run that did not finish: listed, not sent again`);
      name = candidate; sent = true; break;
    }
    console.log(`bulk/${build}/${candidate} is in the bucket but not in the list, with other bytes: left as it is`);
    rmSync(there, { force: true });
  }

  const key = `bulk/${build}/${name}`;
  if (!sent) {
    await to.put(key, file);
    const back = join(work, "back");
    if (!(await to.get(key, back))) throw new Error(`${key} is not there after it was sent: the list is not changed`);
    if (statSync(back).size !== bytes || (await sha256(back)) !== sum) throw new Error(`${key} does not read back as the delta's bytes: the list is not changed`);
    rmSync(back, { force: true });
  }

  // The list again, just before it is written: it must be the one this run added to.
  const now = await readList(join(work, "deltas-now.json"));
  if ((now?.text ?? null) !== (held?.text ?? null)) throw new Error(`${indexKey} changed while this ran (or was not read the same twice): nothing is written to it; run again`);
  list.build ??= build;
  list.deltas.push({ name, date, bytes, sha256: sum, through });
  const text = JSON.stringify(list, null, 1) + "\n";
  writeFileSync(join(work, "deltas.json"), text);
  await to.put(indexKey, join(work, "deltas.json"));
  const after = await readList(join(work, "deltas-after.json"));
  if (after?.text !== text) throw new Error(`${indexKey} does not read back as written: run again (the delta ${key} is in the bucket and will be listed, not sent again)`);
  console.log(`uploaded ${key} (${(bytes / 1e3).toFixed(1)} KB), delta ${list.deltas.length} of build ${build}, into ${to.label}`);
}
