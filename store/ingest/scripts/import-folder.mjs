// Loads a folder of SQL files (scripts/dump-for-import.mjs) into the store, in the order
// of their names, stopping at the first that fails, then counts each table against the
// dump's manifest.
//
//   node scripts/import-folder.mjs <folder> [--manifest <file>] [--persist-to <folder>]    the local engine
//   node scripts/import-folder.mjs <folder> [--manifest <file>] --remote                  the preview database
//
// For each file: its size, the seconds it took, and the rows D1 says it wrote (D1 bills
// rows written, indexes and search tables included; the local engine does not say).
// The manifest is <folder>/manifest.json unless named. Exit 1 on a failure or a count
// that differs. A file that failed may have been applied in part or not at all: Cloudflare's
// documentation does not say, so read the counts before loading it again.
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { execute, sum, target } from "./d1.mjs";

const folder = process.argv[2];
if (!folder || folder.startsWith("--")) { console.error("usage: import-folder.mjs <folder> [--manifest <file>] [--remote | --persist-to <folder>]"); process.exit(2); }
const to = target(process.argv);
const named = process.argv.includes("--manifest") ? process.argv[process.argv.indexOf("--manifest") + 1] : join(folder, "manifest.json");
const files = readdirSync(folder).filter((name) => name.endsWith(".sql")).sort();
if (!files.length) { console.error(`no .sql file in ${folder}`); process.exit(2); }
// A folder is loaded only when its dump finished: the manifest is written last, and a file
// still named `.partial`, or a file the manifest does not list, means it did not.
if (!existsSync(named)) { console.error(`no manifest at ${named}: the dump did not finish, or is not here; nothing was loaded`); process.exit(1); }
const manifest = JSON.parse(readFileSync(named, "utf8"));
const listed = (manifest.files || []).map((file) => file.name ?? file.file ?? file.path).filter(Boolean);
const unfinished = readdirSync(folder).filter((name) => name.endsWith(".partial"));
const strangers = listed.length ? [...files.filter((name) => !listed.includes(name)), ...listed.filter((name) => !files.includes(name))] : [];
if (unfinished.length || strangers.length) {
  console.error(`the folder is not the dump its manifest describes (${[...unfinished, ...strangers].slice(0, 5).join(", ")}); nothing was loaded`);
  process.exit(1);
}
console.log(`${files.length} file(s) into the ${to.remote ? "preview database" : "local engine"}`);

let written = 0, seconds = 0;
for (const name of files) {
  const path = resolve(folder, name), started = Date.now();
  let answer;
  try { answer = await execute(to, "--file", path); } catch (error) {
    console.error(`FAILED ${name} after ${((Date.now() - started) / 1000).toFixed(1)} s; nothing after it was loaded\n${error.message}`);
    process.exit(1);
  }
  const took = (Date.now() - started) / 1000, rows = sum(answer, "rows_written");
  written += rows || 0; seconds += took;
  console.log(`${name}  ${(statSync(path).size / 1e6).toFixed(1)} MB  ${took.toFixed(1)} s  rows_written ${rows ?? "not said"}`);
}
console.log(`loaded in ${seconds.toFixed(1)} s, rows_written ${written || "not said"}`);

const { tables } = manifest;
const names = Object.keys(tables).filter((name) => /^[A-Za-z0-9_]+$/.test(name));
const [{ results: [have] }] = await execute(to, "--command", `SELECT ${names.map((name) => `(SELECT count(*) FROM "${name}") AS "${name}"`).join(", ")}`);
const differ = names.filter((name) => have[name] !== tables[name]);
for (const name of differ) console.error(`COUNT DIFFERS ${name}: the manifest says ${tables[name]}, the store has ${have[name]}`);
console.log(differ.length ? `${differ.length} table(s) differ` : `all ${names.length} tables hold what the manifest says (${names.reduce((n, name) => n + tables[name], 0)} rows)`);
process.exit(differ.length ? 1 : 0);
