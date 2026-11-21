// A bundle version written back out of the pair tables (openspec pairs-site, task 2.1c), on
// D1's local engine. The bundle is real: site/tests/bundle holds the pair pages and schemas
// the lab's own pipeline test writes from its recorded slice.
import assert from "node:assert/strict";
import { copyFileSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { Service, engineUnavailable } from "./harness.mjs";
import { exportBundle } from "../scripts/export-pairs.mjs";
import { PART_CHARS, SCHEMA_MODEL, bodyParts, bundleVersion, manifestBackfill, statements } from "../scripts/load-pairs.mjs";
import { writeManifest } from "../scripts/bundle-manifest.mjs";

const skip = (await engineUnavailable()) ?? false;
if (skip && process.env.CI) throw new Error(skip);

const bundle = fileURLToPath(new URL("../../../site/tests/bundle", import.meta.url));
let s;
let load;
const read = async (sql) => (await s.db.prepare(sql).all()).results;
const scratch = () => join(mkdtempSync(join(tmpdir(), "thenwhat-export-")), "bundle");

before(async () => {
  if (skip) return;
  s = await Service.open();
  load = statements(bundle, { loadedAt: "2026-11-20T00:00:00.000Z" });
  for (const sql of load.sql) await s.db.prepare(sql).run();
});
after(async () => { if (s) await s.close(); });

/** Every file of a bundle folder, by its path inside it. */
function filesOf(folder) {
  const out = {};
  for (const sub of readdirSync(folder).sort()) {
    if (sub.endsWith(".json")) { out[sub] = JSON.parse(readFileSync(join(folder, sub), "utf8")); continue; }
    for (const name of readdirSync(join(folder, sub)).sort()) out[`${sub}/${name}`] = JSON.parse(readFileSync(join(folder, sub, name), "utf8"));
  }
  return out;
}

test("the schemas are kept in D1 with the pages, and count in the version", { skip }, async () => {
  const schemas = readdirSync(join(bundle, "schemas"));
  const held = await read(`SELECT DISTINCT key FROM pair_page WHERE version = '${load.version}' AND model = '${SCHEMA_MODEL}' ORDER BY key`);
  assert.deepEqual(held.map((row) => row.key), schemas.map((name) => name.slice(0, -5)).sort());
  assert.equal(bundleVersion(bundle), load.version);
});

test("the current version is written back as the folder it was loaded from", { skip }, async () => {
  const out = scratch();
  const done = await exportBundle(read, out);
  assert.equal(done.version, load.version);
  assert.deepEqual(filesOf(out), filesOf(bundle));
  assert.equal(bundleVersion(out), load.version);
  await assert.rejects(exportBundle(read, out), /exists/);
});

test("a version loaded without its manifest is not written back until the manifest is kept with it", { skip }, async () => {
  await s.db.prepare("DELETE FROM pair_page WHERE version = ? AND model = '$manifest'").bind(load.version).run();
  const out = scratch();
  await assert.rejects(exportBundle(read, out), /was loaded without a manifest\.json/);
  assert.equal(existsSync(out), false);
  // The same folder, now with its manifest, keeps the version: the manifest is stored beside it, once.
  const backfill = manifestBackfill(statements(bundle));
  assert.equal(backfill.version, load.version);
  for (const sql of [...backfill.sql, ...backfill.sql]) await s.db.prepare(sql).run();
  assert.equal((await read(`SELECT count(*) AS n FROM pair_page WHERE version = '${load.version}' AND model = '$manifest'`))[0].n, 1);
  const again = scratch();
  assert.equal((await exportBundle(read, again)).version, load.version);
  assert.deepEqual(filesOf(again), filesOf(bundle));
});

test("a version with a part missing is refused, and nothing is left behind", { skip }, async () => {
  const [long] = await read(`SELECT model, key FROM pair_page WHERE version = '${load.version}' AND part = 1 LIMIT 1`);
  assert.ok(long, "the bundle has a file kept in more than one part");
  await s.db.prepare("DELETE FROM pair_page WHERE version = ? AND model = ? AND key = ? AND part = 1").bind(load.version, long.model, long.key).run();
  const out = scratch();
  await assert.rejects(exportBundle(read, out), /not whole|version/);
  assert.equal(existsSync(out), false);
  await assert.rejects(exportBundle(read, scratch(), "0000000000000000"), /holds no bundle 0000000000000000/);
});

// A copy of the small bundle that also carries a trial listing whose stored body has a character
// outside the Basic Multilingual Plane (two UTF-16 units) across the boundary of its first part.
function bundleWithListing() {
  const folder = scratch();
  cpSync(bundle, folder, { recursive: true });
  const site = fileURLToPath(new URL("../../../site/", import.meta.url));
  const listing = JSON.parse(readFileSync(join(site, "tests/fixture-trials-listing.json"), "utf8"));
  listing.trials[0][1] = "@@";
  const at = JSON.stringify(listing).indexOf("@@");
  listing.trials[0][1] = `${"a".repeat(PART_CHARS - 1 - at)}\u{1F600} trial`;
  assert.equal(JSON.stringify(listing).codePointAt(PART_CHARS - 1), 0x1f600);
  mkdirSync(join(folder, "p12_pair_trial_listing"));
  writeFileSync(join(folder, "p12_pair_trial_listing/listed.json"), `${JSON.stringify(listing)}\n`);
  copyFileSync(join(site, "trials-listing.schema.json"), join(folder, "schemas/PairTrialListing.json"));
  rmSync(join(folder, "manifest.json"));
  writeManifest(folder, { snapshot: { trial_listing: { complete: false, registry_total: 9, trials_read: 1, trials_listed: listing.trials.length } } });
  return folder;
}

test("a body is never cut inside a character, and its parts join back to it", () => {
  const body = `${"a".repeat(PART_CHARS - 1)}\u{1F600}${"b".repeat(PART_CHARS)}`;
  const parts = bodyParts(body);
  assert.equal(parts.join(""), body);
  assert.equal(parts[0].length, PART_CHARS - 1);
  for (const part of parts) {
    assert.ok(part.length <= PART_CHARS);
    assert.ok(part.isWellFormed(), "no part holds half a character");
  }
  assert.deepEqual(bodyParts(""), [""]);
});

test("a listing with a two-unit character across a part boundary is written back as it was loaded", { skip }, async () => {
  const folder = bundleWithListing();
  const listed = statements(folder);
  for (const sql of listed.sql) await s.db.prepare(sql).run();
  const out = scratch();
  assert.equal((await exportBundle(read, out)).version, listed.version);
  assert.deepEqual(filesOf(out), filesOf(folder));
  assert.equal(bundleVersion(out), listed.version);
});

test("the same pages with a corrected manifest keep their version, and the corrected manifest is the one held", { skip }, async () => {
  const folder = bundleWithListing();
  const first = statements(folder);
  // As the loader does: a version already current is not loaded again.
  const [current] = await read("SELECT version FROM pair_bundle WHERE current = 1");
  if (current?.version !== first.version) for (const sql of first.sql) await s.db.prepare(sql).run();
  const count = JSON.parse(readFileSync(join(folder, "p12_pair_trial_listing/listed.json"), "utf8")).trials.length;
  rmSync(join(folder, "manifest.json"));
  const corrected = writeManifest(folder, { snapshot: { trial_listing: { complete: true, registry_total: count, trials_read: count, trials_listed: count } } });
  const again = statements(folder);
  assert.equal(again.version, first.version);
  for (const sql of manifestBackfill(again).sql) await s.db.prepare(sql).run();
  assert.equal((await read(`SELECT count(*) AS n FROM pair_page WHERE version = '${again.version}' AND model = '$manifest'`))[0].n, 1);
  const out = scratch();
  await exportBundle(read, out);
  assert.deepEqual(JSON.parse(readFileSync(join(out, "manifest.json"), "utf8")).snapshot, corrected.snapshot);
});
