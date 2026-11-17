// A merge's report says how many records of each kind it added. Nine kinds have tables
// that do not carry the run that added a row (a link, a label, a day's totals, a ledger
// entry, an icon, a load, a slice, a count), and the report used to say "0 added" of all
// of them though the rows were written. Each is counted by its key just before it is
// written (store/merge.sql), and the report without applying counts the same way
// (store/preview.sql).
//
// One test a kind, each through the service's routes on D1's local engine: a record the
// store has none of is reported added, the same record from another run is reported
// matched, and a run of one of each is reported as one and one. The preview is held to
// the merge's own report each time, and the rows are counted in the table itself.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { Service, engineUnavailable } from "./harness.mjs";

const skip = (await engineUnavailable()) ?? false;
if (skip && process.env.CI) throw new Error(skip);

const SLUG = "semaglutide-obesity";
const OTHER = "tirzepatide-obesity";
const T = "2026-11-01T00:00:00.000000+00:00";
const counts = (resolved, added, conflicts, matched) => ({ resolved, added, conflicts, matched });

const claim = (slug) => ["claim", slug, { slug, headline: `Report on ${slug}`, summary: "s", vertical: "metabolic",
  indication: "obesity", origin: "entry", created_at: T }];
const article = (key) => ["source_article", `${SLUG}|${key}`, { slug: SLUG, url_key: key, url: `https://${key}`,
  outlet: key.split("/")[0], title: "t", published_date: "2026-10-01" }];
const lead = (key) => ["link_lead", key, { url_key: key, url_key_version: 2, url: `https://${key}`, outlet: key.split("/")[0],
  outlet_kind: "general_news", title: "New obesity drug shows promise", first_shared_at: T, origin: "file",
  screen_outcome: "in_scope", triage_score: 0.8, triage_version: 3 }];

// For each kind: the table its rows go to, and two records that differ in their key.
const daily = (day) => ["measure_daily", `${day}|link_triage|3|mini|done`, { day, step: "link_triage", step_version: 3,
  writer: "mini", outcome: "done", spans: 1, records: 4, reused: 0, ran_seconds: 1.5, waited_seconds: 0,
  waited_by_cause: {}, requests_by_source: {}, tokens_in: 10, tokens_out: 2, cost_usd: 0.01, inner_cost_usd: 0, rows_written: 4 }];
const KINDS = {
  entity_article: { table: "entity_article", as: "operator", records: ["bbc.com/a", "reuters.com/b"].map((key) =>
    ["entity_article", `${SLUG}|intervention|semaglutide|${key}`, { slug: SLUG, entity_type: "intervention", entity_name: "semaglutide", url_key: key }]) },
  registry_load: { table: "registry_load", as: "operator", records: ["obesity", "diabetes"].map((condition) =>
    ["registry_load", `clinicaltrials.gov|${condition}`, { registry_name: "clinicaltrials.gov", condition, loaded_from: T, completed_at: T }]) },
  link_lead_label: { table: "link_lead_label", as: "operator", records: ["human", "assistant"].map((by) =>
    ["link_lead_label", `bbc.com/a|${by}`, { lead_url_key: "bbc.com/a", labelled_by: by, label: "not_health", labelled_at: T }]) },
  measure_daily: { table: "measure_daily", as: "operator", records: ["2026-11-15", "2026-11-16"].map(daily) },
  measure_claim: { table: "measure_claim", as: "operator", records: [SLUG, OTHER].map((slug) =>
    ["measure_claim", slug, { slug, first_seen_at: T, last_step_at: T, spans: 2, ran_seconds: 3, waited_seconds: 1, cost_usd: 0.02 }]) },
  work_entry: { table: "work_entry", as: "operator", records: [1, 2].map((version) =>
    ["work_entry", `claim|${SLUG}|news_search|${version}`, { record_kind: "claim", record_key: SLUG, step: "news_search",
      step_version: version, outcome: "done", attempts: 1, requests_used: 2, fingerprint: "f", last_attempt_at: T }]) },
  outlet_icon: { table: "outlet_icon", as: "operator", records: ["bbc.com", "reuters.com"].map((domain) =>
    ["outlet_icon", domain, { domain, icon_url: `https://${domain}/i.png`, media_type: "image/png", content_hex: "89504e470d0a1a0a", fetched_at: T }]) },
  work_slice: { table: "work_slice", as: "operator", records: ["2026-03", "2026-04"].map((month) =>
    ["work_slice", `reddit|science|${month}`, { platform: "reddit", community: "science", month }]) },
  unlisted_domain: { table: "unlisted_domain_count", as: "lookup", records: ["blog.example", "forum.example"].map((domain) =>
    ["unlisted_domain", `${domain}|2026-11-16`, { domain, day: "2026-11-16", asked: 1 }]) },
};

let s;
before(async () => {
  if (skip) return;
  s = await Service.open();
  const parents = [claim(SLUG), claim(OTHER), article("bbc.com/a"), article("reuters.com/b"),
    ["entity", `${SLUG}|intervention|semaglutide`, { slug: SLUG, type: "intervention", name: "semaglutide" }], lead("bbc.com/a")];
  assert.equal(await s.hand("parents", parents, { as: "operator" }), null);
  assert.equal((await s.merge("parents", "operator")).body.status, "merged");
});
after(async () => { if (s) await s.close(); });

// Take the report without applying from a twin run, which the service drops once it has
// answered; then hand the run over, merge it, and hold the two reports together.
async function reported(id, records, as) {
  const twin = await s.hand(`${id}-twin`, records, { as });
  assert.equal(twin, null, `handing over ${id}: ${twin?.text}`);
  const counted = (await s.preview(`${id}-twin`, as)).body;
  assert.equal(await s.hand(id, records, { as }), null);
  const merged = (await s.merge(id, as)).body;
  assert.equal(merged.status, "merged", JSON.stringify(merged));
  assert.deepEqual(counted.report, merged.report, "the report without applying says what the merge says");
  return merged.report;
}

for (const [kind, { table, as, records: [first, second] }] of Object.entries(KINDS)) {
  test(`a merge's report counts the ${kind} records it adds`, { skip }, async () => {
    const rows = () => s.one(`SELECT count(*) FROM ${table}`);
    const held = await rows();

    assert.deepEqual((await reported(`${kind}-1`, [first], as))[kind], counts(1, 1, 0, 0), "a record the store has none of is added");
    assert.equal(await rows(), held + 1);

    assert.deepEqual((await reported(`${kind}-2`, [first], as))[kind], counts(1, 0, 0, 1), "the same record from another run is matched");
    assert.equal(await rows(), held + 1);

    assert.deepEqual((await reported(`${kind}-3`, [first, second], as))[kind], counts(2, 1, 0, 1), "one of each is one added and one matched");
    assert.equal(await rows(), held + 2);
  });
}
