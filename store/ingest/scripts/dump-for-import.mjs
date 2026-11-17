// Writes a store held in a SQLite file as SQL that `wrangler d1 execute --file` takes:
// the rows only, for a database that already has migrations/ applied.
//
//   node scripts/dump-for-import.mjs <store.sqlite> <out.sql> [--rows-a-file N]
//
// What Cloudflare's import refuses or bounds, read on 2026-11-17
// (developers.cloudflare.com/d1/best-practices/import-export-data, .../d1/platform/limits):
//   - no BEGIN TRANSACTION or COMMIT in the file;
//   - a statement is at most 100,000 bytes, so rows are grouped into INSERTs under 90,000;
//   - a file is at most 5 GiB; `--rows-a-file` splits the output into out.0001.sql, ...
// Beside the output it writes manifest.json, each table's rows, so put the output in a
// folder of its own.
// And what the schema needs: a generated column is never written, so every INSERT names
// its columns; the search tables are filled by the schema's triggers as the rows arrive,
// so they and their shadow tables are left out; so are staged records and the tables
// Wrangler and D1 keep for themselves.
import { createWriteStream, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { once } from "node:events";
import { DatabaseSync } from "node:sqlite";

const [source, out] = process.argv.slice(2);
const flag = process.argv.indexOf("--rows-a-file");
const rowsAFile = flag > 0 ? Number(process.argv[flag + 1]) : Infinity;
if (!source || !out) { console.error("usage: dump-for-import.mjs <store.sqlite> <out.sql> [--rows-a-file N]"); process.exit(2); }

const MAX_STATEMENT_BYTES = 90_000;
const LEFT_OUT = /^(sqlite_|_cf_|d1_migrations$|stg$|merging$|ingest_chunk$)/;
const db = new DatabaseSync(source, { readOnly: true });
const quote = (name) => `"${name.replaceAll('"', '""')}"`;

function literal(value) {
  if (value === null) return "NULL";
  if (typeof value === "number" || typeof value === "bigint") return String(value);
  if (value instanceof Uint8Array) return `X'${Buffer.from(value).toString("hex")}'`;
  return `'${String(value).replaceAll("'", "''")}'`;
}

const virtual = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND sql LIKE 'CREATE VIRTUAL TABLE%'").all().map((row) => row.name);
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid").all().map((row) => row.name)
  .filter((name) => !LEFT_OUT.test(name) && !virtual.some((v) => name === v || name.startsWith(`${v}_`)));

let file = 0, inFile = 0, stream = null, total = 0, statements = 0, longest = 0;
const path = () => (rowsAFile === Infinity ? out : out.replace(/(\.sql)?$/, `.${String(file).padStart(4, "0")}.sql`));
async function open() {
  if (stream) { stream.end(); await once(stream, "finish"); }
  file += 1; inFile = 0;
  stream = createWriteStream(path());
  // Parents are written before children, but a row may point at a later row of its own table.
  stream.write("PRAGMA defer_foreign_keys = true;\n");
}
async function write(text) { if (!stream.write(text)) await once(stream, "drain"); }

await open();
const counts = {};
for (const table of tables) {
  // hidden 2 and 3 are generated columns.
  const columns = db.prepare(`PRAGMA table_xinfo(${quote(table)})`).all().filter((column) => column.hidden === 0).map((column) => column.name);
  const head = `INSERT INTO ${quote(table)} (${columns.map(quote).join(", ")}) VALUES\n`;
  let rows = [], bytes = head.length;
  const flush = async () => {
    if (!rows.length) return;
    const text = `${head}${rows.join(",\n")};\n`;
    longest = Math.max(longest, Buffer.byteLength(text));
    await write(text);
    statements += 1; rows = []; bytes = head.length;
  };
  counts[table] = 0;
  const all = db.prepare(`SELECT ${columns.map(quote).join(", ")} FROM ${quote(table)}`);
  all.setReadBigInts(true);
  for (const row of all.iterate()) {
    const text = `(${columns.map((column) => literal(row[column])).join(", ")})`;
    const size = Buffer.byteLength(text) + 2;
    if (size + head.length > 100_000) throw new Error(`a row of ${table} is ${size} bytes: over D1's 100,000 bytes a statement`);
    if (bytes + size > MAX_STATEMENT_BYTES) await flush();
    if (inFile >= rowsAFile) { await flush(); await open(); }
    rows.push(text); bytes += size; inFile += 1; total += 1; counts[table] += 1;
  }
  await flush();
}
stream.end();
await once(stream, "finish");
// What each table should hold after the load, for scripts/import-folder.mjs to count.
const held = Object.fromEntries(Object.entries(counts).filter(([, n]) => n));
writeFileSync(join(dirname(out), "manifest.json"), JSON.stringify({ rows: total, statements, tables: held }, null, 1) + "\n");
console.log(JSON.stringify({ files: file, rows: total, statements, longest_statement_bytes: longest, tables: Object.fromEntries(Object.entries(counts).filter(([, n]) => n)) }));
