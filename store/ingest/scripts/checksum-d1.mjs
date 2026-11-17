// Holds the store in D1 to the file it was loaded from, table by table, without fetching
// rows back: one statement a table, run on both, the answers compared.
//
//   node scripts/checksum-d1.mjs --file <hot.sqlite> (--remote | --persist-to <dir>)
//   node scripts/checksum-d1.mjs --checks <checks.json> [--file <hot.sqlite>] (--remote | --persist-to <dir>)
//
// With `--checks`, the statements and the answers expected are the pipeline's
// (`thenwhat store checksum`): {"tables": {"<table>": {"sql": "<one SELECT, one row>",
// "expected": {...}}}}, or for a table of many columns {"parts": [{"sql", "expected"}, ...]},
// since D1 answers at most 100 columns a statement. With `--file` too, each statement is also run on the file, so a
// wrong expectation shows as such. Without `--checks`, the script's own fingerprint is
// run on both: for each table its rows, and for each column the values that are not
// null, their bytes in all, and a sum over each value of how often each hex digit occurs in it
// and of its first, middle and last character.
// It is made of SQLite's core functions only, since D1 has no SHA; it catches a missing,
// doubled, cut or altered value, but not bytes of one value in another order, and is not
// proof against a deliberate change.
// Tables the file leaves empty are checked too: D1 must hold none of their rows.
// Exit 1 on any difference.
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { execute, target } from "./d1.mjs";
import { MAX_RESULT_COLUMNS, fingerprint } from "./fingerprint.mjs";

const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const file = value("--file"), given = value("--checks");
if ((!file && !given) || (!argv.includes("--remote") && !value("--persist-to"))) { console.error("usage: checksum-d1.mjs (--file <store.sqlite> | --checks <checks.json>) (--remote | --persist-to <dir>)"); process.exit(2); }
const LEFT_OUT = /^(sqlite_|_cf_|d1_migrations$|stg$|merging$|ingest_chunk$|inbox$|inbox_folded$|inbox_fold$)/;
const quote = (name) => `"${name.replaceAll('"', '""')}"`;

const db = file ? new DatabaseSync(file, { readOnly: true }) : null;
let checks;
// A table's check is one statement, or `parts`, several: D1 answers at most 100 columns.
if (given) {
  checks = Object.entries(JSON.parse(readFileSync(given, "utf8")).tables)
    .flatMap(([table, check]) => (check.parts || [check]).map((part, n, all) => ({ table, part: all.length > 1 ? n + 1 : 0, sql: part.sql, expected: part.expected })));
}
else {
  const virtual = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND sql LIKE 'CREATE VIRTUAL TABLE%'").all().map((row) => row.name);
  checks = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid").all().map((row) => row.name)
    .filter((name) => !LEFT_OUT.test(name) && !virtual.some((v) => name === v || name.startsWith(`${v}_`)))
    .flatMap((table) => fingerprint(table, db.prepare(`PRAGMA table_xinfo(${quote(table)})`).all().filter((column) => column.hidden === 0).map((column) => column.name))
      .map((sql, n, all) => ({ table, part: all.length > 1 ? n + 1 : 0, sql })));
}

let to;
try { to = target(process.argv); } catch (error) { console.error(error.message); process.exit(2); }
const started = Date.now();
const same = (a, b) => JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());
const differ = [];
let rows = 0;
const label = ({ table, part }) => (part ? `${table} (part ${part})` : table);
// A statement D1 would refuse is found here when the file is at hand: over 100,000
// bytes, or more result columns than D1 gives.
const fit = checks.filter((check) => {
  if (Buffer.byteLength(check.sql) > 100_000) { differ.push(`${label(check)}: its statement is over D1's 100,000 bytes`); return false; }
  const columns = db ? db.prepare(check.sql).columns().length : Object.keys(check.expected || {}).length;
  if (columns > MAX_RESULT_COLUMNS + 10) { differ.push(`${label(check)}: its statement answers ${columns} columns and D1 gives at most 100; split it into parts`); return false; }
  return true;
});
const d1Says = (error) => /"text":\s*"([^"]*)"/.exec(error.message)?.[1] || error.message.split("\n").find((line) => /error/i.test(line))?.trim().slice(0, 300) || "failed";
// Every statement in one file and one call: Wrangler answers each in turn. When D1
// refuses the file, each statement is asked on its own, so the one refused is named.
const dir = mkdtempSync(join(tmpdir(), "thenwhat-checksum-"));
writeFileSync(join(dir, "checks.sql"), fit.map(({ sql }) => `${sql.replace(/;\s*$/, "")};`).join("\n") + "\n");
let answers = null;
try { answers = await execute(to, "--file", join(dir, "checks.sql")); } catch (error) {
  console.error(`D1 refused the checks as one file (${d1Says(error)}); asking each statement on its own`);
} finally { rmSync(dir, { recursive: true, force: true }); }
if (answers && (!Array.isArray(answers) || answers.length !== fit.length)) answers = null;
const seen = new Set();
for (const [at, check] of fit.entries()) {
  const { table, sql, expected } = check;
  const inFile = db ? { ...db.prepare(sql).get() } : null;
  let inD1 = answers?.[at]?.results?.[0];
  if (!answers) {
    try { [{ results: [inD1] }] = await execute(to, "--command", sql); } catch (error) { differ.push(`${label(check)}: D1 refused the statement: ${d1Says(error)}`); continue; }
  }
  inD1 ??= {};
  const want = expected ?? inFile;
  if (expected && inFile && !same(expected, inFile)) differ.push(`${label(check)}: the file does not give what the checks expect`);
  if (!same(want, inD1)) {
    const which = Object.keys(want).filter((name) => want[name] !== inD1[name]);
    differ.push(`${label(check)}: differs in ${which.slice(0, 6).join(", ")}${which.length > 6 ? ` and ${which.length - 6} more` : ""} (rows: ${want.rows ?? "?"} expected, ${inD1.rows ?? "?"} in D1)`);
  }
  if (!seen.has(table)) { seen.add(table); rows += Number(inD1.rows ?? Object.values(inD1)[0] ?? 0); }
}
const tables = new Set(checks.map((check) => check.table)).size;
for (const line of differ) console.error(`DIFFERS ${line}`);
console.log(differ.length ? `${differ.length} difference(s) in ${tables} tables` : `all ${tables} tables in D1 give the ${given ? "expected" : "file's"} checksums (${rows} rows), in ${((Date.now() - started) / 1000).toFixed(1)} s`);
process.exit(differ.length ? 1 : 0);
