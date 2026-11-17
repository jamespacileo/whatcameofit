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

const T = "2026-11-01T00:00:00.000000+00:00";
const claim = (slug, more = {}) => ["claim", slug, { slug, headline: `Report on ${slug}`, summary: "s", vertical: "metabolic", indication: "obesity",
  origin: "backfill", created_at: T, awaiting_audit_at: T, review_state: "approved", reviewed_by: "rule", reviewed_at: T, ...more }];
const article = (slug, key) => ["source_article", `${slug}|${key}`, { slug, url_key: key, url: `https://${key}`, outlet: key.split("/")[0], title: "t", published_date: "2026-10-01" }];
const action = (kind, slug, by = "human") => ["action", `${kind}|${slug}`, { action: kind, slug, decided_by: by, at: "2026-11-16T12:00:00.000000+00:00" }];
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

test("every bundled statement is inside D1's limits for a statement, and the merge is the store's 98", { skip }, async () => {
  const { MERGE, PREVIEW, INGEST } = await import("../src/sql.generated.mjs");
  const { D1 } = await import("../src/limits.mjs");
  assert.equal(MERGE.length, 98);
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
    ["a structured field of another kind used for text", ["source_article", "base-claim|text.com/4", { ...article("base-claim", "text.com/4")[2], body: text }], "unknown_field", "body"],
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

// One chunk sent as the bytes given, not written out from a value: what a writer that
// builds its own JSON could send.
async function raw(as, writer, text, counts) {
  const run = id("raw");
  const registered = await s.ask("POST", "/runs", { as, body: { id: run, writer, commit: "abc1234", steps: {}, counts, checksum: runChecksum([sha(text)]) } });
  assert.equal(registered.status, 201);
  const staged = await s.ask("POST", `/runs/${run}/records`, { as, body: text, headers: { "x-content-sha256": sha(text) } });
  return { run, staged };
}
const stagedAs = (run, ...fields) => s.all(`SELECT ${fields.map((field) => `body ->> '${field}'`).join(", ")} FROM stg WHERE run_id = ?1`, run);

test("a key given twice is stored as the door read it, never as SQLite would", { skip }, async () => {
  assert.equal((await push([claim("twice-held")])).body.status, "merged");
  // An export's publication dressed over a person's audit clear.
  const clear = `[{"kind":"action","key":"a1","body":{"action":"audit_clear","action":"publish","slug":"twice-held","decided_by":"human","decided_by":"rule","at":"${T}"}}]`;
  const sent = await raw("export", "export", clear, { action: 1 });
  assert.equal(sent.staged.status, 200);
  assert.deepEqual(await stagedAs(sent.run, "action", "decided_by"), [["publish", "rule"]]);
  await s.merge(sent.run, "export");
  assert.notEqual(await s.one("SELECT awaiting_audit_at FROM claim WHERE slug = 'twice-held'"), null, "the claim is still held");
  assert.equal(await s.one("SELECT count(*) FROM claim_action a JOIN claim c ON c.id = a.claim_id WHERE c.slug = 'twice-held' AND a.action = 'audit_clear'"), 0);
  assert.equal(await s.one("SELECT count(*) FROM claim_public WHERE slug = 'twice-held'"), 0, "a held claim is not public");
  // The daily job's rule dressed over a person's rejection.
  const body = claim("twice-held", { review_state: "rejected", reviewed_at: "2026-11-05T00:00:00.000000+00:00" })[2];
  const person = JSON.stringify([{ kind: "claim", key: "twice-held", body }]).replace('"reviewed_by":"rule"', '"reviewed_by":"human","reviewed_by":"rule"');
  assert.ok(person.includes('"reviewed_by":"human"'));
  const daily = await raw("daily", "daily", person, { claim: 1 });
  assert.deepEqual(await stagedAs(daily.run, "reviewed_by"), [["rule"]]);
  assert.equal((await s.merge(daily.run, "daily")).body.status, "merged");
  assert.equal(await s.one("SELECT count(*) FROM claim WHERE reviewed_by = 'human'"), 0);
  // A long title hidden before a short one; and the other way round, which the door reads as long.
  const long = "Lorem ipsum dolor sit amet. ".repeat(120);
  const titled = (first, second) => JSON.stringify([{ kind: "source_article", key: "twice-held|dup.com/1", body: article("twice-held", "dup.com/1")[2] }])
    .replace('"title":"t"', `"title":${JSON.stringify(first)},"title":${JSON.stringify(second)}`);
  const hidden = await raw("device-mini", "device", titled(long, "t"), { source_article: 1 });
  assert.deepEqual(await stagedAs(hidden.run, "title"), [["t"]]);
  assert.equal(await s.one("SELECT count(*) FROM stg WHERE body LIKE '%Lorem ipsum%'"), 0, "no long text reached the store");
  const shown = await raw("device-mini", "device", titled("t", long), { source_article: 1 });
  assert.deepEqual([shown.staged.status, shown.staged.body.error], [422, "field_too_long"]);
  // A payload whose first body is not what its checksum says.
  const good = "what was fetched";
  const pay = `[{"kind":"payload","key":"${sha(good)}","body":{"sha256":"${sha(good)}","bytes":${good.length},"body":"something else","body":"${good}"}}]`;
  const paid = await raw("device-mini", "device", pay, { payload: 1 });
  assert.deepEqual(await stagedAs(paid.run, "body"), [[good]]);
  // A kind given twice, and half a character, which SQLite and JavaScript read differently.
  const kinds = await raw("device-mini", "device", `[{"kind":"action","kind":"claim","key":"twice-kind","body":${JSON.stringify(claim("twice-kind")[2])}}]`, { claim: 1 });
  assert.deepEqual(await s.all("SELECT kind FROM stg WHERE run_id = ?1", kinds.run), [["claim"]]);
  const half = await raw("device-mini", "device", '[{"kind":"claim","key":"half","body":{"slug":"half","headline":"a \\ud83d b"}}]', { claim: 1 });
  assert.deepEqual([half.staged.status, half.staged.body.error], [400, "bad_text"]);
  const nul = await raw("device-mini", "device", '[{"kind":"claim","key":"nul","body":{"slug":"nul","headline":"a\\u0000b"}}]', { claim: 1 });
  assert.deepEqual([nul.staged.status, nul.staged.body.error], [400, "bad_text"]);
  const bytes = await s.ask("POST", `/runs/${nul.run}/records`, { as: "device-mini", body: new Uint8Array([0x5b, 0x22, 0xff, 0x22, 0x5d]), type: "application/json" });
  assert.deepEqual([bytes.status, bytes.body.error], [400, "not_json"]);
});

test("a device records no person's or assistant's decision, and holds every claim it approves", { skip }, async () => {
  const device = (record) => stageOne("device-mini", "device", record);
  for (const by of ["human", "assistant"]) {
    assert.equal((await device(claim("by-a-script", { reviewed_by: by })))?.status, 403, `a claim reviewed by ${by}`);
    assert.equal((await device(["link_lead_label", "bbc.com/a", { lead_url_key: "bbc.com/a", labelled_by: by, label: "not_health", labelled_at: T }]))?.status, 403);
    assert.equal((await device(["entity_match", "k", { slug: "base-claim", entity_type: "intervention", entity_name: "x", source_name: "clinicaltrials.gov", external_id: "NCT1", score: 1,
      review_state: "approved", reviewed_by: by, reviewed_at: T }]))?.status, 403);
  }
  assert.equal((await device(["decision", "k", { step: "triage", seq: 1, human_label: "in_scope" }]))?.body.detail.field, "human_label");
  // An approved claim with no hold: refused when new, when pending, and when still held.
  const unheld = await device(claim("no-hold", { awaiting_audit_at: undefined }));
  assert.deepEqual([unheld?.status, unheld?.body.error, unheld?.body.detail.field], [403, "outside_scope", "awaiting_audit_at"]);
  assert.equal((await push([claim("still-held")])).body.status, "merged");
  assert.equal((await device(claim("still-held", { awaiting_audit_at: undefined })))?.status, 403);
  assert.equal(await s.one("SELECT count(*) FROM stg WHERE key IN ('no-hold', 'by-a-script')"), 0);
  // By seed, held, it goes through; so does a claim the operator has released, handed over again.
  const seeded = await push([claim("seeded", { reviewed_by: "seed" })]);
  assert.equal(seeded.body.status, "merged");
  assert.equal((await push([["action", "audit_clear|seeded", { action: "audit_clear", slug: "seeded", decided_by: "human", at: T }]], { as: "operator" })).body.status, "merged");
  assert.equal((await push([claim("seeded", { reviewed_by: "seed", awaiting_audit_at: undefined })])).body.status, "merged");
  // The operator's token carries a person's decision.
  assert.equal((await push([claim("by-a-person", { reviewed_by: "human", awaiting_audit_at: undefined })], { as: "operator" })).body.status, "merged");
});

test("a field is taken only on a kind that reads it, a lookup ties no lead to a claim, and a time has one form", { skip }, async () => {
  const lead = { url_key: "form.com/1", url_key_version: 2, url: "https://form.com/1", outlet: "form.com", first_shared_at: "2026-10-01" };
  const tied = await stageOne("lookup", "lookup", ["link_lead", "form.com/1", { ...lead, claim_slug: "base-claim" }]);
  assert.deepEqual([tied?.status, tied?.body.detail.field], [403, "claim_slug"]);
  const other = await stageOne("device-mini", "device", ["link_share", "k", { lead_url_key: "form.com/1", platform: "hackernews", community: "hackernews", shared_at: T, claim_slug: "base-claim" }]);
  assert.deepEqual([other?.status, other?.body.error, other?.body.detail.field], [422, "unknown_field", "claim_slug"]);
  for (const time of ["2026-11-01T00:00:00Z", "2026-11-01T00:00:00+00:00", "2026-11-01T00:00:00.000Z", "2026-11-01 00:00:00.000000+00:00", "2026-11-01T01:00:00.000000+01:00", 1793491200]) {
    const answer = await stageOne("device-mini", "device", claim("timed", { reviewed_at: time }));
    assert.deepEqual([answer?.status, answer?.body.error, answer?.body.detail.field], [422, "bad_time", "reviewed_at"], String(time));
  }
  assert.match(await s.one("SELECT registered_at FROM run WHERE writer = 'device' LIMIT 1"), /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}\+00:00$/);
  // A trial's joined arm names may be long; its title may not.
  const trial = { registry_name: "clinicaltrials.gov", external_id: "NCT77", title: "t", intervention_names: "Drug: arm; ".repeat(400) };
  assert.equal(await stageOne("device-mini", "device", ["registry_trial", "clinicaltrials.gov|NCT77", trial]), null);
  assert.equal((await stageOne("device-mini", "device", ["registry_trial", "clinicaltrials.gov|NCT78", { ...trial, external_id: "NCT78", title: trial.intervention_names }]))?.body.error, "field_too_long");
});

test("registering a run again writes nothing, before its merge or after", { skip }, async () => {
  const body = { id: "once", writer: "device", commit: "abc1234", steps: { link_triage: 3 }, counts: { claim: 1 }, checksum: runChecksum([]) };
  const rows = () => Promise.all([s.all("SELECT step, version FROM run_step WHERE run_id = 'once'"), s.all("SELECT kind, records FROM run_stated WHERE run_id = 'once'")]);
  assert.equal((await s.ask("POST", "/runs", { as: "device-mini", body })).status, 201);
  const first = await rows();
  assert.deepEqual([(await s.ask("POST", "/runs", { as: "device-mini", body })).status, await rows()], [200, first]);
  for (const more of [{ steps: { link_triage: 3, lead_read: 9 } }, { counts: { claim: 1, entity: 4 } }, { steps: {} }]) {
    const answer = await s.ask("POST", "/runs", { as: "device-mini", body: { ...body, ...more } });
    assert.deepEqual([answer.status, answer.body.error, await rows()], [409, "run_exists", first]);
  }
  await s.drop("once");
  const merged = await push([claim("registered-once")]);
  const stated = { id: merged.run, writer: "device", commit: "abc1234", steps: { link_triage: 3 }, counts: { claim: 1 }, checksum: await s.one("SELECT stated_checksum FROM run WHERE id = ?1", merged.run) };
  const after = await s.ask("POST", "/runs", { as: "device-mini", body: { ...stated, steps: { link_triage: 3, lead_read: 9 }, counts: { claim: 1, entity: 4 } } });
  assert.equal(after.status, 409);
  assert.deepEqual((await s.ask("POST", "/runs", { as: "device-mini", body: stated })).body.status, "merged");
  assert.equal(await s.one("SELECT count(*) FROM run_step WHERE run_id = ?1", merged.run), 1);
  assert.equal(await s.one("SELECT count(*) FROM run_stated WHERE run_id = ?1", merged.run), 1);
});

test("bulk records a run hands over wait in the inbox, and leave D1 once the daily job has folded them", { skip }, async () => {
  const box = await Service.open();
  try {
    await box.db.prepare("INSERT INTO store_step VALUES ('link_triage', 3)").run();
    const day = new Date().toISOString().slice(0, 10);
    const raw = JSON.stringify({ nctId: "NCT500" });
    const lead = (key) => ["link_lead", key, { url_key: key, url_key_version: 2, url: `https://${key}`, outlet: key.split("/")[0], outlet_kind: "general_news", title: "A report",
      first_shared_at: day, origin: "reader", screen_outcome: "in_scope" }];
    const share = (key) => ["link_share", `${key}|reader|${day}`, { lead_url_key: key, platform: "reader", community: "reader", shared_at: day, score: 0 }];
    const first = [["payload", sha(raw), { sha256: sha(raw), bytes: raw.length, body: raw }],
      ["registry_trial", "clinicaltrials.gov|NCT500", { registry_name: "clinicaltrials.gov", external_id: "NCT500", title: "A trial", conditions: ["Obesity"], interventions: [],
        intervention_names: "x", phases: [], overall_status: "RECRUITING", payload_sha256: sha(raw), fetched_at: `${day}T00:00:00.000000+00:00` }],
      lead("inbox.example/one"), share("inbox.example/one")];
    assert.equal(await box.hand("look-1", first, { as: "lookup", writer: "lookup" }), null);
    assert.equal((await box.merge("look-1", "lookup")).body.status, "merged");
    assert.equal(await box.hand("look-2", [lead("inbox.example/two"), share("inbox.example/two")], { as: "lookup", writer: "lookup" }), null);
    assert.equal((await box.merge("look-2", "lookup")).body.status, "merged");
    // A hot kind is not kept, nor a run the merge undid.
    assert.equal(await box.hand("hot-1", [claim("inbox-claim")]), null);
    assert.equal((await box.merge("hot-1")).body.status, "merged");
    assert.equal(await box.hand("undone-1", [share("inbox.example/never")], { as: "lookup", writer: "lookup" }), null);
    assert.equal((await box.merge("undone-1", "lookup")).body.status, "undone");
    await box.drop("undone-1", "lookup");

    for (const as of ["device-mini", "lookup", "consumer", "export"]) {
      assert.equal((await box.ask("GET", "/inbox", { as })).status, 403, as);
      assert.equal((await box.ask("POST", "/inbox/clear", { as, body: { through: 99 } })).status, 403, as);
    }
    const all = (await box.ask("GET", "/inbox", { as: "daily" })).body;
    assert.deepEqual(all.records.map((record) => [record.run, record.kind]), [["look-1", "payload"], ["look-1", "registry_trial"], ["look-1", "link_lead"], ["look-1", "link_share"],
      ["look-2", "link_lead"], ["look-2", "link_share"]]);
    assert.deepEqual(all.records[2], { seq: all.records[2].seq, run: "look-1", kind: "link_lead", key: "inbox.example/one", body: first[2][2] }, "a record is as it was staged");
    assert.equal(all.more, false);
    // Read in pages, by the cursor the service gives.
    const page = (await box.ask("GET", "/inbox?limit=5", { as: "daily" })).body;
    assert.deepEqual([page.records.length, page.more, page.through], [5, true, all.records[4].seq]);
    assert.equal((await box.ask("GET", `/inbox?after=${page.through}`, { as: "daily" })).body.records.length, 1);
    assert.equal((await box.ask("GET", "/inbox?after=x", { as: "daily" })).status, 400);

    // Cleared through the first page: look-1 is folded whole and leaves D1; look-2 is cut
    // by the page, so its rows stay until the rest of it is folded.
    const counts = () => box.all("SELECT (SELECT count(*) FROM link_lead), (SELECT count(*) FROM link_share), (SELECT count(*) FROM registry_trial), (SELECT count(*) FROM registry_trial_fts), (SELECT count(*) FROM inbox)");
    assert.deepEqual(await counts(), [[2, 2, 1, 1, 6]]);
    assert.equal((await box.ask("POST", "/inbox/clear", { as: "daily", body: {} })).status, 400);
    // Nothing is cleared before a fold is recorded, and a fold is recorded only with its
    // delta in the bucket, no further than the inbox has given.
    const early = await box.ask("POST", "/inbox/clear", { as: "daily", body: { through: page.through } });
    assert.deepEqual([early.status, early.body.error, early.body.detail.folded_through], [409, "not_folded", 0]);
    const fold = (as, through, object) => box.ask("POST", "/inbox/folded", { as, body: { through, object } });
    assert.equal((await fold("lookup", page.through, "bulk/b1/delta-2026-11-17-1.jsonl.gz")).status, 403);
    assert.equal((await fold("daily", page.through, "payload/abc")).status, 400);
    assert.equal((await fold("daily", page.through, "bulk/b1/delta-2026-11-17-1.jsonl.gz")).body.error, "delta_not_uploaded");
    const r2 = await box.mf.getR2Bucket("PAYLOADS");
    const one = "bulk/b1/delta-2026-11-17-1.jsonl.gz", two = "bulk/b1/delta-2026-11-17-2.jsonl.gz";
    const list = (deltas) => r2.put("bulk/b1/deltas.json", JSON.stringify({ build: "b1", deltas }));
    const delta = (name, text, through) => ({ name, date: "2026-11-17", bytes: text.length, sha256: sha(text), through });
    await r2.put(one, "the day's records");
    await r2.put(two, "the rest");
    // How far a delta folded is the build's list's word, not the caller's.
    assert.equal((await fold("daily", page.through, one)).body.error, "delta_not_listed");
    await list([delta("delta-2026-11-17-1.jsonl.gz", "the day's records", null)]);
    assert.equal((await fold("daily", page.through, one)).body.error, "delta_has_no_through");
    await list([delta("delta-2026-11-17-1.jsonl.gz", "another size", page.through)]);
    assert.equal((await fold("daily", page.through, one)).body.error, "delta_differs");
    await list([delta("delta-2026-11-17-1.jsonl.gz", "the day's records", 9999)]);
    assert.equal((await fold("daily", undefined, one)).body.error, "beyond_inbox");
    await list([delta("delta-2026-11-17-1.jsonl.gz", "the day's records", page.through), delta("delta-2026-11-17-2.jsonl.gz", "the rest", all.through)]);
    const other = await fold("daily", all.through, one);
    assert.deepEqual([other.status, other.body.error, other.body.detail.listed_through], [409, "through_differs", page.through]);
    const recorded = (await fold("daily", undefined, one)).body;
    assert.deepEqual([recorded.recorded, recorded.again, recorded.folded_through], [page.through, false, page.through]);
    // Recorded again, even after its list changed: the answer is what was recorded then.
    await list([delta("delta-2026-11-17-1.jsonl.gz", "the day's records", page.through - 1), delta("delta-2026-11-17-2.jsonl.gz", "the rest", all.through)]);
    const twice = (await fold("daily", undefined, one)).body;
    assert.deepEqual([twice.recorded, twice.again, twice.recorded_at, twice.folded_through], [page.through, true, recorded.recorded_at, page.through]);
    assert.equal(await counts().then((rows) => rows[0][4]), 6, "recording a fold clears nothing");
    assert.equal((await box.ask("POST", "/inbox/clear", { as: "daily", body: { through: page.through + 1 } })).status, 409);
    const cleared = (await box.ask("POST", "/inbox/clear", { as: "daily", body: { through: page.through } })).body;
    assert.deepEqual([cleared.cleared, cleared.left, cleared.leads_held], [5, 1, 1]);
    // The trial is gone. The lead is a reader's, and the consumer has not processed it yet:
    // it is held, with its share, though its records have left the inbox.
    assert.deepEqual(await counts(), [[2, 2, 0, 0, 1]]);
    assert.equal(await box.one("SELECT state FROM work_item WHERE record_key = 'inbox.example/one' AND step = 'lead_process'"), "due");
    const work = { kind: "link_lead", key: "inbox.example/one", step: "lead_process" };
    assert.equal((await box.ask("POST", "/work/finish", { as: "consumer", body: work })).body.state, "done");
    const again = (await box.ask("POST", "/inbox/clear", { as: "daily", body: { through: page.through } })).body;
    assert.deepEqual([again.cleared, again.left, again.leads_held], [0, 1, 0]);
    assert.deepEqual(await counts(), [[1, 1, 0, 0, 1]]);
    assert.equal(await box.one("SELECT url_key FROM link_lead"), "inbox.example/two");
    // The second run, cleared while its lead still waits, then after its work failed for good.
    const rest = (await box.ask("GET", `/inbox?after=${page.through}`, { as: "daily" })).body;
    assert.equal((await fold("operator", rest.through, two)).body.folded_through, rest.through);
    assert.deepEqual((await box.ask("POST", "/inbox/clear", { as: "daily", body: { through: rest.through } })).body.leads_held, 1);
    assert.equal(await box.one("SELECT count(*) FROM inbox_folded"), 1);
    await box.ask("POST", "/work/lease", { as: "consumer", body: { step: "lead_process" } });
    assert.equal((await box.ask("POST", "/work/fail", { as: "consumer", body: { ...work, key: "inbox.example/two", error: "reader_refused", max_attempts: 1 } })).body.state, "failed");
    assert.equal((await box.ask("POST", "/inbox/clear", { as: "daily", body: { through: rest.through } })).body.leads_held, 0);
    assert.deepEqual(await counts(), [[0, 0, 0, 0, 0]]);
    assert.equal(await box.one("SELECT count(*) FROM inbox_folded"), 0);
    // Clearing again, or with nothing there, changes nothing; the claim was never touched.
    assert.equal((await box.ask("POST", "/inbox/clear", { as: "operator", body: { through: rest.through } })).body.cleared, 0);
    assert.equal(await box.one("SELECT count(*) FROM claim"), 1);
  } finally { await box.close(); }
});

test("the inbox keeps every kind the pipeline calls bulk", { skip }, async () => {
  const { INBOX_KINDS } = await import("../src/kinds.mjs");
  const tiers = readFileSync(here("../../../pipeline/src/thenwhat/store/tiers.py"), "utf8");
  const bulk = [.../BULK_KINDS = frozenset\(\s*\{([^}]*)\}/.exec(tiers)[1].matchAll(/"([a-z_]+)"/g)].map(([, kind]) => kind);
  assert.ok(bulk.length > 5);
  assert.deepEqual(bulk.filter((kind) => !INBOX_KINDS.includes(kind)), []);
});

test("a registry record that names a person is refused, in a record and in the bucket", { skip }, async () => {
  const { peopleIn } = await import("../src/people.mjs");
  const clean = { protocolSection: { identificationModule: { nctId: "NCT900", briefTitle: "A trial" },
    contactsLocationsModule: { locations: [{ facility: "A hospital", city: "Leeds", country: "United Kingdom" }] },
    sponsorCollaboratorsModule: { leadSponsor: { name: "A university", class: "OTHER" }, responsibleParty: { type: "SPONSOR" }, collaborators: [{ name: "A company", class: "INDUSTRY" }] } },
    resultsSection: { moreInfoModule: { certainAgreement: { piSponsorEmployee: false } } } };
  assert.deepEqual(peopleIn(clean), []);
  assert.deepEqual(peopleIn({ nctId: "NCT1", email: "not a study" }), []);
  const each = {
    centralContacts: (s) => { s.protocolSection.contactsLocationsModule.centralContacts = [{ name: "A Person", role: "CONTACT" }]; },
    overallOfficials: (s) => { s.protocolSection.contactsLocationsModule.overallOfficials = [{ name: "A Person" }]; },
    "location contacts": (s) => { s.protocolSection.contactsLocationsModule.locations[0].contacts = [{ name: "A Person" }]; },
    "investigator name, title or affiliation": (s) => { s.protocolSection.sponsorCollaboratorsModule.responsibleParty.investigatorFullName = "A Person"; },
    "person lead sponsor's name": (s) => { s.protocolSection.sponsorCollaboratorsModule.responsibleParty.type = "SPONSOR_INVESTIGATOR"; },
    "person collaborator's name": (s) => { s.protocolSection.sponsorCollaboratorsModule.collaborators.push({ name: "A Person", class: "INDIV" }); },
    "results point of contact": (s) => { s.resultsSection.moreInfoModule.pointOfContact = { title: "A Person", organization: "A university" }; },
    email: (s) => { s.resultsSection.moreInfoModule.certainAgreement.email = "person@example.org"; },
    phone: (s) => { s.resultsSection.moreInfoModule.certainAgreement.phoneExt = "12"; },
  };
  for (const [field, add] of Object.entries(each)) {
    const study = structuredClone(clean);
    add(study);
    assert.deepEqual(peopleIn(study), [field], field);
    const text = JSON.stringify(study);
    const answer = await stageOne("lookup", "lookup", ["payload", sha(text), { sha256: sha(text), bytes: Buffer.byteLength(text), body: text }]);
    assert.deepEqual([answer?.status, answer?.body.error, answer?.body.detail.people], [422, "personal_data", [field]], field);
    assert.ok(!answer.text.includes("A Person") && !answer.text.includes("person@example.org"), "the refusal does not repeat who");
  }
  // The same record without people goes through, and so does a payload that is no registry record.
  const text = JSON.stringify(clean);
  assert.equal(await stageOne("lookup", "lookup", ["payload", sha(text), { sha256: sha(text), bytes: Buffer.byteLength(text), body: text }]), null);
  // Over 16 KB the record goes to the bucket, and is held to the same.
  const large = structuredClone(clean);
  large.protocolSection.descriptionModule = { detailedDescription: "d".repeat(17_000) };
  const kept = JSON.stringify(large);
  large.protocolSection.contactsLocationsModule.overallOfficials = [{ name: "A Person", affiliation: "A university" }];
  const named = JSON.stringify(large);
  const put = (body) => s.ask("PUT", `/payloads/${sha(body)}`, { as: "lookup", body, type: "application/octet-stream" });
  const refused = await put(named);
  assert.deepEqual([refused.status, refused.body.error, refused.body.detail.people], [422, "personal_data", ["overallOfficials"]]);
  const bucket = await s.mf.getR2Bucket("PAYLOADS");
  assert.equal(await bucket.head(`payload/${sha(named)}`), null, "nothing is stored for it");
  assert.equal((await put(kept)).status, 201);
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
