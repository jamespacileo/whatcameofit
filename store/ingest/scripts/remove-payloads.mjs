// Takes payload objects, or a bulk build, out of the PAYLOADS bucket.
//
//   node scripts/remove-payloads.mjs --all-noted (--remote | --persist-to <dir>)
//       every object the upload noted for this bucket (.upload-state/<bucket>.json), then the notes
//   node scripts/remove-payloads.mjs --not-in <payload folder> (--remote | --persist-to <dir>)
//       the noted objects the folder no longer holds: after a rebuild the checksums change
//   node scripts/remove-payloads.mjs --bulk-build <id> (--remote | --persist-to <dir>)
//       bulk/<id>/: its parts, its deltas and their list, and its manifest last
//   ... --verify-empty     afterwards, ask for every key that was noted and show none is there
//
// Wrangler's own login, the EU jurisdiction, the preview bucket unless `--remote
// --production <bucket>` names production's. At most 4 objects at a time (`--jobs`, never
// more: twelve at a time were refused with 429 on the preview), each tried again with a
// longer wait when refused. Resumable: a key leaves the notes when its object is gone, so
// a run that stopped is run again. It prints counts, and of a key only its first 12
// characters.
//
// What it cannot do: this Wrangler (4.161.0) has no command that lists a bucket's
// objects, so only the objects the notes name can be removed or shown to be gone. An
// object uploaded with other notes, or by hand, is not seen. To be sure a bucket holds no
// payload/ or bulk/ object, look in the dashboard: R2, the bucket, Objects, and search the
// prefixes `payload/` and `bulk/`; `wrangler r2 bucket info <bucket> --jurisdiction eu`
// also gives the bucket's object count, which lags by some minutes.
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { bucket } from "./r2.mjs";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const modes = ["--all-noted", "--not-in", "--bulk-build"].filter((flag) => argv.includes(flag));
if (modes.length !== 1) { console.error("usage: remove-payloads.mjs (--all-noted | --not-in <payload folder> | --bulk-build <id>) (--remote | --persist-to <dir>) [--verify-empty] [--jobs N] [--state <file>] [--production <bucket>]"); process.exit(2); }
let at;
try { at = bucket(argv); } catch (error) { console.error(error.message); process.exit(2); }
const jobs = Math.min(Math.max(Number(value("--jobs")) || 4, 1), 4);
const short = (key) => `${key.slice(0, key.lastIndexOf("/") + 13)}…`;
const scratch = mkdtempSync(join(tmpdir(), "thenwhat-remove-"));
const suffix = at.remote ? "" : ".local";

// Removes the keys, a few at a time; `gone` is told of each one removed.
async function removeAll(keys, gone) {
  const failed = [];
  let next = 0, done = 0, since = Date.now();
  await Promise.all(Array.from({ length: jobs }, async () => {
    for (;;) {
      const key = keys[next]; next += 1;
      if (key === undefined) return;
      try { await at.remove(key); gone(key); done += 1; } catch (error) { failed.push([key, error.message]); }
      if (Date.now() - since > 15_000) { since = Date.now(); console.log(`  ${done} of ${keys.length} removed`); }
    }
  }));
  return failed;
}
// The keys still answering, of those given.
async function stillThere(keys) {
  const there = [];
  let next = 0;
  await Promise.all(Array.from({ length: jobs }, async (_, n) => {
    for (;;) {
      const key = keys[next]; next += 1;
      if (key === undefined) return;
      const path = join(scratch, `left-${n}`);
      if (await at.get(key, path)) there.push(key);
      rmSync(path, { force: true });
    }
  }));
  return there;
}

const started = Date.now();
let asked = [], failed = [];
if (modes[0] === "--bulk-build") {
  const build = value("--bulk-build");
  if (!/^[A-Za-z0-9._-]{1,64}$/.test(build || "")) { console.error("name the build: --bulk-build <id>"); process.exit(2); }
  // What the build holds is read from its own manifest and list of deltas, and from the
  // upload's notes when the manifest never arrived.
  const names = new Set();
  const read = async (name) => { const path = join(scratch, name); return (await at.get(`bulk/${build}/${name}`, path)) ? JSON.parse(readFileSync(path, "utf8")) : null; };
  const manifest = await read("manifest.json"), deltas = await read("deltas.json");
  for (const part of manifest?.parts || []) names.add(part.name);
  for (const delta of deltas?.deltas || []) names.add(delta.name);
  const notes = here(`../.upload-state/bulk-${build}-${at.name}${suffix}.json`);
  if (existsSync(notes)) for (const name of Object.keys(JSON.parse(readFileSync(notes, "utf8")))) names.add(name);
  // The lists go last, so a run that stopped can still read what is left.
  asked = [...[...names].sort().map((name) => `bulk/${build}/${name}`), `bulk/${build}/deltas.json`, `bulk/${build}/manifest.json`];
  console.log(`build ${build} in ${at.label}: ${names.size} part(s) and delta(s), and its lists`);
  failed = await removeAll(asked.slice(0, -2), () => {});
  if (!failed.length) { failed = await removeAll(asked.slice(-2), () => {}); if (!failed.length) rmSync(notes, { force: true }); }
} else {
  const statePath = value("--state") || here(`../.upload-state/${at.name}${suffix}.json`);
  if (!existsSync(statePath)) { console.error(`no notes of an upload to ${at.name} at ${statePath}: nothing is known to remove (see the head of this script)`); process.exit(1); }
  const state = JSON.parse(readFileSync(statePath, "utf8"));
  let names = Object.keys(state);
  if (modes[0] === "--not-in") {
    const folder = value("--not-in");
    if (!folder || !existsSync(folder)) { console.error("--not-in names the payload folder that is kept"); process.exit(2); }
    const kept = new Set(readdirSync(existsSync(join(folder, "payload")) ? join(folder, "payload") : folder));
    names = names.filter((name) => !kept.has(name));
  }
  asked = names.map((name) => `payload/${name}`);
  console.log(`${asked.length} of ${Object.keys(state).length} noted payload objects to remove from ${at.label}, ${jobs} at a time`);
  let since = 0;
  failed = await removeAll(asked, (key) => {
    delete state[key.slice(8)];
    if (Date.now() - since > 10_000) { since = Date.now(); writeFileSync(statePath, JSON.stringify(state)); }
  });
  if (Object.keys(state).length) writeFileSync(statePath, JSON.stringify(state)); else rmSync(statePath, { force: true });
}
console.log(`removed ${asked.length - failed.length}, failed ${failed.length}, in ${((Date.now() - started) / 1000).toFixed(1)} s`);
for (const [key, why] of failed.slice(0, 10)) console.error(`FAILED ${short(key)}: ${why}`);

let left = [];
if (argv.includes("--verify-empty")) {
  left = await stillThere(asked);
  console.log(left.length ? `STILL THERE: ${left.length} of ${asked.length} objects asked for (${left.slice(0, 3).map(short).join(", ")})` : `asked for all ${asked.length} again: none is there`);
  console.log("This shows only the objects the notes named. Wrangler cannot list a bucket: for proof that no payload/ or bulk/ object is left, search those prefixes in the dashboard (R2, the bucket, Objects).");
}
rmSync(scratch, { recursive: true, force: true });
process.exit(failed.length || left.length ? 1 : 0);
