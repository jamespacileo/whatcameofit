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

// Loaded as D1 was seen to: a file at a time, every statement on its own, foreign keys
// checked at once, and no PRAGMA to defer them.
function loadStrictly(schema, folder) {
  const db = new DatabaseSync(":memory:");
  db.exec(schema);
  db.exec("PRAGMA foreign_keys = ON");
  const files = readdirSync(folder).filter((name) => name.endsWith(".sql")).sort();
  for (const file of files) {
    const text = readFileSync(join(folder, file), "utf8");
    assert.ok(!text.includes("defer_foreign_keys"), `${file} leans on deferred checks`);
    for (const statement of text.split(/;\n(?=INSERT INTO|UPDATE|$)/)) if (statement.trim()) db.exec(statement);
  }
  return { db, files };
}

test("a child never lands in a file, or a statement, before its parent", () => {
  // The child table is created first, and each row of `tree` has a lower id than its parent.
  const schema = `CREATE TABLE leaf (id INTEGER PRIMARY KEY, tree_id INTEGER NOT NULL REFERENCES tree (id), run TEXT NOT NULL REFERENCES job (name)) STRICT;
CREATE TABLE tree (id INTEGER PRIMARY KEY, into_id INTEGER REFERENCES tree (id), run TEXT NOT NULL REFERENCES job (name)) STRICT;
CREATE TABLE job (name TEXT PRIMARY KEY) STRICT;`;
  const path = join(dir, "order.sqlite");
  const db = new DatabaseSync(path, { enableForeignKeyConstraints: false });
  db.exec(schema);
  db.prepare("INSERT INTO job VALUES ('r1')").run();
  for (const [id, into] of [[1, 2], [2, 3], [3, 4], [4, null], [5, 5], [6, null], [7, 1]]) db.prepare("INSERT INTO tree VALUES (?, ?, 'r1')").run(id, into);
  for (let id = 1; id <= 7; id += 1) db.prepare("INSERT INTO leaf VALUES (?, ?, 'r1')").run(id, id);
  const out = join(dir, "order");
  const done = dump(path, join(out, "store.sql"), "--rows-a-file", "2");
  assert.equal(done.status, 0, done.stderr);
  const manifest = JSON.parse(readFileSync(join(out, "manifest.json"), "utf8"));
  assert.deepEqual(manifest.deferred, []);
  assert.deepEqual(manifest.files.map((file) => file.tables.join("+")), ["job+tree", "tree", "tree", "tree", "leaf", "leaf", "leaf", "leaf"]);
  const { db: loaded, files } = loadStrictly(schema, out);
  assert.equal(files.length, 8);
  for (const table of ["job", "tree", "leaf"]) {
    assert.deepEqual(loaded.prepare(`SELECT * FROM ${table} ORDER BY 1`).all(), db.prepare(`SELECT * FROM ${table} ORDER BY 1`).all(), table);
  }
  // Rows that point at each other in a ring cannot be put parents first: the dump says so.
  db.exec("PRAGMA foreign_keys = OFF; UPDATE tree SET into_id = 7 WHERE id = 4");
  const ring = dump(path, join(out, "store.sql"), "--rows-a-file", "2");
  assert.equal(ring.status, 1);
  assert.match(ring.stderr, /tree holds 7 rows but 2 could be ordered parents first/);
  assert.deepEqual(readdirSync(out), []);
  // Two tables that point at each other are kept in one file, named, with checks deferred.
  const cycle = join(dir, "cycle.sqlite");
  const both = new DatabaseSync(cycle, { enableForeignKeyConstraints: false });
  both.exec(`CREATE TABLE a (id INTEGER PRIMARY KEY, b_id INTEGER REFERENCES b (id)) STRICT; CREATE TABLE b (id INTEGER PRIMARY KEY, a_id INTEGER REFERENCES a (id)) STRICT;
    CREATE TABLE c (id INTEGER PRIMARY KEY) STRICT;`);
  for (let id = 1; id <= 5; id += 1) { both.prepare("INSERT INTO a VALUES (?, ?)").run(id, id); both.prepare("INSERT INTO b VALUES (?, ?)").run(id, id); both.prepare("INSERT INTO c VALUES (?)").run(id); }
  const cyclic = dump(cycle, join(out, "store.sql"), "--rows-a-file", "2");
  assert.equal(cyclic.status, 0, cyclic.stderr);
  const said = JSON.parse(readFileSync(join(out, "manifest.json"), "utf8"));
  assert.deepEqual(said.deferred, ["a", "b"]);
  assert.deepEqual(said.files.at(-1).tables, ["a", "b"]);
  assert.match(readFileSync(join(out, said.files.at(-1).name), "utf8"), /^PRAGMA defer_foreign_keys = true;/);
});

// A store shaped like the real one, made through store/merge.sql, holding what stopped
// the first loads: a merged claim that points at a later claim, an icon of 93 KB, two
// articles of one claim at one address, and tables cut across files.
test("the faults of the first real loads, in one store of the real schema", async () => {
  const { INGEST, MERGE } = await import("../src/sql.generated.mjs");
  const path = join(dir, "real.sqlite");
  const db = new DatabaseSync(path);
  db.exec(readFileSync(here("../../schema.sql"), "utf8"));
  const T = "2026-11-01T00:00:00.000000+00:00";
  const run = (id, records) => {
    const counts = {};
    for (const [kind] of records) counts[kind] = (counts[kind] || 0) + 1;
    db.prepare(INGEST.register_run).run(id, "migration", null, null, "abc1234", T, "0".repeat(64), null);
    db.prepare(INGEST.state_counts).run(id, JSON.stringify(counts));
    db.prepare(INGEST.stage).run(id, JSON.stringify(records.map(([kind, key, body]) => ({ kind, key, body }))));
    db.exec("BEGIN");
    for (const sql of MERGE) { const s = db.prepare(sql); if (sql.includes("?1")) s.run(id); else s.run(); }
    db.exec("COMMIT");
    assert.equal(db.prepare("SELECT status FROM run WHERE id = ?").get(id).status, "merged", id);
  };
  const claim = (slug) => ["claim", slug, { slug, headline: `Report on ${slug}`, summary: "s", vertical: "metabolic", indication: "obesity", origin: "backfill", created_at: T,
    review_state: "approved", reviewed_by: "rule", reviewed_at: T }];
  const article = (slug, key) => ["source_article", `${slug}|${key}`, { slug, url_key: key, url: "https://outlet.example/story?ref=1", outlet: "outlet.example", title: "t", published_date: "2026-10-01" }];
  const icon = Buffer.from(bytes(93_062, 7)).toString("hex");
  run("r1", [claim("first-gone"), claim("second-kept"), ...Array.from({ length: 9 }, (_, i) => claim(`other-${i}`)),
    article("second-kept", "outlet.example/story"), article("second-kept", "outlet.example/story-amp"),
    ["outlet_icon", "outlet.example", { domain: "outlet.example", icon_url: "https://outlet.example/i.png", media_type: "image/png", content_hex: icon, fetched_at: T }]]);
  run("r2", [["action", "merge|first-gone", { action: "merge", slug: "first-gone", into_slug: "second-kept", decided_by: "human", at: T }]]);
  db.exec("DELETE FROM stg");
  const merged = db.prepare("SELECT id, merged_into FROM claim WHERE slug = 'first-gone'").get();
  assert.ok(merged.merged_into > merged.id, "the merged claim points at a later claim");
  assert.equal(db.prepare("SELECT length(content) AS n FROM outlet_icon").get().n, 93_062);
  assert.equal(db.prepare("SELECT count(*) AS n FROM source_article").get().n, 2);

  const out = join(dir, "real");
  const done = dump(path, join(out, "store.sql"), "--rows-a-file", "3");
  assert.equal(done.status, 0, done.stderr);
  const manifest = JSON.parse(readFileSync(join(out, "manifest.json"), "utf8"));
  assert.ok(manifest.files.filter((file) => file.tables.includes("claim")).length >= 3, "the claims are cut across files");
  assert.equal(manifest.rows_written_in_parts, 1);
  assert.equal(manifest.tables.claim, 11);
  // The strict replay against the real migrations: each statement alone, checks at once.
  const scratch = join(dir, "real-scratch.sqlite");
  const checked = spawnSync(process.execPath, [here("../scripts/check-dump.mjs"), out, "--scratch", scratch], { encoding: "utf8" });
  assert.equal(checked.status, 0, checked.stdout + checked.stderr);
  assert.match(checked.stdout, /no foreign key broken/);
  const loaded = new DatabaseSync(scratch, { readOnly: true });
  for (const sql of ["SELECT slug, merged_into FROM claim ORDER BY id", "SELECT claim_id, url_key, url FROM source_article ORDER BY id",
    "SELECT domain, hex(content) FROM outlet_icon", "SELECT action, decided_by FROM claim_action ORDER BY id"]) {
    assert.deepEqual(loaded.prepare(sql).all(), db.prepare(sql).all(), sql);
  }
});

// D1 answers at most 100 columns a statement, which the local engine does not hold to.
test("no checksum statement asks D1 for more than 90 columns, on the real schema", async () => {
  const { MAX_RESULT_COLUMNS, fingerprint } = await import("../scripts/fingerprint.mjs");
  const db = new DatabaseSync(":memory:");
  for (const file of readdirSync(here("../migrations")).sort()) db.exec(readFileSync(here(`../migrations/${file}`), "utf8"));
  db.exec(`CREATE TABLE wide (${Array.from({ length: 70 }, (_, i) => `c${i} TEXT`).join(", ")})`);
  db.prepare(`INSERT INTO wide (c0, c69) VALUES ('first', 'last')`).run();
  const tables = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND sql NOT LIKE 'CREATE VIRTUAL%' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts_%'").all().map((row) => row.name);
  assert.ok(tables.length > 40);
  let most = 0, split = 0;
  for (const table of tables) {
    const columns = db.prepare(`PRAGMA table_xinfo("${table}")`).all().filter((column) => column.hidden === 0).map((column) => column.name);
    const parts = fingerprint(table, columns);
    if (parts.length > 1) split += 1;
    const seen = new Set();
    for (const sql of parts) {
      assert.ok(Buffer.byteLength(sql) < 100_000, `${table}: a statement of ${Buffer.byteLength(sql)} bytes`);
      const answered = db.prepare(sql).columns().map((column) => column.name);
      most = Math.max(most, answered.length);
      assert.ok(answered.length <= MAX_RESULT_COLUMNS, `${table}: ${answered.length} columns in one answer`);
      for (const name of answered) if (name !== "rows") { assert.ok(!seen.has(name), `${table}: ${name} twice`); seen.add(name); }
    }
    assert.equal(seen.size, columns.length * 3, `${table}: every column has its three figures`);
  }
  assert.ok(most > 60 && split >= 1, "a table of many columns is spread over statements");
  assert.equal(fingerprint("wide", Array.from({ length: 70 }, (_, i) => `c${i}`)).length, 3);
});

// A payload at the row's bound (the schema's CHECK on payload.body, in bytes) is a row far
// longer than a statement: it is written in parts, every part passes the CHECK, and it
// comes back whole.
test("a payload at the row's bound is dumped in parts and comes back whole", async () => {
  const { INLINE_PAYLOAD_BYTES } = await import("../src/sql.generated.mjs");
  const table = /CREATE TABLE payload \([\s\S]*?\n\) STRICT;/.exec(readFileSync(here("../../schema.sql"), "utf8"))[0].replace("REFERENCES run (id)", "");
  assert.match(table, new RegExp(`<= ${INLINE_PAYLOAD_BYTES}\\)`));
  const path = join(dir, "bound.sqlite");
  const db = new DatabaseSync(path);
  db.exec(table);
  const body = ('{"text":"it\'s ' + 'naïve 日本語 "quoted" '.repeat(40_000)).slice(0, 300_000);
  const exact = body + "x".repeat(INLINE_PAYLOAD_BYTES - Buffer.byteLength(body));
  assert.equal(Buffer.byteLength(exact), INLINE_PAYLOAD_BYTES);
  db.prepare("INSERT INTO payload (sha256, bytes, body, added_run) VALUES (?, ?, ?, 'r1')").run("a".repeat(64), INLINE_PAYLOAD_BYTES, exact);
  assert.throws(() => db.prepare("INSERT INTO payload (sha256, bytes, body, added_run) VALUES (?, ?, ?, 'r1')").run("b".repeat(64), INLINE_PAYLOAD_BYTES + 1, `${exact}y`), /CHECK/);
  const out = join(dir, "bound");
  const done = dump(path, join(out, "store.sql"));
  assert.equal(done.status, 0, done.stderr);
  const manifest = JSON.parse(readFileSync(join(out, "manifest.json"), "utf8"));
  assert.deepEqual([manifest.rows, manifest.rows_written_in_parts], [1, 1]);
  assert.ok(manifest.statements >= 6, "one row, many statements");
  const loaded = new DatabaseSync(":memory:");
  loaded.exec(table);
  for (const statement of readFileSync(join(out, "store.sql"), "utf8").split(/;\n(?=INSERT INTO|UPDATE|$)/)) {
    if (!statement.trim()) continue;
    assert.ok(Buffer.byteLength(statement) < 100_000);
    loaded.exec(statement);
  }
  assert.equal(loaded.prepare("SELECT body FROM payload").get().body, exact);
});
