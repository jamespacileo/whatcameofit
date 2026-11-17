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
// And what the schema needs: a generated column is never written, so every INSERT names
// its columns; the search tables are filled by the schema's triggers as the rows arrive,
// so they and their shadow tables are left out; so are staged records and the tables
// Wrangler and D1 keep for themselves.
//
// Order. D1 checks foreign keys statement by statement: `PRAGMA defer_foreign_keys` did
// not hold through a file of 400 MB on D1 itself (17 November 2026), so nothing here
// leans on it. Tables are written parents first by the schema's foreign keys, whatever
// order they were created in. In a table that points at itself (a merged claim at the
// claim it went into) rows are written parents first too, since a child's INSERT may be
// a statement or a file before its parent's. Tables whose foreign keys form a cycle, or
// that point at themselves in a way this cannot order, are named in the output
// (`deferred`), kept together in one file and given the PRAGMA: that is the best that
// can be done for them and it may fail on D1. store/schema.sql has none.
//
// A row too long for one statement is written in parts: an INSERT that holds the start
// of each long value, then UPDATEs that append the rest, found by the row's primary key
// (`content = CAST(content || X'..' AS BLOB)`, and without the cast for a text). Before such a row is written, its statements are run
// on a scratch copy of the table and the row read back, so a CHECK that a part of a
// value would break stops the dump here and not the load.
//
// Beside the output it writes manifest.json: each table's rows (rows, not statements) and
// the files. Put the output in a folder of its own. Files are written under a name ending
// `.partial` and named `.sql` only when the whole dump is done, with the manifest; a dump
// that fails removes what it wrote, so a folder never looks complete when it is not.
import { createHash } from "node:crypto";
import { once } from "node:events";
import { createReadStream, createWriteStream, existsSync, mkdirSync, readdirSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { DatabaseSync } from "node:sqlite";

const [source, out] = process.argv.slice(2);
const flag = process.argv.indexOf("--rows-a-file");
const rowsAFile = flag > 0 ? Number(process.argv[flag + 1]) : Infinity;
if (!source || !out || out.startsWith("--")) { console.error("usage: dump-for-import.mjs <store.sqlite> <out.sql> [--rows-a-file N]"); process.exit(2); }

const MAX_STATEMENT_BYTES = 90_000;
const LEFT_OUT = /^(sqlite_|_cf_|d1_migrations$|stg$|merging$|ingest_chunk$|inbox$|inbox_folded$)/;
const quote = (name) => `"${name.replaceAll('"', '""')}"`;
const size = (text) => Buffer.byteLength(text);

function literal(value) {
  if (value === null) return "NULL";
  if (typeof value === "number" || typeof value === "bigint") return String(value);
  if (value instanceof Uint8Array) return `X'${Buffer.from(value).toString("hex")}'`;
  return `'${String(value).replaceAll("'", "''")}'`;
}

// A long value cut into pieces whose literals are each at most `first`, then `rest`,
// bytes. A text is cut between characters, never inside one.
function pieces(value, first, rest) {
  const parts = [];
  if (value instanceof Uint8Array) {
    for (let at = 0, room = first; at < value.length; room = rest) {
      const take = Math.max(1, Math.floor((room - 3) / 2));
      parts.push(value.subarray(at, at + take));
      at += take;
    }
    return parts;
  }
  let part = "", bytes = 2, room = first;
  for (const character of value) {
    const cost = character === "'" ? 2 : size(character);
    if (part && bytes + cost > room) { parts.push(part); part = ""; bytes = 2; room = rest; }
    part += character; bytes += cost;
  }
  if (part) parts.push(part);
  return parts;
}

const base = basename(out).replace(/\.sql$/, "");
const folder = dirname(out);
const ours = (name) => name === "manifest.json" || ((name.startsWith(`${base}.`) || name === base) && /\.sql(\.partial)?$/.test(name));
const clear = () => { for (const name of existsSync(folder) ? readdirSync(folder) : []) if (ours(name)) rmSync(join(folder, name), { force: true }); };

async function dump() {
  const db = new DatabaseSync(source, { readOnly: true });
  const virtual = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND sql LIKE 'CREATE VIRTUAL TABLE%'").all().map((row) => row.name);
  const tables = db.prepare("SELECT name, sql FROM sqlite_master WHERE type = 'table' ORDER BY rowid").all()
    .filter(({ name }) => !LEFT_OUT.test(name) && !virtual.some((v) => name === v || name.startsWith(`${v}_`)));

  // Each table's parents, by the schema's foreign keys.
  const names = tables.map(({ name }) => name);
  const keysOf = Object.fromEntries(names.map((name) => [name, db.prepare(`PRAGMA foreign_key_list(${quote(name)})`).all()]));
  const parents = Object.fromEntries(names.map((name) => [name, new Set(keysOf[name].map((key) => key.table).filter((parent) => parent !== name && names.includes(parent)))]));
  // Parents first: a table is written once all its parents are; ties keep the schema's order.
  const ordered = [];
  for (let moved = true; moved;) {
    moved = false;
    for (const name of names) {
      if (ordered.includes(name) || ![...parents[name]].every((parent) => ordered.includes(parent))) continue;
      ordered.push(name); moved = true;
    }
  }
  // What is left points at itself through other tables: a cycle. It goes last, together.
  const deferred = names.filter((name) => !ordered.includes(name));
  // How a table that points at itself is read parents first, or null when it cannot be.
  function selfOrder(name, columns) {
    const own = keysOf[name].filter((key) => key.table === name);
    if (!own.length) return "";
    const ids = new Set(own.map((key) => key.id));
    const pk = db.prepare(`PRAGMA table_xinfo(${quote(name)})`).all().filter((column) => column.pk > 0).map((column) => column.name);
    if (ids.size !== 1 || own.length !== 1 || pk.length !== 1) return null;
    const [{ from, to }] = own;
    const target = quote(to || pk[0]);
    return `WITH RECURSIVE up (k, depth) AS (
      SELECT ${target}, 0 FROM ${quote(name)} WHERE ${quote(from)} IS NULL OR ${quote(from)} = ${target}
      UNION ALL
      SELECT t.${target}, up.depth + 1 FROM ${quote(name)} t JOIN up ON t.${quote(from)} = up.k WHERE t.${quote(from)} <> t.${target})
    SELECT ${columns.map((column) => `t.${quote(column)}`).join(", ")} FROM ${quote(name)} t JOIN up ON up.k = t.${target} ORDER BY up.depth, t.${quote(pk[0])}`;
  }

  const written = [], held = {};
  let file = 0, inFile = 0, stream = null, total = 0, statements = 0, longest = 0, inParts = 0;
  const name = () => (rowsAFile === Infinity ? `${base}.sql` : `${base}.${String(file).padStart(4, "0")}.sql`);
  const close = async () => { if (stream) { stream.end(); await once(stream, "finish"); stream = null; } };
  async function open() {
    await close();
    file += 1; inFile = 0;
    written.push(name());
    held[name()] = new Set();
    stream = createWriteStream(join(folder, `${name()}.partial`));
  }
  async function write(text) {
    const bytes = size(text);
    if (bytes > 100_000) throw new Error(`a statement of ${bytes} bytes was about to be written: over D1's 100,000`);
    longest = Math.max(longest, bytes); statements += 1;
    if (!stream.write(text)) await once(stream, "drain");
  }

  await open();
  const counts = {};
  const created = Object.fromEntries(tables.map(({ name, sql }) => [name, sql]));
  let together = false;
  for (const table of [...ordered, ...deferred]) {
    if (deferred.includes(table) && !together) {
      // The tables of a cycle start a file of their own, which is not cut until they end.
      together = true;
      if (inFile) await open();
      stream.write("PRAGMA defer_foreign_keys = true;\n");
    }
    // hidden 2 and 3 are generated columns.
    const info = db.prepare(`PRAGMA table_xinfo(${quote(table)})`).all().filter((column) => column.hidden === 0);
    const columns = info.map((column) => column.name);
    const keys = info.filter((column) => column.pk > 0).map((column) => column.name);
    const insert = `INSERT INTO ${quote(table)} (${columns.map(quote).join(", ")}) VALUES\n`;
    const head = size(insert);

    // The statements for one row that does not fit: an INSERT, then appends by primary key.
    function inPartsOf(row) {
      if (!keys.length) throw new Error(`a row of ${table} is too long for one statement and the table has no primary key to find it by`);
      const where = ` WHERE ${keys.map((key) => `${quote(key)} = ${literal(row[key])}`).join(" AND ")};\n`;
      const long = (column) => !keys.includes(column) && (typeof row[column] === "string" || row[column] instanceof Uint8Array);
      const cost = Object.fromEntries(columns.map((column) => [column, size(literal(row[column]))]));
      // The longest values are cut until the rest of the row fits beside their starts.
      const cut = [];
      const fixed = () => head + 4 + columns.reduce((sum, column) => sum + 2 + (cut.includes(column) ? 0 : cost[column]), 0);
      for (const column of columns.filter(long).sort((a, b) => cost[b] - cost[a])) {
        if (fixed() + cut.length * 200 <= MAX_STATEMENT_BYTES && cut.length) break;
        cut.push(column);
      }
      const share = Math.floor((MAX_STATEMENT_BYTES - fixed()) / Math.max(cut.length, 1));
      if (!cut.length || share < 16) throw new Error(`a row of ${table} is too long for one statement even with its long values cut`);
      const parts = Object.fromEntries(cut.map((column) => {
        const append = size(`UPDATE ${quote(table)} SET ${quote(column)} = CAST(${quote(column)} ||  AS BLOB)`) + size(where);
        return [column, pieces(row[column], share, MAX_STATEMENT_BYTES - append)];
      }));
      const out = [`${insert}(${columns.map((column) => literal(cut.includes(column) ? parts[column][0] : row[column])).join(", ")});\n`];
      for (const column of cut) {
        // `||` gives a text even of two BLOBs, which a STRICT table refuses in a BLOB
        // column, so a BLOB's append is cast back; the bytes are the same.
        const blob = row[column] instanceof Uint8Array;
        for (const part of parts[column].slice(1)) {
          out.push(`UPDATE ${quote(table)} SET ${quote(column)} = ${blob ? "CAST(" : ""}${quote(column)} || ${literal(part)}${blob ? " AS BLOB)" : ""}${where}`);
        }
      }
      // Tried on a scratch copy of the table: every step must pass its CHECKs, and the
      // row at the end must be the row that was read.
      const scratch = new DatabaseSync(":memory:");
      try {
        scratch.exec("PRAGMA foreign_keys = OFF");
        scratch.exec(created[table]);
        for (const statement of out) scratch.exec(statement);
        const select = `SELECT ${columns.map((column) => `hex(${quote(column)}) AS ${quote(column)}, typeof(${quote(column)}) AS ${quote(`type of ${column}`)}`).join(", ")} FROM ${quote(table)}`;
        const got = scratch.prepare(select).get();
        const want = db.prepare(`${select} WHERE ${keys.map((key) => `${quote(key)} IS ?`).join(" AND ")}`).get(...keys.map((key) => row[key]));
        if (JSON.stringify(got) !== JSON.stringify(want)) throw new Error("written in parts, the row does not come back as it was");
      } catch (error) {
        throw new Error(`a row of ${table} is too long for one statement and cannot be written in parts: ${error.message}`);
      } finally { scratch.close(); }
      return out;
    }

    let rows = [], bytes = head;
    const flush = async () => {
      if (!rows.length) return;
      await write(`${insert}${rows.join(",\n")};\n`);
      rows = []; bytes = head;
    };
    counts[table] = 0;
    let order = selfOrder(table, columns);
    if (order === null && !deferred.includes(table)) {
      // It points at itself in a way that cannot be ordered here: one file, checks deferred.
      deferred.push(table);
      await flush();
      if (inFile) await open();
      stream.write("PRAGMA defer_foreign_keys = true;\n");
    }
    const whole = deferred.includes(table);
    const all = db.prepare(order || `SELECT ${columns.map(quote).join(", ")} FROM ${quote(table)}`);
    all.setReadBigInts(true);
    for (const row of all.iterate()) {
      if (inFile >= rowsAFile && !whole) { await flush(); await open(); }
      held[name()].add(table);
      const text = `(${columns.map((column) => literal(row[column])).join(", ")})`;
      const length = size(text) + 2;
      if (head + length > MAX_STATEMENT_BYTES) {
        await flush();
        for (const statement of inPartsOf(row)) await write(statement);
        inParts += 1;
      } else {
        if (bytes + length > MAX_STATEMENT_BYTES) await flush();
        rows.push(text); bytes += length;
      }
      inFile += 1; total += 1; counts[table] += 1;
    }
    await flush();
    // A row that points at itself in a ring is never reached by the ordered read.
    const there = db.prepare(`SELECT count(*) AS n FROM ${quote(table)}`).get().n;
    if (counts[table] !== Number(there)) throw new Error(`${table} holds ${there} rows but ${counts[table]} could be ordered parents first: some point at each other in a ring`);
  }
  await close();
  db.close();

  // Only now is the folder made to look like a dump: the files take their names and the
  // manifest is written last.
  const rowsOf = Object.fromEntries(Object.entries(counts).filter(([, n]) => n));
  const files = [];
  for (const name of written) {
    const hash = createHash("sha256");
    for await (const chunk of createReadStream(join(folder, `${name}.partial`))) hash.update(chunk);
    files.push({ name, sha256: hash.digest("hex"), tables: [...held[name]] });
  }
  for (const name of written) renameSync(join(folder, `${name}.partial`), join(folder, name));
  writeFileSync(join(folder, "manifest.json"), JSON.stringify({ rows: total, statements, rows_written_in_parts: inParts, tables: rowsOf, deferred, files }, null, 1) + "\n");
  console.log(JSON.stringify({ files: file, rows: total, statements, rows_written_in_parts: inParts, longest_statement_bytes: longest, deferred, tables: rowsOf }));
}

// What an earlier dump left under this name goes first, so old files never mix with new.
mkdirSync(folder, { recursive: true });
clear();
try { await dump(); } catch (error) {
  clear();
  console.error(`the dump failed and left no file: ${error.message}`);
  process.exit(1);
}
