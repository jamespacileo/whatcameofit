// What the service refuses at its door, on D1's local engine: a request with no token or
// a revoked one, each kind of token outside its scope, a payload or a chunk that is not
// what its checksum says, a body over a bound or of the wrong type, a field that could
// carry an article's text; and what it takes twice without adding anything.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import http from "node:http";
import { readFileSync } from "node:fs";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { ENTRIES, PAYLOADS, Service, TOKENS, engineUnavailable, runChecksum, sha } from "./harness.mjs";

const reason = await engineUnavailable();
if (reason && process.env.CI) throw new Error(reason);
const skip = reason ?? false;
const here = (path) => fileURLToPath(new URL(path, import.meta.url));

const T = "2026-11-01T00:00:00Z";
const claim = (slug, more = {}) => ["claim", slug, { slug, headline: `Report on ${slug}`, summary: "s", vertical: "metabolic", indication: "obesity",
  origin: "backfill", created_at: T, awaiting_audit_at: T, review_state: "approved", reviewed_by: "rule", reviewed_at: T, ...more }];
const article = (slug, key) => ["source_article", `${slug}|${key}`, { slug, url_key: key, url: `https://${key}`, outlet: key.split("/")[0], title: "t", published_date: "2026-10-01" }];
const action = (kind, slug, by = "human") => ["action", `${kind}|${slug}`, { action: kind, slug, decided_by: by, at: "2026-11-16T12:00:00Z" }];
const large = (n) => `payload ${n} ${"x".repeat(17_000)}`;

let s;
let n = 0;
const id = (name) => `${name}-${(n += 1)}`;
// Hand over and merge in one step; the last answer is returned.
async function push(records, options = {}) {
  const run = id("run");
  const refused = await s.hand(run, records, options);
  return refused || { run, ...(await s.merge(run, options.as || "device-mini")) };
}
const register = (as, body) => s.ask("POST", "/runs", { as, body: { id: id("reg"), commit: "abc1234", steps: {}, counts: {}, checksum: runChecksum([]), ...body } });
const stageOne = async (as, writer, record, extra = {}) => s.hand(id("scope"), [record], { as, writer, ...extra });

before(async () => {
  if (skip) return;
  s = await Service.open();
  await s.db.prepare("INSERT INTO store_step VALUES ('link_triage', 3)").run();
  const first = await push([claim("base-claim"), article("base-claim", "bbc.com/a")]);
  assert.equal(first.body.status, "merged");
});
after(async () => { if (s) await s.close(); });

test("the first migration is store/schema.sql unchanged, and the bundled statements are the store's", { skip }, () => {
  assert.equal(readFileSync(here("../migrations/0001_store_schema.sql"), "utf8"), readFileSync(here("../../schema.sql"), "utf8"));
  execFileSync(process.execPath, [here("../scripts/generate.mjs"), "--check"], { stdio: "pipe" });
});

test("every bundled statement is inside D1's limits for a statement, and the merge is the store's 89", { skip }, async () => {
  const { MERGE, PREVIEW, INGEST } = await import("../src/sql.generated.mjs");
  const { D1 } = await import("../src/limits.mjs");
  assert.equal(MERGE.length, 89);
  for (const sql of [...MERGE, ...PREVIEW, ...Object.values(INGEST)]) {
    assert.ok(Buffer.byteLength(sql) < D1.statementBytes);
    assert.ok(new Set(sql.match(/\?\d+/g) || []).size <= D1.boundParameters);
  }
});

test("nothing answers without a token, and a refusal says nothing of why", { skip }, async () => {
  for (const [method, path] of [["GET", "/"], ["POST", "/runs"], ["GET", "/runs/r1"], ["PUT", `/payloads/${sha("x")}`], ["POST", "/work/lease"]]) {
    for (const token of [null, "not-a-token-not-a-token-not-a-token", TOKENS.operator.slice(0, -1)]) {
      const answer = await s.ask(method, path, { token });
      assert.equal(answer.status, 401, `${method} ${path}`);
      assert.deepEqual(answer.body, { error: "unauthorized" });
    }
  }
});

test("a revoked token is refused and every other token still works", { skip }, async () => {
  const other = await Service.open({ entries: ENTRIES.filter((entry) => entry.name !== "device-macbook") });
  try {
    assert.equal((await other.ask("GET", "/runs/none", { as: "device-macbook" })).status, 401);
    assert.equal((await other.ask("GET", "/runs/none", { as: "device-mini" })).status, 404);
    assert.equal((await other.ask("GET", "/runs/none", { as: "operator" })).status, 404);
  } finally { await other.close(); }
});

test("a token registers only its own kind of writer, for its own device", { skip }, async () => {
  const may = { "device-mini": ["device"], daily: ["daily"], lookup: ["lookup"], consumer: ["consumer"], export: ["export"], operator: ["operator", "migration"] };
  for (const [as, writers] of Object.entries(may)) {
    for (const writer of ["device", "daily", "lookup", "consumer", "operator", "export", "migration"]) {
      const answer = await register(as, { writer, ...(writer === "lookup" ? { request_class: "site" } : {}) });
      assert.equal(answer.status, writers.includes(writer) ? 201 : 403, `${as} registering ${writer}`);
    }
  }
  assert.equal((await register("device-mini", { writer: "device", device: "macbook" })).status, 403);
  // One device cannot see, stage into, merge or drop another device's run.
  const run = id("mine");
  assert.equal(await s.hand(run, [article("base-claim", "mine.com/1")], { as: "device-mini" }), null);
  for (const [method, path] of [["GET", `/runs/${run}`], ["POST", `/runs/${run}/merge`], ["POST", `/runs/${run}/preview`], ["DELETE", `/runs/${run}`]]) {
    assert.equal((await s.ask(method, path, { as: "device-macbook" })).status, 404, `${method} ${path}`);
    assert.equal((await s.ask(method, path, { as: "daily" })).status, 404, `${method} ${path}`);
  }
  assert.equal((await s.drop(run)).status, 200);
});

test("a backfill cannot clear an audit, archive, publish, merge or rename", { skip }, async () => {
  for (const kind of ["audit_clear", "archive", "unarchive", "publish", "merge", "rename", "conflict_accept", "conflict_dismiss"]) {
    for (const as of ["device-mini", "daily", "consumer"]) {
      const answer = await stageOne(as, as.split("-")[0], action(kind, "base-claim"));
      assert.equal(answer?.status, 403, `${as} stating ${kind}`);
      assert.equal(answer.body.error, "outside_scope");
    }
  }
  assert.equal(await s.one("SELECT count(*) FROM claim_action"), 0);
  assert.notEqual(await s.one("SELECT awaiting_audit_at FROM claim WHERE slug = 'base-claim'"), null);
  assert.equal(await s.one("SELECT count(*) FROM stg"), 0);
});

test("a lookup cannot archive, make a claim, an event or a match, or record anyone's decision", { skip }, async () => {
  const lookup = (record) => stageOne("lookup", "lookup", record);
  assert.equal((await lookup(action("archive", "base-claim")))?.status, 403);
  assert.equal((await lookup(claim("from-a-reader", { origin: "lookup" })))?.status, 403);
  assert.equal((await lookup(article("base-claim", "reader.com/1")))?.status, 403);
  assert.equal((await lookup(["entity_match", "k", { slug: "base-claim", entity_type: "intervention", entity_name: "x", source_name: "clinicaltrials.gov", external_id: "NCT1", score: 1 }]))?.status, 403);
  assert.equal((await lookup(["evidence_event", "k", { slug: "base-claim", dedupe_key: "k" }]))?.status, 403);
  assert.equal((await lookup(["link_lead_label", "k", { lead_url_key: "bbc.com/a", labelled_by: "human", label: "not_health" }]))?.status, 403);
  assert.equal((await s.ask("POST", "/work/lease", { as: "lookup", body: { step: "prepare" } })).status, 403);
  assert.equal((await s.ask("POST", "/slices/take", { as: "lookup", body: { platform: "reddit", community: "science", month: "2026-03" } })).status, 403);
  assert.equal(await s.one("SELECT archived_at FROM claim WHERE slug = 'base-claim'"), null);
  assert.equal(await s.one("SELECT count(*) FROM claim"), 1);
});

test("the export states a publication by rule and nothing else; a schedule records no person's decision", { skip }, async () => {
  assert.equal((await stageOne("export", "export", action("archive", "base-claim", "rule")))?.status, 403);
  assert.equal((await stageOne("export", "export", action("audit_clear", "base-claim", "rule")))?.status, 403);
  assert.equal((await stageOne("export", "export", action("publish", "base-claim", "human")))?.status, 403);
  assert.equal((await stageOne("export", "export", claim("by-the-export")))?.status, 403);
  assert.equal((await s.ask("PUT", `/payloads/${sha(large(1))}`, { as: "export", body: large(1), type: "application/octet-stream" })).status, 403);
  assert.equal(await s.hand("export-publish", [action("publish", "base-claim", "rule")], { as: "export" }), null);
  assert.equal((await s.drop("export-publish", "export")).status, 200);
  for (const as of ["daily", "consumer"]) {
    for (const by of ["human", "assistant"]) {
      const answer = await stageOne(as, as, claim("decided", { reviewed_by: by }));
      assert.equal(answer?.status, 403, `${as} recording a decision by ${by}`);
    }
  }
  // Only the consumer and the operator take work; only a device and the operator a slice.
  assert.equal((await s.ask("POST", "/work/lease", { as: "device-mini", body: { step: "prepare" } })).status, 403);
  assert.equal((await s.ask("POST", "/work/lease", { as: "daily", body: { step: "prepare" } })).status, 403);
  assert.equal((await s.ask("POST", "/slices/take", { as: "consumer", body: { platform: "reddit", community: "science", month: "2026-03" } })).status, 403);
  assert.equal((await s.ask("POST", "/work/lease", { as: "consumer", body: { step: "prepare" } })).status, 200);
});

test("the operator's actions go through, and no route runs a statement a caller wrote", { skip }, async () => {
  const done = await push([action("audit_clear", "base-claim")], { as: "operator" });
  assert.equal(done.body.status, "merged");
  assert.equal(await s.one("SELECT awaiting_audit_at FROM claim WHERE slug = 'base-claim'"), null);
  for (const path of ["/sql", "/query", "/runs/x/sql", "/d1", "/snapshot"]) {
    assert.equal((await s.ask("POST", path, { as: "operator", body: { sql: "SELECT 1" } })).status, 404, path);
  }
});

test("a payload is stored under its checksum, once, and a body that does not match is refused", { skip }, async () => {
  const text = large(100), checksum = sha(text);
  const put = (key, body, options = {}) => s.ask("PUT", `/payloads/${key}`, { as: "device-mini", body, type: "application/octet-stream", ...options });
  const wrong = await put(sha("something else"), text);
  assert.equal(wrong.status, 422);
  assert.equal(wrong.body.error, "checksum_mismatch");
  const bucket = await s.mf.getR2Bucket("PAYLOADS");
  assert.equal((await bucket.list()).objects.length, 0, "nothing is stored for a body that does not match");
  assert.deepEqual((await put(checksum, text)).body, { key: `payload/${checksum}`, bytes: Buffer.byteLength(text), stored: true });
  assert.equal((await put(checksum, text)).body.stored, false, "the same payload twice is kept once");
  assert.equal(await (await bucket.get(`payload/${checksum}`)).text(), text);
  assert.equal((await put(sha("small"), "small")).status, 422, "a payload of 16 KB or less is not an R2 object");
  assert.equal((await put(checksum, text, { type: "text/html" })).status, 415);
  assert.equal((await put("NOT-A-CHECKSUM", text)).status, 400);
  // A record may not name a payload that was never put, nor carry a body its checksum does not fit.
  const absent = sha(large(101));
  assert.equal((await stageOne("device-mini", "device", ["payload", absent, { sha256: absent, bytes: 17_012, r2_key: `payload/${absent}` }]))?.body.error, "payload_not_handed_over");
  assert.equal((await stageOne("device-mini", "device", ["payload", sha("a"), { sha256: sha("a"), bytes: 1, body: "b" }]))?.body.error, "checksum_mismatch");
  assert.equal((await stageOne("device-mini", "device", ["payload", checksum, { sha256: checksum, bytes: 5, r2_key: `payload/${checksum}` }]))?.body.error, "checksum_mismatch");
  assert.equal((await stageOne("device-mini", "device", ["payload", checksum, { sha256: checksum, bytes: 5, r2_key: "somewhere/else" }]))?.status, 422);
  assert.equal(await s.one("SELECT count(*) FROM payload"), 0);
});

test("a chunk that is not what its checksum says is not staged, and a run short of a chunk is not merged", { skip }, async () => {
  const run = id("sum");
  const one = JSON.stringify([{ kind: "source_article", key: "base-claim|sum.com/1", body: article("base-claim", "sum.com/1")[2] }]);
  const two = JSON.stringify([{ kind: "source_article", key: "base-claim|sum.com/2", body: article("base-claim", "sum.com/2")[2] }]);
  const registered = await s.ask("POST", "/runs", { as: "device-mini", body: { id: run, writer: "device", commit: "abc1234", steps: {}, counts: { source_article: 1 }, checksum: runChecksum([sha(one), sha(two)]) } });
  assert.equal(registered.status, 201);
  const stage = (text, stated) => s.ask("POST", `/runs/${run}/records`, { as: "device-mini", body: text, headers: stated ? { "x-content-sha256": stated } : {} });
  assert.equal((await stage(one, sha(two))).body.error, "checksum_mismatch");
  assert.equal((await stage(one)).body.error, "checksum_mismatch", "a chunk must state its checksum");
  assert.equal(await s.one("SELECT count(*) FROM stg WHERE run_id = ?", run), 0);
  assert.equal((await stage(one, sha(one))).status, 200);
  // Its one stated record is staged, so the counts reconcile; the second chunk never came.
  const merged = await s.merge(run);
  assert.equal(merged.status, 409);
  assert.equal(merged.body.status, "not_merged");
  assert.equal(merged.body.reason, "checksum_mismatch");
  assert.equal(await s.one("SELECT count(*) FROM source_article WHERE url_key = 'sum.com/1'"), 0);
  assert.equal((await s.preview(run)).body.checksum_holds, false);
});

test("a replayed batch adds nothing: the same chunk, the same run, and the same records as a new run", { skip }, async () => {
  const records = [claim("replayed"), article("replayed", "replay.com/1"), article("replayed", "replay.com/2")];
  const run = id("replay");
  assert.equal(await s.hand(run, records), null);
  const text = JSON.stringify(records.map(([kind, key, body]) => ({ kind, key, body })));
  const twice = await s.ask("POST", `/runs/${run}/records`, { as: "device-mini", body: text, headers: { "x-content-sha256": sha(text) } });
  assert.deepEqual([twice.status, twice.body.staged, twice.body.again], [200, 0, true]);
  assert.equal(await s.one("SELECT count(*) FROM stg WHERE run_id = ?", run), 3);
  // Registering it again changes nothing; registering it as something else is refused.
  const body = { id: run, writer: "device", commit: "abc1234", steps: { link_triage: 3 }, counts: { claim: 1, source_article: 2 }, checksum: runChecksum([sha(text)]) };
  assert.deepEqual([(await s.ask("POST", "/runs", { as: "device-mini", body })).status, (await s.ask("POST", "/runs", { as: "device-mini", body: { ...body, checksum: sha("other") } })).status], [200, 409]);
  const first = await s.merge(run);
  assert.deepEqual(first.body.report, { claim: { resolved: 1, added: 1, conflicts: 0, matched: 0 }, source_article: { resolved: 2, added: 2, conflicts: 0, matched: 0 } });
  const tables = async () => {
    const out = {};
    for (const t of ["claim", "source_article", "payload", "claim_action", "work_item", "stg", "ingest_chunk", "merge_report"]) out[t] = await s.one(`SELECT count(*) FROM ${t}`);
    return out;
  };
  const before = await tables();
  const second = await s.merge(run);
  assert.equal(second.status, 200);
  assert.deepEqual([second.body.again, second.body.merged_at, second.body.report], [true, first.body.merged_at, first.body.report]);
  assert.deepEqual(await tables(), before);
  assert.equal((await s.ask("POST", `/runs/${run}/records`, { as: "device-mini", body: text, headers: { "x-content-sha256": sha(text) } })).status, 409, "a merged run takes no more records");
  assert.equal((await s.drop(run)).status, 409, "a merged run is kept");
  const anew = await push(records);
  assert.deepEqual(anew.body.report, { claim: { resolved: 1, added: 0, conflicts: 0, matched: 1 }, source_article: { resolved: 2, added: 0, conflicts: 0, matched: 2 } });
  assert.deepEqual({ ...(await tables()), merge_report: 0 }, { ...before, merge_report: 0 });
});

test("a batch over the limits is refused whole: a run, a chunk, a record, a payload", { skip }, async () => {
  const small = await Service.open({ vars: { MAX_RUN_RECORDS: "5", MAX_CHUNK_RECORDS: "3", MAX_CHUNK_BYTES: "4000", MAX_PAYLOAD_BYTES: "20000" } });
  try {
    await small.db.prepare("INSERT INTO store_step VALUES ('link_triage', 3)").run();
    const many = (count) => [claim("limits"), ...Array.from({ length: count - 1 }, (_, i) => article("limits", `limit.com/${i}`))];
    const tooMany = await small.hand("over-run", many(6), { chunk: 3 });
    assert.deepEqual([tooMany.status, tooMany.body.error], [413, "run_too_large"]);
    const fat = await small.hand("over-chunk", many(4), { chunk: 4 });
    assert.deepEqual([fat.status, fat.body.error], [413, "chunk_too_large"]);
    const heavy = await small.hand("over-bytes", [claim("limits", { summary: "s".repeat(1900) }), article("limits", `limit.com/${"p".repeat(1900)}`), article("limits", "limit.com/z")], { chunk: 3 });
    assert.deepEqual([heavy.status, heavy.body.error], [413, "too_large"]);
    // A body sent in pieces states no length, and is refused before it is read.
    const { port } = await small.mf.ready;
    const unstated = await new Promise((resolve, reject) => {
      const request = http.request({ port, host: "127.0.0.1", method: "POST", path: "/runs/over-bytes/records",
        headers: { authorization: `Bearer ${TOKENS["device-mini"]}`, "content-type": "application/json" } }, (response) => { response.resume(); resolve(response.statusCode); });
      request.on("error", reject);
      request.write("[");
      request.end("]");
    });
    assert.equal(unstated, 411, "a body must say how long it is");
    const big = "y".repeat(20_001);
    assert.equal((await small.ask("PUT", `/payloads/${sha(big)}`, { as: "device-mini", body: big, type: "application/octet-stream" })).status, 413);
    assert.equal(await small.one("SELECT count(*) FROM stg"), 0);
    assert.equal(await small.one("SELECT count(*) FROM run WHERE id = 'over-run'"), 0);
    // Inside the limits the same records go through, in chunks.
    assert.equal(await small.hand("inside", many(5), { chunk: 3 }), null);
    assert.equal((await small.merge("inside")).body.status, "merged");
  } finally { await small.close(); }
  // A payload over 16 KB cannot travel in its record: a row holds no more.
  const text = large(200);
  const inline = await stageOne("device-mini", "device", ["payload", sha(text), { sha256: sha(text), bytes: Buffer.byteLength(text), body: text }]);
  assert.deepEqual([inline.status, inline.body.error], [413, "payload_too_large_for_a_row"]);
});

test("a body must be JSON and say so, and a record must be a record", { skip }, async () => {
  const run = id("shape");
  assert.equal(await s.hand(run, []), null);
  const send = (body, type, checksum = sha(body)) => s.ask("POST", `/runs/${run}/records`, { as: "device-mini", body, type, headers: { "x-content-sha256": checksum } });
  assert.equal((await send("[]", "text/plain")).status, 415);
  assert.equal((await send("<html>", "application/json")).body.error, "not_json");
  assert.equal((await send("{}", "application/json")).body.error, "not_a_list");
  for (const record of [{ kind: "claim", key: "k" }, { kind: "claim", key: "k", body: [] }, { kind: "claim", key: "k", body: {}, extra: 1 }, "claim"]) {
    assert.equal((await send(JSON.stringify([record]), "application/json")).body.error, "not_a_record");
  }
  assert.equal((await send(JSON.stringify([{ kind: "article_text", key: "k", body: {} }]), "application/json")).body.error, "unknown_kind");
  assert.equal((await s.ask("POST", "/runs", { as: "device-mini", body: "{}", type: "text/plain" })).status, 415);
  for (const bad of [{ id: "has space" }, { commit: "not-a-commit" }, { checksum: "short" }, { counts: { claim: -1 } }, { steps: { link_triage: "3" } }, { request_class: "site" }]) {
    assert.equal((await register("device-mini", { writer: "device", ...bad })).status, 400, JSON.stringify(bad));
  }
  assert.equal((await register("lookup", { writer: "lookup" })).status, 400, "a lookup states its request class");
  assert.equal((await register("device-mini", { writer: "device", counts: { action: 1 } })).status, 403);
  assert.equal(await s.one("SELECT count(*) FROM stg WHERE run_id = ?", run), 0);
});

test("a field that could carry an article's text is refused, and the refusal does not repeat it", { skip }, async () => {
  const text = `An article's own words. ${"Lorem ipsum dolor sit amet. ".repeat(120)}`;
  const cases = [
    ["a field no statement reads", ["source_article", "base-claim|text.com/1", { ...article("base-claim", "text.com/1")[2], article_text: text }], "unknown_field", "article_text"],
    ["a field named for content", ["link_lead", "text.com/2", { url_key: "text.com/2", content: "short" }], "unknown_field", "content"],
    ["a title as long as an article", ["source_article", "base-claim|text.com/3", { ...article("base-claim", "text.com/3")[2], title: text }], "field_too_long", "title"],
    ["a summary as long as an article", claim("long-summary", { summary: text }), "field_too_long", "summary"],
    ["a statement over the schema's 200 characters", ["reported_statement", "k", { slug: "base-claim", url_key: "bbc.com/a", text: "w".repeat(201), text_key: "w" }], "field_too_long", "text"],
    ["a structured field of another kind used for text", ["source_article", "base-claim|text.com/4", { ...article("base-claim", "text.com/4")[2], body: text }], "field_too_long", "body"],
    ["text inside a list", ["entity", "base-claim|intervention|x", { slug: "base-claim", type: "intervention", name: "x", synonyms: [text] }], "field_too_long", "synonyms"],
    ["text inside a model's reasons", ["lead_reading", "bbc.com/a", { lead_url_key: "bbc.com/a", reasons: [{ why: text }] }], "field_too_long", "reasons"],
  ];
  for (const [name, record, error, field] of cases) {
    const answer = await stageOne("device-mini", "device", record);
    assert.deepEqual([answer?.status, answer?.body.error, answer?.body.detail.field], [422, error, field], name);
    assert.ok(!answer.text.includes("Lorem ipsum") && !answer.text.includes("own words"), `${name}: the refusal repeats what was sent`);
  }
  assert.equal(await s.one("SELECT count(*) FROM stg"), 0);
  // What the schema does allow still goes through: a statement of 200 characters.
  const fits = ["reported_statement", "base-claim|bbc.com/a|w", { slug: "base-claim", url_key: "bbc.com/a", text: "w".repeat(200), text_key: "w", kind: "finding",
    firmness: "firm", speaker: "author", basis: "trial", confidence: 0.9, decision_ref: "d1", article_read_at: T, created_at: T }];
  assert.equal((await push([fits])).body.status, "merged");
});

test("a merge wakes the consumer once for each step with work due, saying nothing else", { skip }, async () => {
  const day = new Date().toISOString().slice(0, 10);
  const done = await push([["link_lead", "wake.com/1", { url_key: "wake.com/1", url_key_version: 2, url: "https://wake.com/1", outlet: "wake.com", outlet_kind: "general_news",
    title: "t", first_shared_at: day, origin: "reader", screen_outcome: "in_scope" }],
    ["link_share", `wake.com/1|reader|${day}`, { lead_url_key: "wake.com/1", platform: "reader", community: "reader", shared_at: day, score: 0 }]], { as: "lookup" });
  assert.equal(done.body.status, "merged");
  assert.equal(done.body.merged_at.length, 10, "a lookup's run says only the day");
  assert.equal(await s.one("SELECT state FROM work_item WHERE record_key = 'wake.com/1'"), "due");
});
