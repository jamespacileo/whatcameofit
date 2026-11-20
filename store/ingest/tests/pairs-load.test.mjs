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
import { statements } from "../scripts/load-pairs.mjs";
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
