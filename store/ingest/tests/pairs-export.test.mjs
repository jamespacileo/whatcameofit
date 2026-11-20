// A bundle version written back out of the pair tables (openspec pairs-site, task 2.1c), on
// D1's local engine. The bundle is real: site/tests/bundle holds the pair pages and schemas
// the lab's own pipeline test writes from its recorded slice.
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { Service, engineUnavailable } from "./harness.mjs";
import { exportBundle } from "../scripts/export-pairs.mjs";
import { SCHEMA_MODEL, bundleVersion, statements } from "../scripts/load-pairs.mjs";

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

test("a version loaded without its manifest is not written back", { skip }, async () => {
  await s.db.prepare("DELETE FROM pair_page WHERE version = ? AND model = '$manifest'").bind(load.version).run();
  const out = scratch();
  await assert.rejects(exportBundle(read, out), /was loaded without a manifest\.json/);
  assert.equal(existsSync(out), false);
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
