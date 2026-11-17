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
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { bucket, sha256 } from "./r2.mjs";

const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const file = argv[0], build = value("--build");
if (!file || file.startsWith("--") || !existsSync(file) || !/^[A-Za-z0-9._-]{1,64}$/.test(build || "")) { console.error("usage: upload-delta.mjs <delta file> --build <id> [--through <seq>] [--date YYYY-MM-DD] (--remote | --persist-to <dir>) [--production <bucket>]"); process.exit(2); }
let to;
try { to = bucket(argv); } catch (error) { console.error(error.message); process.exit(2); }
const date = value("--date") || new Date().toISOString().slice(0, 10);
const through = value("--through") === null ? null : Number(value("--through"));
if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || (through !== null && !(Number.isInteger(through) && through >= 0))) { console.error("--date is YYYY-MM-DD and --through a whole number"); process.exit(2); }

const work = mkdtempSync(join(tmpdir(), "thenwhat-delta-"));
try {
  if (!(await to.get(`bulk/${build}/manifest.json`, join(work, "manifest.json")))) throw new Error(`no build ${build} in ${to.label}: a delta is kept beside its build`);
  const list = (await to.get(`bulk/${build}/deltas.json`, join(work, "deltas.json"))) ? JSON.parse(readFileSync(join(work, "deltas.json"), "utf8")) : { build, deltas: [] };
  const sum = await sha256(file);
  const known = list.deltas.find((delta) => delta.sha256 === sum);
  if (known) { console.log(`already there: bulk/${build}/${known.name}`); process.exit(0); }
  const ext = /(\.[a-z0-9]+){1,2}$/i.exec(basename(file))?.[0] || "";
  const name = `delta-${date}-${list.deltas.filter((delta) => delta.date === date).length + 1}${ext}`;
  await to.put(`bulk/${build}/${name}`, file);
  list.deltas.push({ name, date, bytes: statSync(file).size, sha256: sum, through });
  writeFileSync(join(work, "deltas.json"), JSON.stringify(list, null, 1) + "\n");
  await to.put(`bulk/${build}/deltas.json`, join(work, "deltas.json"));
  console.log(`uploaded bulk/${build}/${name} (${(statSync(file).size / 1e3).toFixed(1)} KB), delta ${list.deltas.length} of build ${build}, into ${to.label}`);
} catch (error) { console.error(`FAILED: ${error.message}`); process.exitCode = 1; } finally { rmSync(work, { recursive: true, force: true }); }
