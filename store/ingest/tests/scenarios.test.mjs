// The proof's 62 scenarios (store/proof/proof.py), driven through the service's HTTP
// routes on D1's local engine. Every write is a request with a writer's token: register a
// run, put its payloads, stage, merge. What the store then holds is read through the
// binding. The numbering and the wording are the proof's, so the two can be read side by
// side; a note marks each place the proof wrote SQL directly and this asks the service.
//
// As in the proof, every merge is first reported without applying, here as a twin run
// that is previewed and dropped, and the two reports are held to each other (57, 58).
import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { setTimeout as wait } from "node:timers/promises";
import { PAYLOADS, Service, engineUnavailable, sha } from "./harness.mjs";

const skip = await engineUnavailable();
if (skip && process.env.CI) throw new Error(skip);

const SLUG = "semaglutide-obesity";
const T = "2026-11-01T00:00:00Z";
const today = () => new Date().toISOString().slice(0, 10);
const previews = { same: 0, differ: [], seen: 0, missed: [] };
const open = [];

// ---- records, in the natural-key form a writer hands over ---------------------------------

// A payload's checksum is really its body's, since the service checks. With a body it is
// small and travels in its record; without, it is over 16 KB and is put to R2 first.
const bodies = new Map();
function content(n, body) {
  if (body !== undefined) bodies.set(n, JSON.stringify(body));
  else if (!bodies.has(n)) bodies.set(n, `payload ${n} ${"x".repeat(17_000)}`);
  return bodies.get(n);
}
const digest = (n) => sha(content(n));

function payload(n, body) {
  const text = content(n, body);
  const record = { sha256: sha(text), bytes: Buffer.byteLength(text) };
  if (body !== undefined) record.body = text;
  else { record.r2_key = `payload/${record.sha256}`; PAYLOADS.set(record.sha256, text); }
  return ["payload", record.sha256, record];
}

function claim(slug = SLUG, { state = "approved", by = "rule", held = T, origin = "backfill", reviewed_at = T, ...more } = {}) {
  const body = { slug, headline: `Report on ${slug}`, summary: "s", vertical: "metabolic", indication: slug.split("-").at(-1), origin, created_at: T, awaiting_audit_at: held };
  if (state !== "pending") Object.assign(body, { review_state: state, reviewed_by: by, reviewed_at });
  return ["claim", slug, { ...body, ...more }];
}

const article = (key, slug = SLUG, date = "2026-10-01") => ["source_article", `${slug}|${key}`,
  { slug, url_key: key, url: `https://${key}`, outlet: key.split("/")[0], title: "t", published_date: date }];

const entity = (name = "semaglutide", slug = SLUG) => ["entity", `${slug}|intervention|${name}`, { slug, type: "intervention", name, synonyms: ["Wegovy"] }];

const match = (trialId, state, by, { score = 0.9, name = "semaglutide", slug = SLUG, at = T } = {}) => ["entity_match", `${slug}|${name}|${trialId}`,
  { slug, entity_type: "intervention", entity_name: name, source_name: "clinicaltrials.gov", external_id: trialId, score, review_state: state, reviewed_by: by, reviewed_at: at, created_at: T }];

function event({ trial: id = "NCT1", content: said = "c1", pay = 1, fetched = "2026-11-01T00:00:00Z", state = "approved", by = "rule", slug = SLUG } = {}) {
  const key = `clinicaltrials.gov|${id}|trial_registered|`;
  const body = { slug, dedupe_key: key, type: "trial_registered", event_date: "2020-01-01", source_name: "clinicaltrials.gov",
    source_url: `https://clinicaltrials.gov/study/${id}`, external_id: id, summary: "registered", confidence: 1, content_sha256: said,
    payload_sha256: digest(pay), fetched_at: fetched, created_at: T };
  if (state !== "pending") Object.assign(body, { review_state: state, reviewed_by: by, reviewed_at: T });
  return ["evidence_event", `${slug}|${key}`, body];
}

const trial = ({ number = "NCT1", status = "RECRUITING", pay = 10, fetched = "2026-11-01T00:00:00Z", title = "Semaglutide in obesity" } = {}) => ["registry_trial", `clinicaltrials.gov|${number}`,
  { registry_name: "clinicaltrials.gov", external_id: number, title, conditions: ["Obesity"], interventions: [{ type: "DRUG", name: "Semaglutide" }],
    intervention_names: "Semaglutide", phases: ["PHASE3"], overall_status: status, payload_sha256: digest(pay), fetched_at: fetched }];

function lead(key = "bbc.com/a", { score = 0.8, version = 3, origin = "file", shared = "2026-10-01T09:00:00Z", ...more } = {}) {
  const body = { url_key: key, url_key_version: 2, url: `https://${key}`, outlet: key.split("/")[0], outlet_kind: "general_news",
    title: "New obesity drug shows promise", first_shared_at: shared, origin, screen_outcome: "in_scope" };
  if (score !== null) Object.assign(body, { triage_score: score, triage_version: version });
  return ["link_lead", key, { ...body, ...more }];
}

const share = (key = "bbc.com/a", platform = "hackernews", at = "2026-10-01T09:00:00Z", score = 12) => ["link_share", `${key}|${platform}|${at}`,
  { lead_url_key: key, platform, community: platform, shared_at: at, score }];

const action = (kind, slug = SLUG, by = "human", more = {}) => ["action", `${kind}|${slug}`, { action: kind, slug, decided_by: by, at: "2026-11-16T12:00:00Z", ...more }];

// ---- a store, and a run through the service -----------------------------------------------

const AS = { device: "device-mini", daily: "daily", lookup: "lookup", consumer: "consumer", export: "export", operator: "operator" };

class Store {
  static async open() {
    const store = new Store();
    store.s = await Service.open();
    open.push(store.s);
    // The store's own setting, which no writer may change: the lowest triage version taken.
    await store.s.db.prepare("INSERT INTO store_step VALUES ('link_triage', 3)").run();
    store.runs = 0;
    return store;
  }

  one(sql, ...args) { return this.s.one(sql, ...args); }
  all(sql, ...args) { return this.s.all(sql, ...args); }

  // Hand a run over and merge it. Before the merge, the same records are handed over as a
  // twin run and reported without applying; afterwards the two reports are compared.
  async run(records, { writer = "device", as = AS[writer], name, ...more } = {}) {
    this.runs += 1;
    const id = name || `r${this.runs}`;
    const twin = `${id}-twin`;
    assert.equal(await this.s.hand(twin, records, { as, writer, ...more }), null);
    const counted = (await this.s.preview(twin, as)).body;
    assert.equal(await this.s.hand(id, records, { as, writer, ...more }), null);
    const merged = (await this.s.merge(id, as)).body;
    if (merged.status === "merged") {
      const same = JSON.stringify(sorted(counted.report)) === JSON.stringify(sorted(merged.report));
      if (same) previews.same += 1; else previews.differ.push([id, counted.report, merged.report]);
    } else if (merged.reason === "counts_do_not_reconcile") {
      if (!counted.reconciles) previews.seen += 1; else previews.missed.push(id);
    }
    // A run the merge undid still waits with its records; it is dropped, as its writer would.
    if (merged.status === "undone") await this.s.drop(id, as);
    return { ok: merged.status === "merged", id, as, ...merged };
  }

  async report(id, as = "device-mini") { return (await this.s.ask("GET", `/runs/${id}`, { as })).body.report; }

  async dump() {
    const out = [];
    for (const sql of [
      "SELECT slug, review_state, reviewed_by, archived_at IS NOT NULL, awaiting_audit_at IS NOT NULL FROM claim ORDER BY 1",
      "SELECT c.slug, a.url_key FROM source_article a JOIN claim c ON c.id = a.claim_id ORDER BY 1, 2",
      "SELECT c.slug, e.dedupe_key, e.content_sha256, e.review_state FROM evidence_event e JOIN claim c ON c.id = e.claim_id ORDER BY 1, 2",
      "SELECT e.name, m.external_id, m.review_state, m.reviewed_by FROM entity_match m JOIN entity e ON e.id = m.entity_id ORDER BY 1, 2",
      "SELECT url_key, triage_score, triage_version, read_outcome FROM link_lead ORDER BY 1",
      "SELECT registry_name, external_id, overall_status, payload_sha256 FROM registry_trial ORDER BY 1, 2"]) out.push(await this.all(sql));
    return out;
  }
}

const sorted = (object) => Object.fromEntries(Object.entries(object).sort(([a], [b]) => a.localeCompare(b)));
const counts = (resolved, added, conflicts, matched) => ({ resolved, added, conflicts, matched });

// A store holding one held claim with an article, an entity, an approved event.
async function base() {
  const s = await Store.open();
  const first = await s.run([payload(1), claim(), article("bbc.com/a"), entity(), event()]);
  assert.ok(first.ok, JSON.stringify(first));
  return [s, first];
}

const results = [];
const check = (name, ok) => results.push([name, Boolean(ok)]);
const eq = (a, b) => { try { assert.deepStrictEqual(a, b); return true; } catch { return false; } };

async function scenarios() {
  // -- the spike's fourteen, on the designed schema --
  let [s, r1] = await base();
  check("1 claim absent: added with its records", await s.one("SELECT count(*) FROM claim") === 1
    && await s.one("SELECT count(*) FROM source_article") === 1 && await s.one("SELECT count(*) FROM evidence_event") === 1);
  check("2 audit mark carried on a new claim", await s.one("SELECT awaiting_audit_at FROM claim") === T);
  check("3 report reconciles", eq(sorted(await s.report(r1.id)), sorted({ payload: counts(1, 1, 0, 0), claim: counts(1, 1, 0, 0),
    source_article: counts(1, 1, 0, 0), entity: counts(1, 1, 0, 0), evidence_event: counts(1, 1, 0, 0) })));
  let before = await s.dump();
  const again = (await s.s.merge(r1.id)).body;
  check("4 same run twice: nothing changes, first time reported", again.status === "merged" && again.again && again.merged_at === r1.merged_at
    && eq(await s.dump(), before) && await s.one("SELECT status FROM run WHERE id = ?", r1.id) === "merged" && await s.one("SELECT count(*) FROM stg") === 0);
  let r = await s.run([article("reuters.com/b"), article("bbc.com/a")]);
  check("5 claim present: new article added, known one matched", r.ok && eq(r.report.source_article, counts(2, 1, 0, 1)));

  await s.run([action("audit_clear"), action("archive", SLUG, "human", { reason: "not one treatment" })], { writer: "operator" });
  // The proof set a person's rejection with an UPDATE; here a person's decision is pushed.
  await s.run([claim(SLUG, { state: "rejected", by: "human", held: null, reviewed_at: "2026-11-02T00:00:00Z" })]);
  r = await s.run([claim(SLUG, { held: null }), article("stat.com/c")]);
  check("6 archived stays archived, a person's decision kept, article stored", r.ok
    && eq(await s.all("SELECT archived_at IS NOT NULL, review_state, reviewed_by FROM claim"), [[1, "rejected", "human"]])
    && await s.one("SELECT count(*) FROM source_article") === 3);
  check("7 a merge never clears the audit mark", await s.one("SELECT awaiting_audit_at FROM claim") === null);
  await s.run([claim()]);
  check("8 audit mark carried onto a claim already held", await s.one("SELECT awaiting_audit_at FROM claim") === T);

  [s] = await base();
  await s.run([match("NCT9", "rejected", "human", { score: 0.4 })]);
  await s.run([match("NCT9", "approved", "rule", { score: 0.97, at: "2026-12-01T00:00:00Z" }), match("NCT8", "approved", "rule", { score: 0.99 })]);
  check("9 a person's rejection of a match stands; a new match is added",
    eq(await s.all("SELECT review_state, reviewed_by FROM entity_match WHERE external_id = 'NCT9'"), [["rejected", "human"]])
    && await s.one("SELECT count(*) FROM entity_match") === 2);
  await s.run([match("NCT8", "rejected", "human")]);
  check("10 a person's decision replaces a rule's", eq(await s.all("SELECT review_state, reviewed_by FROM entity_match WHERE external_id = 'NCT8'"), [["rejected", "human"]]));

  [s] = await base();
  await s.run([action("audit_clear")], { writer: "operator" });
  r = await s.run([payload(2), event({ content: "c2", pay: 2, fetched: "2026-11-10T00:00:00Z" })], { writer: "daily" });
  check("11 differing evidence: stored kept, new kept apart with reason, claim held, one conflict", r.ok
    && await s.one("SELECT content_sha256 FROM evidence_event") === "c1"
    && eq(await s.all("SELECT content_sha256, reason, state FROM evidence_conflict"), [["c2", "differs from the approved event stored", "open"]])
    && await s.one("SELECT awaiting_audit_at FROM claim") !== null && eq(r.report.evidence_event, counts(1, 0, 1, 0)));
  before = await s.dump();
  r = await s.run([claim("x-y")], { steps: { link_triage: 2 } });
  check("12 older step version: refused, naming the step, nothing stored", r.status === "refused" && eq(await s.dump(), before)
    && eq(await s.all("SELECT status, refusal FROM run WHERE id = ?", r.id), [["refused", "step link_triage is at version 2, the store accepts 3"]])
    && r.refusal === "step link_triage is at version 2, the store accepts 3" && await s.one("SELECT count(*) FROM stg") === 0);
  r = await s.run([claim("x-y"), article("a.com/1", "x-y")], { stated: { claim: 1, source_article: 2 } });
  check("13 counts that do not reconcile: batch undone", r.status === "undone" && r.reason === "counts_do_not_reconcile" && eq(await s.dump(), before));

  const two = async (order) => {
    const [d] = await base();
    const runs = { a: [article("ft.com/z"), article("nyt.com/q")], b: [article("ft.com/z"), article("sky.com/k")] };
    for (const name of order) await d.run(runs[name]);
    return d.dump();
  };
  const ab = await two("ab");
  check("14 two runs on one claim: same store in either order", eq(ab, await two("ba")) && ab[1].length === 4);

  // -- what the spec asks beyond the spike --
  [s] = await base();
  before = await s.dump();
  r = await s.run([article("a.com/1", "no-such-claim")]);
  check("15 a record whose claim the store lacks: batch undone", r.status === "undone" && eq(await s.dump(), before));
  r = await s.run([event({ trial: "NCT5", pay: 404 })]);
  check("16 an event whose payload was never handed over: batch undone", r.status === "undone" && eq(await s.dump(), before));
  const rows = async () => {
    const out = [];
    for (const t of ["run", "run_step", "run_stated", "stg", "merging", "merge_report", "source_article", "ingest_chunk"]) out.push(await s.one(`SELECT count(*) FROM ${t}`));
    return out;
  };
  const untouched = await rows();
  assert.equal(await s.s.hand("dry", [article("dry.com/1"), article("bbc.com/a")]), null);
  const dry = (await s.s.preview("dry")).body;
  check("17 report without applying: counted, not tried; one would be added and one matched",
    eq(dry.report, { source_article: counts(2, 1, 0, 1) }) && dry.reconciles && dry.not_checked.length === 2 && eq(await s.dump(), before));
  check("17b after it the run is dropped and the store is as it was", eq(await rows(), untouched)
    && await s.one("SELECT count(*) FROM run WHERE id = 'dry'") === 0);
  const keyless = await s.s.hand("keyless", [["claim", "", {}]]);
  check("18 a record without its natural key is refused at the door", keyless?.status === 400 && keyless.body.error === "no_natural_key"
    && await s.one("SELECT count(*) FROM stg") === 0);
  await s.s.drop("keyless");
  const text = JSON.stringify([{ kind: "claim", key: "k", body: {} }]);
  const nobody = await s.s.ask("POST", "/runs/nobody/records", { as: "device-mini", body: text, headers: { "x-content-sha256": sha(text) } });
  check("19 records for a run never registered are not stored", nobody.status === 404 && await s.one("SELECT count(*) FROM stg WHERE run_id = 'nobody'") === 0);

  // -- evidence: a refetch that says the same is not a conflict --
  [s] = await base();
  await s.run([action("audit_clear")], { writer: "operator" });
  r = await s.run([payload(3), event({ content: "c1", pay: 3, fetched: "2026-11-12T00:00:00Z" })], { writer: "daily" });
  check("20 a later fetch that says the same: no conflict, no hold, newest payload kept", r.ok
    && await s.one("SELECT count(*) FROM evidence_conflict") === 0 && await s.one("SELECT awaiting_audit_at FROM claim") === null
    && await s.one("SELECT payload_sha256 FROM evidence_event") === digest(3) && eq(r.report.evidence_event, counts(1, 0, 0, 1)));
  await s.run([payload(4), event({ content: "c9", pay: 4, fetched: "2026-11-13T00:00:00Z" })], { writer: "daily" });
  await s.run([payload(4), event({ content: "c9", pay: 4, fetched: "2026-11-13T00:00:00Z" })], { writer: "device" });
  check("21 the same difference from two runs is kept apart once", await s.one("SELECT count(*) FROM evidence_conflict") === 1);
  r = await s.run([action("audit_clear")], { writer: "operator" });
  check("22 a claim is not cleared while its evidence is still kept apart", r.ok && await s.one("SELECT awaiting_audit_at FROM claim") !== null);
  await s.run([action("conflict_accept", SLUG, "human", { dedupe_key: "clinicaltrials.gov|NCT1|trial_registered|", content_sha256: "c9" })], { writer: "operator" });
  await s.run([["action", "clear2", action("audit_clear")[2]]], { writer: "operator" });
  check("23 accepted evidence replaces the stored event, and the claim can then be cleared",
    eq(await s.all("SELECT content_sha256, review_state, reviewed_by FROM evidence_event"), [["c9", "approved", "human"]])
    && await s.one("SELECT state FROM evidence_conflict") === "accepted" && await s.one("SELECT awaiting_audit_at FROM claim") === null);
  const [s2] = await base();
  await s2.run([payload(5), event({ trial: "NCT7", content: "p1", pay: 5, state: "pending" })]);
  await s2.run([payload(6), event({ trial: "NCT7", content: "p2", pay: 6, fetched: "2026-11-20T00:00:00Z" })]);
  check("24 a pending event is replaced by a later fetch and takes its decision",
    eq(await s2.all("SELECT content_sha256, review_state FROM evidence_event WHERE external_id = 'NCT7'"), [["p2", "approved"]]));

  // -- trials: the load and what a trial page reads --
  s = await Store.open();
  r = await s.run([payload(10, { nctId: "NCT1" }), trial()], { writer: "daily" });
  check("25 a trial absent: added with its payload and first state", r.ok && eq(r.report.registry_trial, counts(1, 1, 0, 0))
    && eq(await s.all("SELECT overall_status FROM registry_trial_status"), [["RECRUITING"]]));
  r = await s.run([trial({ fetched: "2026-11-05T00:00:00Z" })], { writer: "daily" });
  check("26 a trial fetched again unchanged: matched, checked time moves, payload time does not", r.ok
    && eq(r.report.registry_trial, counts(1, 0, 0, 1))
    && eq(await s.all("SELECT fetched_at, checked_at FROM registry_trial"), [["2026-11-01T00:00:00Z", "2026-11-05T00:00:00Z"]]));
  await s.run([payload(11, { nctId: "NCT1", v: 2 }), trial({ status: "COMPLETED", pay: 11, fetched: "2026-11-09T00:00:00Z" })], { writer: "daily" });
  check("27 a trial that changed: replaced whole, and its history has both states", await s.one("SELECT overall_status FROM registry_trial") === "COMPLETED"
    && eq((await s.all("SELECT overall_status FROM registry_trial_status ORDER BY seen_at")).map((x) => x[0]), ["RECRUITING", "COMPLETED"]));
  await s.run([payload(12, { old: 1 }), trial({ status: "RECRUITING", pay: 12, fetched: "2026-10-01T00:00:00Z" })], { writer: "device" });
  check("28 an older fetch never replaces a newer record", await s.one("SELECT overall_status FROM registry_trial") === "COMPLETED");
  check("29 trial search finds it by condition and by intervention",
    await s.one("SELECT count(*) FROM registry_trial_fts WHERE registry_trial_fts MATCH 'obesity'") === 1
    && await s.one("SELECT t.external_id FROM registry_trial_fts f JOIN registry_trial t ON t.id = f.rowid WHERE registry_trial_fts MATCH 'intervention_names:semaglutide'") === "NCT1");
  const page = await s.all(`SELECT t.title, t.overall_status, p.body IS NOT NULL FROM registry_trial t
    JOIN payload p ON p.sha256 = t.payload_sha256 WHERE t.registry_name = ? AND t.external_id = ?`, "clinicaltrials.gov", "NCT1");
  check("30 a plain trial page is one keyed read, payload included", eq(page, [["Semaglutide in obesity", "COMPLETED", 1]]));

  // -- leads, and what a reader's lookup leaves --
  s = await Store.open();
  await s.run([lead(), share()]);
  await s.run([lead("bbc.com/a", { score: 0.2, version: 2 })]);
  await s.run([lead("bbc.com/a", { score: 0.9, version: 4, read_outcome: "cannot_be_read" })], { steps: { link_triage: 4 } });
  check("32 a lead's score is taken only from a higher triage version; a read outcome once",
    eq(await s.all("SELECT triage_score, triage_version, read_outcome FROM link_lead"), [[0.9, 4, "cannot_be_read"]]));
  const day = "2026-11-16";
  const reader = (key, at) => ["link_share", `${key}|reader|${at}`, { lead_url_key: key, platform: "reader", community: "reader", shared_at: at, score: 0 }];
  r = await s.run([lead("stat.com/new", { score: null, origin: "reader", shared: day }), reader("stat.com/new", day),
    payload(20, { nctId: "NCT20" }), trial({ number: "NCT20", pay: 20 }),
    ["lead_reading", "stat.com/new", { lead_url_key: "stat.com/new", intervention: "retatrutide", indication: "obesity", confidence: 0.8,
      read_version: 1, read_on: day, trials: [{ registry: "clinicaltrials.gov", trial_id: "NCT20", score: 0.7 }] }]], { writer: "lookup" });
  check("33 a lookup leaves a lead, a reader share, the trial and a reading; no claim, event or match", r.ok
    && await s.one("SELECT count(*) FROM link_lead WHERE origin = 'reader'") === 1 && await s.one("SELECT count(*) FROM lead_reading") === 1
    && await s.one("SELECT count(*) FROM registry_trial") === 1
    && await s.one("SELECT (SELECT count(*) FROM claim) + (SELECT count(*) FROM evidence_event) + (SELECT count(*) FROM entity_match)") === 0);
  await s.run([lead("stat.com/new", { score: null, origin: "reader", shared: day }), reader("stat.com/new", day)], { writer: "lookup" });
  check("34 the same article asked about twice in a day: one lead, one share", await s.one("SELECT count(*) FROM link_share WHERE platform = 'reader'") === 1);
  const fine = await s.all(`SELECT 1 FROM run WHERE writer = 'lookup' AND (length(registered_at) > 10 OR length(merged_at) > 10)
    UNION ALL SELECT 1 FROM link_share WHERE platform = 'reader' AND length(shared_at) > 10
    UNION ALL SELECT 1 FROM work_item WHERE record_key = 'stat.com/new' AND length(due_since) > 10`);
  check("35 nothing a lookup leaves holds a time finer than the day", eq(fine, []) && await s.one("SELECT count(*) FROM run WHERE writer = 'lookup'") >= 2);
  check("36 a reader's lead is due for processing once", eq(await s.all("SELECT state, attempts FROM work_item WHERE step = 'lead_process'"), [["due", 0]]));
  r = await s.run([reader("stat.com/new", "2026-11-17T08:01:02Z")], { writer: "lookup" });
  check("37 a reader share with a time of day cannot be stored", r.status === "undone");
  r = await s.run([lead("blog.example/x", { outlet_kind: "unknown" })]);
  check("38 a lead on an unlisted outlet cannot be stored", r.status === "undone");
  // The proof gave the queue its times; the service reads its own clock, so the lease is
  // one second long and the test waits for it to lapse.
  const lease = async () => (await s.s.ask("POST", "/work/lease", { as: "consumer", body: { step: "lead_process", count: 5, lease_seconds: 1 } })).body.leased;
  const a = await lease(), b = await lease();
  await wait(2100);
  const c = await lease();
  check("39 due work is leased to one consumer, and taken again when the lease lapses", a.length === 1 && b.length === 0 && c.length === 1);
  for (let i = 0; i < 2; i += 1) {
    await s.s.ask("POST", "/work/fail", { as: "consumer", body: { kind: "link_lead", key: "stat.com/new", step: "lead_process", error: "reader_refused", max_attempts: 2 } });
  }
  check("40 work that keeps failing is left with its error, not lost", eq(await s.all("SELECT state, error FROM work_item WHERE step = 'lead_process'"), [["failed", "reader_refused"]]));

  // -- publication by rule: a reader's claim beside a backfill's --
  s = await Store.open();
  await s.run([claim("from-backfill"), claim("from-reader", { held: null, origin: "lookup" })], { writer: "consumer" });
  r = await s.run([action("publish", "from-backfill", "rule"), action("publish", "from-reader", "rule")], { writer: "export" });
  check("41 a reader's claim is published by rule; a backfill's waits for its audit", r.ok && eq(await s.all("SELECT slug FROM claim_public"), [["from-reader"]]));
  const first = await s.one("SELECT published_at FROM claim WHERE slug = 'from-reader'");
  await s.run([["action", "again", { action: "publish", slug: "from-reader", at: "2027-01-01T00:00:00Z" }]], { writer: "export" });
  check("42 a published time is never changed", await s.one("SELECT published_at FROM claim WHERE slug = 'from-reader'") === first);
  const listed = await s.all(`SELECT c.slug FROM claim_action a JOIN claim c ON c.id = a.claim_id
    WHERE a.action = 'publish' AND c.origin = 'lookup' AND substr(a.at, 1, 10) = '2026-11-16'`);
  check("43 claims published from readers' leads can be listed by day", eq(listed, [["from-reader"]]));

  // -- the operator: archive, unarchive, rename, merge --
  [s] = await base();
  await s.run([action("audit_clear"), action("archive", SLUG, "human", { reason: "wrong trial" })], { writer: "operator" });
  r = await s.run([action("unarchive", SLUG, "assistant")], { writer: "operator" });
  check("44 only a person unarchives", r.status === "undone" && await s.one("SELECT archived_at FROM claim") !== null);
  r = await s.run([action("unarchive")], { writer: "operator" });
  check("45 a person unarchives, and the action is on record", r.ok && await s.one("SELECT archived_at FROM claim") === null
    && eq((await s.all("SELECT action FROM claim_action ORDER BY id")).map((x) => x[0]), ["audit_clear", "archive", "unarchive"]));

  r = await s.run([action("rename", SLUG, "human", { new_slug: "semaglutide-weight" })], { writer: "operator" });
  let r2 = await s.run([article("late.com/1")], { writer: "device" });
  check("46 a renamed claim answers to both slugs: a device's late push still lands", r.ok && r2.ok
    && eq(await s.all("SELECT slug FROM claim"), [["semaglutide-weight"]]) && await s.one("SELECT count(*) FROM source_article") === 2);
  await s.run([claim("other-claim", { held: null })]);
  r = await s.run([action("rename", "other-claim", "human", { new_slug: "semaglutide-weight" })], { writer: "operator" });
  check("47 a rename onto a slug another claim holds is undone", r.status === "undone" && await s.one("SELECT count(*) FROM claim WHERE slug = 'other-claim'") === 1);

  await s.run([article("dup.com/1", "other-claim", "2026-01-05"), article("late.com/1", "other-claim"), lead("dup.com/1", { claim_slug: "other-claim" })]);
  await s.run([match("NCT1", "rejected", "human", { name: "semaglutide", slug: "semaglutide-weight" })]);
  r = await s.run([action("merge", "other-claim", "human", { into_slug: "semaglutide-weight" })], { writer: "operator" });
  const kept = await s.one("SELECT id FROM claim WHERE slug = 'semaglutide-weight'");
  check("48 merged claim: archived, pointing at the one that stays", r.ok
    && eq(await s.all("SELECT merged_into, archived_at IS NOT NULL, archive_reason FROM claim WHERE slug = 'other-claim'"), [[kept, 1, "merged into semaglutide-weight"]]));
  check("49 merged claim: its articles and leads move, a shared article is not doubled",
    await s.one("SELECT count(*) FROM source_article WHERE claim_id = ?", kept) === 3 && await s.one("SELECT claim_id FROM link_lead WHERE url_key = 'dup.com/1'") === kept);
  check("50 merged claim: the kept claim's decisions stand, first report is the earlier, prepare is due",
    eq(await s.all("SELECT review_state, reviewed_by FROM entity_match"), [["rejected", "human"]])
    && await s.one("SELECT first_reported_date FROM claim WHERE id = ?", kept) === "2026-01-05"
    && await s.one("SELECT state FROM work_item WHERE record_key = 'semaglutide-weight' AND step = 'prepare'") === "due");
  r = await s.run([article("after.com/1", "other-claim")], { writer: "device" });
  check("51 records pushed for a merged claim go to the claim that stays", r.ok && await s.one("SELECT claim_id FROM source_article WHERE url_key = 'after.com/1'") === kept);
  check("52 claim search finds the claim by a synonym of its intervention",
    await s.one("SELECT c.slug FROM claim_fts f JOIN claim c ON c.id = f.rowid WHERE claim_fts MATCH 'wegovy'") === "semaglutide-weight");

  // -- spend by writer, slices, provenance --
  s = await Store.open();
  const use = (n, cost) => ["usage", String(n), { seq: n, purpose: "triage", model: "m", input_tokens: 10, output_tokens: 1, cost_usd: cost, created_at: "2026-11-16" }];
  await s.run([use(1, 1.5)], { as: "device-mini" });
  await s.run([use(1, 2.0)], { as: "device-macbook", writer: "device" });
  await s.run([use(1, 0.25)], { writer: "lookup" });
  check("53 the month's spend is shown by device and by lookups", eq(await s.all("SELECT who, cost_usd FROM spend_by_writer ORDER BY 1"), [["extension", 0.25], ["macbook", 2.0], ["mini", 1.5]]));
  // As with the queue: the taking lapses after a second, by the service's clock.
  const take = (as) => s.s.ask("POST", "/slices/take", { as, body: { platform: "reddit", community: "science", month: "2026-03", lapse_seconds: 1 } });
  const took = await take("device-mini"), lost = await take("device-macbook");
  await wait(2100);
  const late = await take("device-macbook");
  check("54 a slice is given to one device, and to another only when the taking lapsed", took.body.device === "mini" && lost.status === 409 && !lost.body.taken && late.body.device === "macbook");
  r = await s.run([["work_slice", "reddit|science|2026-03", { platform: "reddit", community: "science", month: "2026-03" }]], { as: "device-mini" });
  check("55 a slice never blocks a merge: done, and noted as not held", r.ok && eq(await s.all("SELECT done_run IS NOT NULL, unheld FROM work_slice"), [[1, 1]]));
  [s] = await base();
  check("56 which records one run added is answered from the records alone", await s.one(
    "SELECT count(*) FROM source_article a JOIN run r ON r.id = a.added_run WHERE r.device = 'mini' AND substr(r.registered_at, 1, 10) = ?", today()) === 1);
  // -- what the pipeline's own merge and rename do (claims/corrections.py), mirrored --
  [s] = await base();
  r = await s.run([action("rename", SLUG, "human", { old_name: "semaglutide", new_name: "semaglutide injection" })], { writer: "operator" });
  check("59 a rename of the intervention: new name, old one kept as a synonym, same slug, registries due again", r.ok
    && eq(await s.all("SELECT name, synonyms FROM entity"), [["semaglutide injection", '["Wegovy","semaglutide"]']])
    && eq(await s.all("SELECT slug FROM claim"), [[SLUG]])
    && await s.one("SELECT state FROM work_item WHERE record_key = ? AND step = 'prepare'", SLUG) === "due");
  r = await s.run([entity("tirzepatide")]);
  check("60 a claim has one intervention, never two", r.status === "undone" && await s.one("SELECT count(*) FROM entity") === 1);
  const company = (slug) => ["entity", `${slug}|company|Novo Nordisk`, { slug, type: "company", name: "Novo Nordisk" }];
  const paper = ["entity", "dup|paper|STEP 1", { slug: "dup", type: "paper", name: "STEP 1" }];
  await s.run([company(SLUG), claim("dup", { held: null }), entity("Ozempic", "dup"), company("dup"), paper, match("NCT4", "approved", "rule", { name: "Ozempic", slug: "dup" })]);
  r = await s.run([action("merge", "dup", "human", { into_slug: SLUG, gains: ["Ozempic", "Wegovy"] })], { writer: "operator" });
  const stays = await s.one("SELECT id FROM claim WHERE slug = ?", SLUG);
  check("61 a merge moves what an article named and the names listed; a name both hold is not doubled", r.ok
    && ['["Wegovy","semaglutide","Ozempic"]', '["Ozempic","Wegovy","semaglutide"]'].includes(await s.one("SELECT synonyms FROM entity WHERE claim_id = ? AND type = 'intervention'", stays))
    && await s.one("SELECT claim_id FROM entity WHERE name = 'STEP 1'") === stays
    && await s.one("SELECT count(*) FROM entity WHERE name = 'Novo Nordisk' AND claim_id = ?", stays) === 1);
  check("62 what a registry said does not move with a merge: the match stays with the claim that went", await s.one(
    "SELECT c.slug FROM entity_match m JOIN entity e ON e.id = m.entity_id JOIN claim c ON c.id = e.claim_id WHERE m.external_id = 'NCT4'") === "dup");

  check(`57 the report without applying said what the merge then said, for every merge above (${previews.same})`,
    !previews.differ.length && !previews.missed.length && previews.same >= 50);
  check(`58 it also said so of every run whose counts did not reconcile (${previews.seen})`, previews.seen >= 2);
}

before(async () => { if (!skip) await scenarios(); });
after(async () => { for (const service of open) await service.close(); });

// Each of the proof's scenarios is its own test, so a failure names the scenario.
const SCENARIOS = 62;
test("the proof's scenarios pass through the service's HTTP routes", { skip: skip ?? false }, async (t) => {
  assert.equal(results.length, SCENARIOS, "the proof has 62 scenarios (its numbering skips 31 and has 17b)");
  for (const [name, ok] of results) await t.test(name, () => assert.ok(ok, name));
  if (previews.differ.length) console.error("reports that differed:", JSON.stringify(previews.differ));
});
