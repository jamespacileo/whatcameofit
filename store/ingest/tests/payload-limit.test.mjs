// Migration 0007 makes the `payload` table again, to change the bound on a body kept in
// its row, on a table other tables reference. That it applies to an empty database every
// other test shows. This one applies it to a loaded one, on D1's local engine and through
// Wrangler as a migration is applied: every payload is there afterwards as it was, every
// row that referenced one still does, and the new bound holds in bytes.
//
// It is the test the migration was written against: two other ways of making the table
// again were refused by the engine once rows referenced it.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { engineUnavailable } from "./harness.mjs";

const skip = (await engineUnavailable()) ?? false;
if (skip && process.env.CI) throw new Error(skip);

const root = fileURLToPath(new URL("..", import.meta.url));
const sha = (text) => createHash("sha256").update(text).digest("hex");
const BOUND = 524_288;

test("migration 0007 keeps every payload and every reference to one, on a loaded database", { skip }, async () => {
  const { INLINE_PAYLOAD_BYTES } = await import("../src/limits.mjs");
  assert.equal(INLINE_PAYLOAD_BYTES, BOUND, "the service's bound is the schema's");

  const dir = mkdtempSync(join(tmpdir(), "thenwhat-payload-limit-"));
  const wrangler = (...args) => execFileSync(join(root, "node_modules/.bin/wrangler"), ["d1", "execute", "STORE", "--local", "--persist-to", dir, ...args],
    { cwd: root, env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, stdio: "pipe", timeout: 180_000 }).toString();
  const file = (path) => wrangler("--file", path);
  const rows = (sql) => JSON.parse(wrangler("--json", "--command", sql))[0].results;
  const refused = (sql) => { try { wrangler("--command", sql); return null; } catch (error) { return `${error.stdout}${error.stderr}`; } };
  try {
    const migrations = readdirSync(join(root, "migrations")).filter((name) => name.endsWith(".sql")).sort();
    const at = migrations.findIndex((name) => name.startsWith("0007_"));
    assert.ok(at > 0, "migration 0007 is there");
    for (const name of migrations.slice(0, at)) file(join(root, "migrations", name));

    // Payloads across every range of checksums the migration copies by, with bodies of
    // two-byte characters, one kept in R2, and rows of another table that reference half.
    const load = ["INSERT INTO run (id, writer, device, commit_sha, registered_at) VALUES ('r1', 'device', 'mini', 'abc1234', '2026-11-17T00:00:00.000000+00:00');"];
    const held = [];
    for (let i = 0; i < 64; i += 1) {
      const body = JSON.stringify({ n: i, text: "é".repeat(100 + i) });
      held.push(sha(body));
      load.push(`INSERT INTO payload (sha256, bytes, body, r2_key, added_run) VALUES ('${sha(body)}', ${Buffer.byteLength(body)}, '${body}', NULL, 'r1');`);
    }
    load.push(`INSERT INTO payload (sha256, bytes, body, r2_key, added_run) VALUES ('${sha("in r2")}', 900000, NULL, 'payload/${sha("in r2")}', 'r1');`);
    held.slice(0, 32).forEach((checksum, i) => load.push("INSERT INTO source_record (kind, source_name, external_id, payload_sha256, fetched_at, added_run, changed_run)"
      + ` VALUES ('substance', 'gsrs', 'S${i}', '${checksum}', '2026-11-17T00:00:00.000000+00:00', 'r1', 'r1');`));
    writeFileSync(join(dir, "load.sql"), `${load.join("\n")}\n`);
    file(join(dir, "load.sql"));
    assert.ok(new Set(held.map((checksum) => checksum[0])).size >= 12, "the payloads fall in most of the sixteen ranges");

    const everything = () => rows("SELECT sha256, bytes, body, r2_key, added_run FROM payload ORDER BY sha256");
    const before = everything();
    assert.equal(before.length, 65);

    file(join(root, "migrations", migrations[at]));

    assert.deepEqual(everything(), before, "every payload is there as it was");
    assert.equal(rows("SELECT count(*) AS n FROM source_record s JOIN payload p ON p.sha256 = s.payload_sha256")[0].n, 32, "every reference still finds its payload");
    assert.deepEqual(rows("PRAGMA foreign_key_check"), []);
    assert.deepEqual(rows("SELECT name FROM sqlite_master WHERE name LIKE 'payload%' OR name LIKE 'ix_payload%' ORDER BY name").map((row) => row.name),
      ["ix_payload_added_run", "payload"], "nothing is left over, and the index is back");

    // Foreign keys are enforced again once the migration is done.
    assert.match(refused(`INSERT INTO source_record (kind, source_name, external_id, payload_sha256, fetched_at, added_run, changed_run)
      VALUES ('substance', 'gsrs', 'orphan', '${sha("no such payload")}', '2026-11-17T00:00:00.000000+00:00', 'r1', 'r1')`), /FOREIGN KEY constraint failed/);

    // The bound, in bytes: a body the old bound refused; one of exactly the bound, in
    // two-byte characters; and one a single character longer, which the old way of
    // counting (characters) would have let through at half the bound.
    // (A long body is made in SQL from `hex(zeroblob())`: D1's engine stops `printf` at 100,000 characters.)
    const insert = (name, characters, of) => `INSERT INTO payload (sha256, bytes, body, added_run) VALUES ('${sha(name)}', ${characters * Buffer.byteLength(of)}, replace(substr(hex(zeroblob(${Math.ceil(characters / 2)})), 1, ${characters}), '0', '${of}'), 'r1')`;
    assert.equal(refused(insert("ascii", 400_000, "x")), null, "400,000 bytes are kept in the row");
    assert.equal(refused(insert("at the bound", BOUND / 2, "é")), null, "exactly the bound is kept");
    assert.match(refused(insert("over the bound", BOUND / 2 + 1, "é")), /CHECK constraint failed/, "one character over the bound, in bytes, is refused");
    assert.deepEqual(rows("SELECT length(CAST(body AS BLOB)) AS bytes FROM payload WHERE bytes >= 400000 AND body IS NOT NULL ORDER BY 1").map((row) => row.bytes),
      [400_000, BOUND], "and they are as long as they were meant to be");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
