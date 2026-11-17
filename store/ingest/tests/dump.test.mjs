// The dump for D1's import (scripts/dump-for-import.mjs), on SQLite alone: a row too long
// for one statement is written in parts and comes back as it was, no statement passes
// D1's 100,000 bytes, the manifest counts rows, and a dump that fails leaves no file.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { after, test } from "node:test";
import { fileURLToPath } from "node:url";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const dir = mkdtempSync(join(tmpdir(), "thenwhat-dump-"));
after(() => rmSync(dir, { recursive: true, force: true }));
const dump = (store, out, ...more) => spawnSync(process.execPath, [here("../scripts/dump-for-import.mjs"), store, out, ...more], { encoding: "utf8" });

// The icon table as store/schema.sql has it, and tables made up to hold what it does not:
// a long text with characters of several bytes and quotes, two long values in one row, a
// key of two columns, a generated column, and a CHECK that half a value breaks.
const ICON = /CREATE TABLE outlet_icon \([\s\S]*?\n\) STRICT, WITHOUT ROWID;/.exec(readFileSync(here("../../schema.sql"), "utf8"))[0].replace("REFERENCES run (id)", "");
const SCHEMA = `${ICON}
CREATE TABLE note (place TEXT NOT NULL, n INTEGER NOT NULL, words TEXT NOT NULL CHECK (length(words) > 0), raw BLOB,
  size INTEGER GENERATED ALWAYS AS (length(words)) VIRTUAL, PRIMARY KEY (place, n)) STRICT;
CREATE TABLE small (id INTEGER PRIMARY KEY, name TEXT) STRICT;`;
const bytes = (n, seed) => Uint8Array.from({ length: n }, (_, i) => (i * 31 + seed) % 256);
const words = (n) => Array.from({ length: n }, (_, i) => ["it's", "naïve", "日本語", "😀", "plain"][i % 5]).join(" ");

function store(path, extra = "") {
  const db = new DatabaseSync(path);
  db.exec(SCHEMA + extra);
  const icon = db.prepare("INSERT INTO outlet_icon VALUES (?, ?, ?, ?, ?, ?)");
  icon.run("small.example", "https://small.example/i.png", "image/png", bytes(900, 1), "2026-11-01T00:00:00.000000+00:00", "r1");
  icon.run("large.example", "https://large.example/i.png", "image/png", bytes(93_062, 2), "2026-11-01T00:00:00.000000+00:00", "r1");
  icon.run("none.example", null, null, null, "2026-11-01T00:00:00.000000+00:00", "r1");
  const note = db.prepare("INSERT INTO note (place, n, words, raw) VALUES (?, ?, ?, ?)");
  note.run("a", 1, "short", null);
  note.run("a's", 2, words(60_000), bytes(70_000, 3));
  note.run("b", 3, words(30_000), null);
  for (let i = 0; i < 500; i += 1) db.prepare("INSERT INTO small VALUES (?, ?)").run(i, `name ${i}`);
  return db;
}
const everything = (db) => ["outlet_icon", "note", "small"].map((table) => db.prepare(`SELECT * FROM ${table} ORDER BY 1, 2`).all());

test("a row too long for one statement is written in parts and comes back as it was", () => {
  const source = store(join(dir, "store.sqlite"));
  const out = join(dir, "out");
  const done = dump(join(dir, "store.sqlite"), join(out, "store.sql"), "--rows-a-file", "300");
  assert.equal(done.status, 0, done.stderr);
  const manifest = JSON.parse(readFileSync(join(out, "manifest.json"), "utf8"));
  assert.deepEqual(manifest.tables, { outlet_icon: 3, note: 3, small: 500 }, "the manifest counts rows, not statements");
  assert.equal(manifest.rows, 506);
  assert.equal(manifest.rows_written_in_parts, 3);
  const files = readdirSync(out).filter((name) => name.endsWith(".sql")).sort();
  assert.deepEqual(files, manifest.files.map((file) => file.name));
  assert.ok(files.length >= 2 && !readdirSync(out).some((name) => name.endsWith(".partial")));
  // Loaded as D1 would, a statement at a time, into the schema alone.
  const loaded = new DatabaseSync(":memory:");
  loaded.exec(SCHEMA);
  let longest = 0, statements = 0;
  for (const file of files) {
    const text = readFileSync(join(out, file), "utf8");
    assert.ok(!/BEGIN TRANSACTION|COMMIT/.test(text.replace(/'(?:[^']|'')*'/g, "")));
    for (const statement of text.split(/;\n(?=INSERT INTO|UPDATE|PRAGMA|$)/)) {
      if (!statement.trim()) continue;
      longest = Math.max(longest, Buffer.byteLength(statement) + 2);
      statements += 1;
      loaded.exec(statement);
    }
  }
  assert.ok(longest <= 100_000, `the longest statement is ${longest} bytes`);
  assert.ok(statements > manifest.rows_written_in_parts + 3, "the long rows took more statements than rows");
  assert.deepEqual(everything(loaded), everything(source));
  assert.equal(loaded.prepare("SELECT length(content) AS n FROM outlet_icon WHERE domain = 'large.example'").get().n, 93_062);
});

test("a dump that fails leaves nothing that looks like a dump, and clears what an earlier one left", () => {
  // A long value whose every part must be whole JSON cannot be written in parts.
  const path = join(dir, "strict.sqlite");
  const db = store(path, "CREATE TABLE doc (id INTEGER PRIMARY KEY, body TEXT CHECK (json_valid(body))) STRICT;");
  db.prepare("INSERT INTO doc VALUES (1, ?)").run(JSON.stringify({ text: "x".repeat(120_000) }));
  db.close();
  const out = join(dir, "failed");
  assert.equal(dump(join(dir, "store.sqlite"), join(out, "store.sql"), "--rows-a-file", "300").status, 0);
  writeFileSync(join(out, "notes.txt"), "not the dump's");
  const failed = dump(path, join(out, "store.sql"), "--rows-a-file", "300");
  assert.equal(failed.status, 1);
  assert.match(failed.stderr, /a row of doc is too long for one statement and cannot be written in parts/);
  assert.ok(!failed.stderr.includes("xxxxxxxx"), "the failure does not repeat the value");
  assert.deepEqual(readdirSync(out), ["notes.txt"], "no SQL file and no manifest are left, and nothing else is touched");
  // A long row in a table with no primary key has nothing to be found by.
  const bare = join(dir, "bare.sqlite");
  const other = new DatabaseSync(bare);
  other.exec("CREATE TABLE loose (words TEXT)");
  other.prepare("INSERT INTO loose VALUES (?)").run("y".repeat(120_000));
  other.close();
  assert.match(dump(bare, join(out, "store.sql")).stderr, /no primary key/);
  assert.deepEqual(readdirSync(out), ["notes.txt"]);
});
