// The lab's page bundle loaded into the pair tables (migration 0011), on D1's local
// engine. The bundle is real: site/tests/bundle holds the pair pages the lab's own
// pipeline test writes from its recorded slice.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { cpSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { Service, engineUnavailable } from "./harness.mjs";
import { chunkedDrops, droppedVersions, scratchBeside, statements, writeStatementFiles, writeStatements } from "../scripts/load-pairs.mjs";
import { Writable } from "node:stream";
import { realpathSync as realpathSync_, symlinkSync } from "node:fs";
import { dirname } from "node:path";
import { writeManifest } from "../scripts/bundle-manifest.mjs";

const skip = (await engineUnavailable()) ?? false;
if (skip && process.env.CI) throw new Error(skip);

const bundle = fileURLToPath(new URL("../../../site/tests/bundle", import.meta.url));
const script = fileURLToPath(new URL("../scripts/load-pairs.mjs", import.meta.url));
const pageFiles = readdirSync(join(bundle, "p12_pair_page"));

let s;
before(async () => { if (!skip) s = await Service.open(); });
after(async () => { if (s) await s.close(); });

const run = async (sql) => { for (const one of sql) await s.db.prepare(one).run(); };
const all = async (sql, ...values) => (await s.db.prepare(sql).bind(...values).all()).results;
const one = async (sql, ...values) => (await all(sql, ...values))[0];
const one_ = one;

test("a bundle is loaded, becomes current, and gives each pair page back as the lab wrote it", { skip }, async () => {
  const load = statements(bundle, { loadedAt: "2026-11-19T00:00:00.000Z" });
  for (const sql of load.sql) assert.ok(Buffer.byteLength(sql) < 100_000 && !sql.includes("\n"), "a statement is one line under D1's limit");
  await run(load.sql);

  assert.deepEqual(await all("SELECT version, current FROM pair_bundle"), [{ version: load.version, current: 1 }]);
  assert.equal((await one("SELECT count(*) AS n FROM pair WHERE version = ?", load.version)).n, pageFiles.length);
  assert.equal(load.counts.pair, pageFiles.length);

  const address = "apitegromab--muscular-atrophy-spinal";
  const parts = await all("SELECT body FROM pair_page WHERE version = ? AND model = 'PairPage' AND key = ? ORDER BY part", load.version, address);
  const written = JSON.parse(readFileSync(join(bundle, "p12_pair_page", `${address}.json`), "utf8"));
  assert.deepEqual(JSON.parse(parts.map((part) => part.body).join("")), written);

  const pair = await one("SELECT * FROM pair WHERE version = ? AND address = ?", load.version, address);
  assert.equal(pair.key, written.row.pair.key);
  assert.equal(pair.status_code, written.row.status.code);
  assert.equal(pair.trials, written.trials.length);
  assert.equal(pair.claim_slug, written.row.origin?.claim_slug ?? null);
  const trials = await all("SELECT nct_id FROM pair_trial WHERE version = ? AND pair_key = ? ORDER BY nct_id", load.version, pair.key);
  assert.deepEqual(trials.map((trial) => trial.nct_id), written.trials.map((trial) => trial.nct_id).sort());

  // An intervention's pairs, as its page lists them: one read by slug.
  const listed = await all(`SELECT p.address FROM pair p JOIN pair_intervention i ON i.version = p.version AND i.id = p.intervention_id
    WHERE p.version = ? AND i.slug = 'apitegromab' ORDER BY p.address`, load.version);
  assert.deepEqual(listed.map((row) => row.address), pageFiles.filter((name) => name.startsWith("apitegromab--")).map((name) => name.slice(0, -5)).sort());
});

test("a second bundle takes over only at its last statements, and the one before is kept", { skip }, async () => {
  const first = (await one("SELECT version FROM pair_bundle WHERE current = 1")).version;
  const smaller = mkdtempSync(join(tmpdir(), "thenwhat-bundle-"));
  try {
    cpSync(bundle, smaller, { recursive: true });
    const dropped = "apitegromab--obesity";
    rmSync(join(smaller, "p12_pair_page", `${dropped}.json`));
    writeManifest(smaller, { madeAt: "2026-11-20T00:00:00Z" });
    const load = statements(smaller, { loadedAt: "2026-11-20T00:00:00.000Z" });
    assert.notEqual(load.version, first);

    // Stopped before the version is marked: readers still have the first bundle, whole.
    const mark = load.sql.findIndex((sql) => sql.startsWith("UPDATE pair_bundle"));
    await run(load.sql.slice(0, mark));
    assert.equal((await one("SELECT version FROM pair_bundle WHERE current = 1")).version, first);
    assert.equal((await one("SELECT count(*) AS n FROM pair WHERE version = ?", first)).n, pageFiles.length);

    // Run again from the start, to the end.
    await run(load.sql);
    assert.equal((await one("SELECT version FROM pair_bundle WHERE current = 1")).version, load.version);
    assert.equal((await one("SELECT count(*) AS n FROM pair WHERE version = ?", load.version)).n, pageFiles.length - 1);
    assert.equal(await one("SELECT 1 AS held FROM pair WHERE version = ? AND address = ?", load.version, dropped), undefined);
    assert.equal((await one("SELECT count(*) AS n FROM pair_bundle")).n, 2);

    // A third leaves two: the first is gone from every table.
    writeFileSync(join(smaller, "p12_pair_page", `${dropped}.json`), readFileSync(join(bundle, "p12_pair_page", `${dropped}.json`)));
    rmSync(join(smaller, "p12_pair_page", "apitegromab--overweight.json"));
    writeManifest(smaller, { madeAt: "2026-11-21T00:00:00Z" });
    const third = statements(smaller, { loadedAt: "2026-11-21T00:00:00.000Z" });
    await run(third.sql);
    assert.deepEqual((await all("SELECT version FROM pair_bundle ORDER BY loaded_at")).map((row) => row.version), [load.version, third.version]);
    assert.equal((await one("SELECT count(*) AS n FROM pair_page WHERE version = ?", first)).n, 0);
  } finally {
    rmSync(smaller, { recursive: true, force: true });
  }
});

test("a folder that differs from its manifest is refused before any statement is made", () => {
  const short = mkdtempSync(join(tmpdir(), "thenwhat-bundle-"));
  try {
    cpSync(bundle, short, { recursive: true });
    rmSync(join(short, "p12_pair_data_file", "apitegromab--obesity.json"));
    const held = readdirSync(join(bundle, "p12_pair_data_file")).length;
    const counted = new RegExp(`the manifest counts ${held} PairDataFile files and ${held - 1} are present`);
    assert.throws(() => statements(short), counted);
    assert.throws(() => execFileSync(process.execPath, [script, short, "--print"], { stdio: "pipe" }), counted);
    writeFileSync(join(short, "p12_pair_data_file", "apitegromab--obesity.json"), "{}");
    assert.throws(() => statements(short), /checksum .* differs from the manifest's/);
  } finally {
    rmSync(short, { recursive: true, force: true });
  }
});

test("a load keeps the current version and the one before unless told to keep more, never fewer", () => {
  assert.throws(() => statements(bundle, { keep: 1 }), /at least 2/);
  const kept = (sql) => sql.find((one) => one.startsWith("DELETE FROM pair_bundle"));
  assert.match(kept(statements(bundle).sql), /LIMIT 2\)/);
  assert.match(kept(statements(bundle, { keep: 10 }).sql), /LIMIT 10\)/);
});

test("the command refuses a folder that holds no page file", () => {
  const empty = mkdtempSync(join(tmpdir(), "thenwhat-bundle-"));
  try {
    assert.throws(() => execFileSync(process.execPath, [script, empty, "--print"], { stdio: "pipe" }), /holds no page file/);
    const printed = execFileSync(process.execPath, [script, bundle, "--print"], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
    assert.match(printed, /INSERT INTO pair \(/);
  } finally {
    rmSync(empty, { recursive: true, force: true });
  }
});

test("a version that falls out is deleted a few rows at a time, each table in as many chunks as its count needs", { skip }, async () => {
  // Three versions in a fresh store's tables, keeping two: the oldest is dropped in chunks of 4.
  const held = async () => all("SELECT version, current, loaded_at, counts FROM pair_bundle");
  const copies = [];
  try {
    const loads = [];
    for (const [at, gone] of [["2026-12-01", "apitegromab--obesity"], ["2026-12-02", "apitegromab--overweight"], ["2026-12-03", null]]) {
      const copy = mkdtempSync(join(tmpdir(), "thenwhat-bundle-"));
      copies.push(copy);
      cpSync(bundle, copy, { recursive: true });
      if (gone) rmSync(join(copy, "p12_pair_page", `${gone}.json`));
      writeManifest(copy, { madeAt: `${at}T00:00:00Z` });
      loads.push(statements(copy, { loadedAt: `${at}T00:00:00.000Z` }));
    }
    for (const load of loads.slice(0, 2)) await run(load.sql);
    const [oldest, , next] = loads;
    const dropped = droppedVersions(await held(), next.version);
    // The rest of the store's versions are older than these three; the oldest of the three is
    // among those dropped, and neither of the two kept after the load is.
    assert.ok(dropped.some((one) => one.version === oldest.version));
    assert.ok(!dropped.some((one) => one.version === loads[1].version || one.version === next.version));
    const chunk = 4;
    const drops = chunkedDrops(dropped, chunk);
    const expected = dropped.reduce((sum, one) => sum + Object.values(one.counts).reduce((n, rows) => n + Math.ceil(rows / chunk), 0), 0);
    assert.equal(drops.length, expected);
    // Run as the command runs them: the new version's rows, its switch, the chunks, then the
    // load's own deletes.
    await run(next.sql.slice(0, next.dropsAt));
    for (const sql of drops) {
      const { meta } = await s.db.prepare(sql).run();
      assert.ok(meta.changes <= chunk, `${meta.changes} rows in one delete`);
    }
    for (const one of dropped) {
      for (const table of Object.keys(one.counts)) assert.equal((await one_(`SELECT count(*) AS n FROM ${table} WHERE version = ?`, one.version)).n, 0, `${table} ${one.version}`);
    }
    await run(next.sql.slice(next.dropsAt));
    assert.deepEqual((await all("SELECT version FROM pair_bundle ORDER BY loaded_at")).map((row) => row.version), [loads[1].version, next.version]);
    assert.equal((await one("SELECT count(*) AS n FROM pair WHERE version = ?", next.version)).n, pageFiles.length);
  } finally {
    for (const copy of copies) rmSync(copy, { recursive: true, force: true });
  }
});

test("a dropped version whose counts the store does not hold is refused, not deleted whole", () => {
  assert.throws(() => chunkedDrops([{ version: "0123456789abcdef", counts: {} }]), /pair_bundle holds no pair_page count for version 0123456789abcdef/);
});

// The statements leave the loader one at a time (writeStatements): joined into one string, a
// full bundle's pass V8's longest string. What is written is still every statement, in order.
test("the printed statements are every statement in order, each ended, written one at a time", () => {
  const printed = execFileSync(process.execPath, [script, bundle, "--print"], { encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });
  const { sql } = statements(bundle);
  // Each run stamps its own loaded_at; everything else is the same text.
  const unstamped = (text) => text.replace(/'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z'/g, "'<loaded at>'");
  assert.equal(unstamped(printed), unstamped(sql.map((statement) => `${statement};\n`).join("")));
  assert.ok(sql.length > 100, "the fixture gives many statements");
});

test("the statements reach the stream one at a time, the writer waiting whenever the stream asks it to", async () => {
  const { sql } = statements(bundle);
  const seen = [];
  let waits = 0;
  // A stream that holds one write before it asks the writer to wait, as a pipe or a slow disk does.
  const slow = new Writable({
    highWaterMark: 1,
    write(chunk, _encoding, done) {
      seen.push(chunk.toString());
      setImmediate(done);
    },
  });
  slow.on("drain", () => { waits += 1; });
  await writeStatements(slow, sql);
  assert.deepEqual(seen, sql.map((statement) => `${statement};\n`));
  assert.ok(waits > 0, "the writer waited on the stream");
});

test("a failing stream fails the write, the last flush included, rather than ending the process", async () => {
  const failing = new Writable({ write(_chunk, _encoding, done) { done(new Error("no space left on device")); } });
  await assert.rejects(writeStatements(failing, ["SELECT 1"]), /no space left on device/);
});

test("statements for the local engine go in bounded files in order, the switch to the new version kept whole in the last", async () => {
  const { sql } = statements(bundle);
  const dir = mkdtempSync(join(tmpdir(), "thenwhat-sql-"));
  try {
    const files = await writeStatementFiles(dir, sql, 64 * 1024);
    assert.ok(files.length > 2, `${files.length} files`);
    const texts = files.map((file) => readFileSync(file, "utf8"));
    assert.equal(texts.join(""), sql.map((statement) => `${statement};\n`).join(""));
    const switchAt = sql.findIndex((statement) => statement.startsWith("UPDATE pair_bundle SET current"));
    assert.ok(texts.at(-1).includes(`${sql[switchAt]};\n${sql[switchAt + 1]};\n`));
    for (const text of texts.slice(0, -1)) assert.ok(!text.includes("UPDATE pair_bundle SET current"));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("the load's SQL is written beside the bundle's real folder, not beside a link to it", () => {
  const drive = mkdtempSync(join(tmpdir(), "thenwhat-drive-"));
  const here = mkdtempSync(join(tmpdir(), "thenwhat-here-"));
  try {
    const real = join(drive, "bundle");
    cpSync(bundle, real, { recursive: true });
    const link = join(here, "bundle");
    symlinkSync(real, link);
    const scratch = scratchBeside(link);
    assert.equal(dirname(scratch), realpathSync_(drive));
  } finally {
    rmSync(drive, { recursive: true, force: true });
    rmSync(here, { recursive: true, force: true });
  }
});
