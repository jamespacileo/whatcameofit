// The whole cut-over chain on this machine, in one command. Nothing is sent anywhere:
// D1 and R2 are Wrangler's local engine, in a work folder that is removed at the end.
//
//   node scripts/rehearsal.mjs --hot <hot.sqlite> --bulk <bulk.sqlite> --payloads <folder> [--work <dir>] [--rows-a-file N] [--skip-export]
//   make store-rehearsal STORE_HOT=... STORE_BULK=... PAYLOADS=...
//
//   1 dump       the hot file as SQL for D1's import
//   2 check      the dump replayed strictly, counted against its manifest
//   3 load       migrations, then the files, into the local D1 engine, counted
//   4 checksum   every table in D1 against the hot file
//   5 payloads   the payload objects into the local bucket, twenty read back
//   6 bulk       the bulk file up, down again, proved the same
//   7 export     `thenwhat export-compare` against the hot file and the payload folder
//
// Each stage's time is printed, and the total. Exit 1 at the first stage that fails or
// finds a difference. `--skip-export` leaves out stage 7, which needs the working
// database (DATABASE_URL); the summary then says it was not run.
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { sha256 } from "./r2.mjs";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const hot = value("--hot"), bulk = value("--bulk"), payloads = value("--payloads");
for (const [name, path] of [["--hot", hot], ["--bulk", bulk], ["--payloads", payloads]]) {
  if (!path || !existsSync(path)) { console.error(`${name} is needed and must exist (STORE_HOT, STORE_BULK and PAYLOADS for make)`); process.exit(2); }
}
const work = value("--work") || mkdtempSync(join(tmpdir(), "thenwhat-rehearsal-"));
const sql = join(work, "sql"), state = join(work, "state");
const script = (name, ...args) => [process.execPath, [here(`./${name}.mjs`), ...args]];
const env = { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" };
const build = "rehearsal";

const stages = [
  ["dump", () => [script("dump-for-import", hot, join(sql, "store.sql"), "--rows-a-file", value("--rows-a-file") || "60000")]],
  ["check", () => [script("check-dump", sql)]],
  ["load", () => [[here("../node_modules/.bin/wrangler"), ["d1", "migrations", "apply", "STORE", "--local", "--persist-to", state]], script("import-folder", sql, "--persist-to", state)]],
  ["checksum", () => [script("checksum-d1", "--file", hot, "--persist-to", state)]],
  ["payloads", () => [script("upload-payloads", payloads, "--persist-to", state, "--state", join(work, "payloads.json"))]],
  ["bulk", () => [script("upload-bulk", bulk, "--persist-to", state, "--state", join(work, "bulk.json"), "--build", build), script("download-bulk", build, join(work, "bulk-back.sqlite"), "--persist-to", state)]],
  ["export", () => [["uv", ["run", "--directory", here("../../../pipeline"), "thenwhat", "export-compare", "--store", resolve(hot), "--payloads", resolve(payloads), "--allow-named"]]]],
];

const times = [];
let failed = null;
const began = Date.now();
for (const [name, commands] of stages) {
  if (name === "export" && argv.includes("--skip-export")) { times.push([name, null]); continue; }
  console.log(`\n== ${name}`);
  const started = Date.now();
  let ok = true;
  for (const [command, args] of commands()) {
    const done = spawnSync(command, args, { cwd: here(".."), env, stdio: ["ignore", "pipe", "inherit"], encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
    // The last lines of each step: what it counted and what differed.
    console.log((done.stdout || "").trimEnd().split("\n").slice(-6).join("\n"));
    if (done.status !== 0) { ok = false; break; }
  }
  if (ok && name === "bulk" && (await sha256(join(work, "bulk-back.sqlite"))) !== (await sha256(bulk))) { console.error("DIFFERS: the bulk file that came back is not the one that went up"); ok = false; }
  times.push([name, (Date.now() - started) / 1000]);
  if (!ok) { failed = name; break; }
}
console.log("\n== times");
for (const [name, seconds] of times) console.log(`${name.padEnd(10)} ${seconds === null ? "not run (--skip-export)" : `${seconds.toFixed(1)} s`}`);
console.log(`${"total".padEnd(10)} ${((Date.now() - began) / 1000).toFixed(1)} s`);
console.log(failed ? `\nFAILED at ${failed}` : `\nthe rehearsal passed${argv.includes("--skip-export") ? ", without the export comparison" : ""}`);
if (!value("--work")) rmSync(work, { recursive: true, force: true });
process.exit(failed ? 1 : 0);
