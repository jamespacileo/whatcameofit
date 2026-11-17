// Builds a store in a SQLite file from made-up records, through store/merge.sql, for
// trying an import: registry trials, link leads and their shares, a third each.
//
//   node scripts/sample-store.mjs <out.sqlite> [rows]
import { createHash } from "node:crypto";
import { readFileSync, rmSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";
import { INGEST, MERGE } from "../src/sql.generated.mjs";

const [out, wanted = "50000"] = process.argv.slice(2);
rmSync(out, { force: true });
const db = new DatabaseSync(out);
db.exec(readFileSync(fileURLToPath(new URL("../../schema.sql", import.meta.url)), "utf8"));
const T = "2026-11-01T00:00:00.000000+00:00";
const sha = (text) => createHash("sha256").update(text).digest("hex");
const each = Math.floor(Number(wanted) / 3);
const records = [];
const raw = JSON.stringify({ protocolSection: { identificationModule: { nctId: "NCT0" } } });
records.push(["payload", sha(raw), { sha256: sha(raw), bytes: Buffer.byteLength(raw), body: raw }]);
for (let i = 0; i < each; i += 1) {
  const number = `NCT${String(i).padStart(8, "0")}`;
  records.push(["registry_trial", `clinicaltrials.gov|${number}`, { registry_name: "clinicaltrials.gov", external_id: number, title: `A study of treatment ${i} in condition ${i % 500}`,
    conditions: [`Condition ${i % 500}`], interventions: [{ type: "DRUG", name: `Treatment ${i}` }], intervention_names: `Treatment ${i}`, phases: ["PHASE2"],
    overall_status: "RECRUITING", payload_sha256: sha(raw), fetched_at: T }]);
}
for (let i = 0; i < each; i += 1) {
  const key = `outlet${i % 300}.example/story-${i}`;
  records.push(["link_lead", key, { url_key: key, url_key_version: 2, url: `https://${key}`, outlet: key.split("/")[0], outlet_kind: "general_news",
    title: `Report ${i} on a new treatment`, first_shared_at: T, origin: "file", screen_outcome: "in_scope", triage_score: 0.5, triage_version: 3 }]);
}
for (let i = 0; i < each; i += 1) {
  const key = `outlet${i % 300}.example/story-${i}`;
  records.push(["link_share", `${key}|hackernews|${T}`, { lead_url_key: key, platform: "hackernews", community: "hackernews", shared_at: T, score: i % 90 }]);
}
db.prepare("INSERT INTO store_step VALUES ('link_triage', 3)").run();
const started = Date.now();
for (let at = 0, n = 0; at < records.length; at += 20_000, n += 1) {
  const run = `sample-${n}`, part = records.slice(at, at + 20_000), counts = {};
  for (const [kind] of part) counts[kind] = (counts[kind] || 0) + 1;
  db.prepare(INGEST.register_run).run(run, "migration", null, null, "abc1234", T, "0".repeat(64), null);
  db.prepare(INGEST.state_counts).run(run, JSON.stringify(counts));
  db.prepare(INGEST.state_steps).run(run, JSON.stringify({ link_triage: 3 }));
  db.prepare(INGEST.stage).run(run, JSON.stringify(part.map(([kind, key, body]) => ({ kind, key, body }))));
  db.exec("BEGIN");
  for (const sql of MERGE) { const s = db.prepare(sql); if (sql.includes("?1")) s.run(run); else s.run(); }
  db.exec("COMMIT");
  const status = db.prepare("SELECT status FROM run WHERE id = ?").get(run).status;
  if (status !== "merged") throw new Error(`run ${run} is ${status}`);
}
db.exec("DELETE FROM stg");
console.log(JSON.stringify({ records: records.length, seconds: (Date.now() - started) / 1000 }));
