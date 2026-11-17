// Task 4.9, end to end on this machine: a reader's lead and share, merged by the real
// service into D1, are folded into a bulk file by the pipeline's own commands
// (`thenwhat store fold-inbox`, `clear-inbox`), and leave D1 only once their delta is in
// the bucket and the consumer has processed the leads. Skipped, with the reason, where
// the pipeline's command line cannot be run.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { Service, TOKENS, engineUnavailable } from "./harness.mjs";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const reason = await engineUnavailable();
if (reason && process.env.CI) throw new Error(reason);
const uv = (env, ...args) => spawnSync("uv", ["run", "--directory", here("../../../pipeline"), "thenwhat", "store", ...args], { env: { ...process.env, ...env }, encoding: "utf8", timeout: 120_000 });
const pipeline = reason ? null : uv({}, "fold-inbox", "--help");
const skip = reason || (pipeline.status !== 0 ? "the pipeline's command line cannot be run here (`uv run thenwhat store fold-inbox --help` failed)" : false);

test("a lookup's lead and share reach the bulk file and leave D1", { skip }, async () => {
  const dir = mkdtempSync(join(tmpdir(), "thenwhat-fold-"));
  const s = await Service.open();
  try {
    await s.db.prepare("INSERT INTO store_step VALUES ('link_triage', 3)").run();
    const day = new Date().toISOString().slice(0, 10);
    const keys = ["fold.example/one", "fold.example/two"];
    for (const [n, key] of keys.entries()) {
      const records = [["link_lead", key, { url_key: key, url_key_version: 2, url: `https://${key}`, outlet: "fold.example", outlet_kind: "general_news", title: "A report",
        first_shared_at: day, origin: "reader", screen_outcome: "in_scope" }],
      ["link_share", `${key}|reader|${day}`, { lead_url_key: key, platform: "reader", community: "reader", shared_at: day, score: 0 }]];
      assert.equal(await s.hand(`look-${n}`, records, { as: "lookup", writer: "lookup" }), null);
      assert.equal((await s.merge(`look-${n}`, "lookup")).body.status, "merged");
    }
    // The bulk file the daily job keeps: here an empty one with the store's schema.
    const bulk = join(dir, "bulk.sqlite");
    const made = new DatabaseSync(bulk);
    made.exec(readFileSync(here("../../schema.sql"), "utf8"));
    made.exec("INSERT INTO store_step VALUES ('link_triage', 3)");
    made.close();
    const env = { INGEST_URL: String(await s.mf.ready).replace(/\/$/, ""), INGEST_TOKEN: TOKENS.daily };
    const d1 = () => s.all("SELECT (SELECT count(*) FROM inbox), (SELECT count(*) FROM link_lead), (SELECT count(*) FROM link_share)");

    const folded = uv(env, "fold-inbox", bulk, "--delta", join(dir, "delta.jsonl.gz"));
    assert.equal(folded.status, 0, folded.stderr);
    assert.match(folded.stdout, /Folded 4 records of 2 runs/);
    const held = new DatabaseSync(bulk, { readOnly: true });
    assert.deepEqual({ ...held.prepare("SELECT (SELECT count(*) FROM link_lead) AS leads, (SELECT count(*) FROM link_share) AS shares").get() }, { leads: 2, shares: 2 });
    held.close();
    assert.deepEqual(await d1(), [[4, 2, 2]], "folding clears nothing");

    // Not before the delta is in the bucket.
    const object = `bulk/b1/delta-${day}-1.jsonl.gz`;
    const early = uv(env, "clear-inbox", "--through", "4", "--object", object);
    assert.notEqual(early.status, 0);
    assert.match(early.stdout + early.stderr, /delta_not_uploaded/);
    assert.deepEqual(await d1(), [[4, 2, 2]]);
    // What scripts/upload-delta.mjs leaves in the bucket: the delta, and the build's list
    // saying how far it folded.
    const bucket = await s.mf.getR2Bucket("PAYLOADS"), delta = readFileSync(join(dir, "delta.jsonl.gz"));
    await bucket.put(object, delta);
    await bucket.put("bulk/b1/deltas.json", JSON.stringify({ build: "b1", deltas: [{ name: object.split("/")[2], date: day, bytes: delta.length, sha256: "", through: 4 }] }));
    const cleared = uv(env, "clear-inbox", "--through", "4", "--object", object);
    assert.equal(cleared.status, 0, cleared.stderr);
    // The records are out of the inbox; the leads wait for the consumer.
    assert.deepEqual(await d1(), [[0, 2, 2]]);
    for (const key of keys) await s.ask("POST", "/work/finish", { as: "consumer", body: { kind: "link_lead", key, step: "lead_process" } });
    assert.equal(uv(env, "clear-inbox", "--through", "4").status, 0);
    assert.deepEqual(await d1(), [[0, 0, 0]], "the lead and the share have left D1");
    // Nothing is folded twice.
    assert.match(uv(env, "fold-inbox", bulk, "--delta", join(dir, "delta-2.jsonl.gz")).stdout, /Folded 0 records/);
  } finally { await s.close(); rmSync(dir, { recursive: true, force: true }); }
});
