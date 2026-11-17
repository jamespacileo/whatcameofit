// Holds the store in D1 to the file it was loaded from, table by table, without fetching
// rows back: one statement a table, run on both, the answers compared.
//
//   node scripts/checksum-d1.mjs --file <hot.sqlite> (--remote | --persist-to <dir>)
//   node scripts/checksum-d1.mjs --checks <checks.json> [--file <hot.sqlite>] (--remote | --persist-to <dir>)
//
// With `--checks`, the statements and the answers expected are the pipeline's
// (`thenwhat store checksum`): {"tables": {"<table>": {"sql": "<one SELECT, one row>",
// "expected": {...}}}}. With `--file` too, each statement is also run on the file, so a
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

const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const file = value("--file"), given = value("--checks");
if ((!file && !given) || (!argv.includes("--remote") && !value("--persist-to"))) { console.error("usage: checksum-d1.mjs (--file <store.sqlite> | --checks <checks.json>) (--remote | --persist-to <dir>)"); process.exit(2); }
const LEFT_OUT = /^(sqlite_|_cf_|d1_migrations$|stg$|merging$|ingest_chunk$|inbox$)/;
const quote = (name) => `"${name.replaceAll('"', '""')}"`;
const M = 1000000007;

// The script's own statement for a table: every figure an integer under 2^53.
export function fingerprint(table, columns) {
  const parts = [`count(*) AS "rows"`];
  const weights = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59];
  for (const column of columns) {
    const c = quote(column), text = `CAST(${c} AS TEXT)`, hex = `hex(CAST(${c} AS BLOB))`;
    // How often each of the sixteen hex digits occurs in the value, weighted: every byte counts.
    const digits = weights.map((weight, digit) => `${weight} * (length(${hex}) - length(replace(${hex}, '${digit.toString(16).toUpperCase()}', '')))`).join(" + ");
    parts.push(`count(${c}) AS ${quote(`${column} set`)}`,
      `coalesce(sum(length(CAST(${c} AS BLOB))), 0) AS ${quote(`${column} bytes`)}`,
      `coalesce(sum((${digits} + coalesce(unicode(substr(${text}, 1, 1)), 0) * 61 + coalesce(unicode(substr(${text}, length(${text}) / 2 + 1, 1)), 0) * 131 + coalesce(unicode(substr(${text}, -1, 1)), 0) * 67) % ${M}) % ${M}, 0) AS ${quote(`${column} sum`)}`);
  }
  return `SELECT ${parts.join(", ")} FROM ${quote(table)}`;
}

const db = file ? new DatabaseSync(file, { readOnly: true }) : null;
let checks;
if (given) checks = Object.entries(JSON.parse(readFileSync(given, "utf8")).tables).map(([table, check]) => ({ table, sql: check.sql, expected: check.expected }));
else {
  const virtual = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND sql LIKE 'CREATE VIRTUAL TABLE%'").all().map((row) => row.name);
  checks = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid").all().map((row) => row.name)
    .filter((name) => !LEFT_OUT.test(name) && !virtual.some((v) => name === v || name.startsWith(`${v}_`)))
    .map((table) => ({ table, sql: fingerprint(table, db.prepare(`PRAGMA table_xinfo(${quote(table)})`).all().filter((column) => column.hidden === 0).map((column) => column.name)) }));
}

const to = target(process.argv);
const started = Date.now();
const same = (a, b) => JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());
const differ = [];
let rows = 0;
// Every statement in one file and one call: Wrangler answers each in turn.
const fit = checks.filter(({ table, sql }) => Buffer.byteLength(sql) <= 100_000 || (differ.push(`${table}: its statement is over D1's 100,000 bytes`), false));
const dir = mkdtempSync(join(tmpdir(), "thenwhat-checksum-"));
writeFileSync(join(dir, "checks.sql"), fit.map(({ sql }) => `${sql.replace(/;\s*$/, "")};`).join("\n") + "\n");
let answers;
try { answers = await execute(to, "--file", join(dir, "checks.sql")); } catch (error) { console.error(`D1 refused the checks: ${error.message.slice(-600)}`); process.exit(1); } finally { rmSync(dir, { recursive: true, force: true }); }
if (!Array.isArray(answers) || answers.length !== fit.length) { console.error("Wrangler did not answer each statement: the checks were not compared"); process.exit(1); }
for (const [at, { table, sql, expected }] of fit.entries()) {
  const inFile = db ? { ...db.prepare(sql).get() } : null;
  const inD1 = answers[at].results?.[0] ?? {};
  const want = expected ?? inFile;
  if (expected && inFile && !same(expected, inFile)) differ.push(`${table}: the file does not give what the checks expect`);
  if (!same(want, inD1)) {
    const which = Object.keys(want).filter((name) => want[name] !== inD1[name]);
    differ.push(`${table}: differs in ${which.slice(0, 6).join(", ")}${which.length > 6 ? ` and ${which.length - 6} more` : ""} (rows: ${want.rows ?? "?"} expected, ${inD1.rows ?? "?"} in D1)`);
  }
  rows += Number(inD1.rows ?? 0);
}
for (const line of differ) console.error(`DIFFERS ${line}`);
console.log(differ.length ? `${differ.length} of ${checks.length} tables differ` : `all ${checks.length} tables in D1 give the ${given ? "expected" : "file's"} checksums (${rows} rows), in ${((Date.now() - started) / 1000).toFixed(1)} s`);
process.exit(differ.length ? 1 : 0);
