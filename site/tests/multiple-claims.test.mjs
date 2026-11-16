// The public lookup seam: independent synthetic claims never borrow each other's
// identity, score or card, and a roundup shares one work allowance. No network.
import assert from "node:assert/strict";
import { test } from "node:test";
import { lookUp } from "../worker/lookup.mjs";
import { describeAnswer } from "../src/lib/live-lookup.mjs";
import { withCurrentClaims } from "../worker/tracked.mjs";
import { previousResult, storeResult } from "../worker/results.mjs";
import { handle } from "../worker/index.mjs";
import { remember, completed, reusable } from "../../extension/src/results.js";

const claim = (intervention, indication, extra = {}) => ({
  about_a_treatment: true, intervention, indication, gist: `${intervention} for ${indication}`,
  other_names: [], known_names: [], search_phrases: [], ...extra,
});
const first = claim("EX-1", "example condition one");
const second = claim("EX-2 plus EX-3", "example condition two");
const reading = { ...first, additional_claims: [second] };
const study = (id, intervention, condition) => ({ protocolSection: {
  identificationModule: { nctId: id, briefTitle: `${intervention} study` },
  conditionsModule: { conditions: [condition] },
  armsInterventionsModule: { interventions: [{ name: intervention }] },
} });
const a = study("NCT00000001", first.intervention, first.indication);
const b = study("NCT00000002", second.intervention, second.indication);
const index = { claims: Object.fromEntries([first, second].map((one, at) => [`card-${at}`, {
  names: [one.intervention], indication: one.indication, headline: one.gist, page: `/card-${at}`,
}])) };
const quiet = { fetch: async () => null, named: async () => [], search: async () => [] };
const yes = () => ({ answer: "match", probabilities: { match: .9 } });
const memory = () => { const values = new Map(); return {
  values, get: async key => JSON.parse(values.get(key) ?? "null"),
  put: async (key, value) => { values.set(key, value); },
}; };

test("one reading gives independent trial scores and complete-regimen cards, with shared record fetches", async () => {
  let reads = 0, scoringCalls = 0;
  const fetched = [];
  const model = {
    read: async () => { reads++; return reading; },
    score: async (_intro, items) => {
      scoringCalls++;
      return items.map(item => {
        const claimText = item.split("Candidate record")[0];
        const recordText = item.split("Candidate record")[1];
        const compatible = claimText.includes(first.indication) === recordText.includes(first.indication);
        return { answer: compatible ? "match" : "other_indication", probabilities: { match: compatible ? .9 : .01 } };
      });
    },
  };
  const found = await lookUp({ text: "Synthetic roundup NCT00000001 NCT00000002", model, index,
    registry: { ...quiet, fetch: async id => { fetched.push(id); return id === a.protocolSection.identificationModule.nctId ? a : b; } } });
  assert.equal(reads, 1);
  assert.equal(scoringCalls, 1, "all claim-record pairs use the existing batch scorer once");
  assert.deepEqual(fetched, ["NCT00000001", "NCT00000002"]);
  assert.equal(found.treatment, null, "no first claim masquerades as the whole page");
  assert.deepEqual(found.claims.map(one => one.treatment), [first.intervention, second.intervention]);
  assert.deepEqual(found.claims.map(one => one.tracked.map(card => card.slug)), [["card-0"], ["card-1"]]);
  assert.deepEqual(found.claims.map(one => one.candidates.filter(c => c.answer === "match").map(c => c.id)), [["NCT00000001"], ["NCT00000002"]]);
  assert.ok(found.claims.every(one => one.check_state === "complete"));
  assert.deepEqual(describeAnswer(found).claims.map(one => one.subject.treatment), [first.intervention, second.intervention]);
});

test("a roundup shares sixty scored pairs and twelve discovery queries; omitted work is explicit", async () => {
  const queries = [], scored = [];
  const many = Array.from({ length: 4 }, (_, at) => claim(`EX-${at + 10}`, `condition-${at}`, {
    known_names: Array.from({ length: 5 }, (_, n) => `alias-${at}-${n}`),
  }));
  const found = await lookUp({ text: "Synthetic roundup", index, model: {
    read: async () => ({ ...many[0], additional_claims: many.slice(1) }),
    score: async (_intro, items) => { scored.push(...items); return items.map(yes); },
  }, registry: { ...quiet, search: async (name, condition) => {
    queries.push([name, condition]);
    return Array.from({ length: 70 }, (_, at) => study(`NCT${String(at).padStart(8, "0")}`, name, condition));
  } } });
  assert.equal(queries.length, 12);
  assert.deepEqual(queries.slice(0, 4).map(([name]) => name), many.map(one => one.intervention));
  assert.equal(scored.length, 60);
  assert.deepEqual(found.claims.map(one => one.candidates.length), [15, 15, 15, 15]);
  assert.ok(found.claims.every(one => one.check_state === "partial" && one.check_reason === "work_limit"));
  assert.ok(describeAnswer(found).claims.every(one => one.unchecked));
  const store = memory();
  await storeResult(store, "https://example.org/roundup", found, true);
  assert.equal(store.values.size, 0, "partial work is never cached as a completed page");
});

test("the same study name in different claim conditions has independent discovery", async () => {
  const asked = [];
  const found = await lookUp({ text: "Synthetic roundup", index, model: {
    read: async () => ({ ...first, trial_name: "EXAMPLE", additional_claims: [{ ...second, trial_name: "EXAMPLE" }] }),
    score: async (_intro, items) => items.map(yes),
  }, registry: { ...quiet, named: async (name, { condition }) => {
    asked.push([name, condition]);
    return [condition === first.indication ? a : b];
  } } });
  assert.deepEqual(asked, [["EXAMPLE", first.indication], ["EXAMPLE", second.indication]]);
  assert.deepEqual(found.claims.map(one => one.candidates.map(c => c.id)), [["NCT00000001"], ["NCT00000002"]]);
});

test("reused multi-claim answers reassociate every card and persist no nested gist", async () => {
  const found = await lookUp({ text: "Synthetic roundup", index, registry: quiet,
    model: { read: async () => reading, score: async () => [] } });
  const store = memory();
  await storeResult(store, "https://example.org/roundup", found, true, 1000);
  const saved = await previousResult(store, "https://example.org/roundup", 2000);
  assert.equal(saved.claims.length, 2);
  assert.ok(saved.claims.every(one => !("gist" in one)));
  const moved = withCurrentClaims(saved, { claims: { "card-1": index.claims["card-1"] } });
  assert.deepEqual(moved.claims.map(one => one.tracked.map(card => card.slug)), [[], ["card-1"]]);
});

test("a vague reference does not become an invented extra treatment", async () => {
  const found = await lookUp({ text: "Synthetic report and an unnamed new drug", index, registry: quiet,
    model: { read: async () => ({ ...first, additional_claims: [{ about_a_treatment: false, intervention: null, indication: null }] }), score: async () => [] } });
  assert.equal(found.treatment, first.intervention);
  assert.equal(found.claims, undefined);
});

test("legacy clients refuse multi-claim answers while opted-in clients receive all claims", async () => {
  const settings = { OPENAI_API_KEY: "test", LLM_MODEL: "test", CONTACT_EMAIL: "test@example.org",
    LOOKUP_PER_READER: { limit: async () => ({ success: true }) }, LOOKUP_IN_ALL: { limit: async () => ({ success: true }) },
    ASSETS: { fetch: async () => Response.json(index) } };
  const tools = { registry: quiet, model: { read: async () => reading, score: async () => [] } };
  for (const claimResults of [false, true]) {
    const response = await handle(new Request("https://example.org/api/lookup", { method: "POST",
      body: JSON.stringify({ text: "Synthetic roundup", claimResults }) }), settings, tools);
    const body = await response.json();
    assert.equal(response.status, claimResults ? 200 : 409);
    if (claimResults) assert.equal(body.claims.length, 2);
    else assert.deepEqual(body, { error: "multiple_claims" });
  }
});

test("an ended roundup returns identified unchecked claims and starts no late paid scoring", async () => {
  let resolveSearch, scores = 0, clock = 0;
  const pending = new Promise(resolve => { resolveSearch = resolve; });
  const found = await lookUp({ text: "Synthetic roundup", index, now: () => clock,
    model: { read: async () => { clock = 44_990; return reading; }, score: async () => { scores++; return []; } },
    registry: { ...quiet, search: () => pending } });
  assert.ok(found.claims.every(one => one.check_state === "unchecked" && one.check_reason === "timeout"));
  assert.ok(describeAnswer(found).claims.every(one => !one.none && /ran out of time/.test(one.unchecked)));
  resolveSearch([a]);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(scores, 0);
  assert.equal(completed(found), false);
});

test("browser reuse keeps the group and checked date but never nested gists or partial answers", async () => {
  const found = await lookUp({ text: "Synthetic roundup", index, registry: quiet,
    model: { read: async () => reading, score: async () => [] } });
  const now = Date.now();
  const entries = remember([], "page", "fingerprint", found, now);
  assert.equal(entries.length, 1);
  assert.ok(entries[0].found.claims.every(one => !("gist" in one)));
  const saved = reusable(entries, "page", "fingerprint", now + 1, { claims: {} });
  assert.equal(saved.at, now);
  assert.ok(saved.found.claims.every(one => one.tracked.length === 0));
  found.claims[1].check_state = "partial";
  assert.deepEqual(remember([], "page", "fingerprint", found, now), []);
});

test("time already spent before discovery leaves claims unchecked without starting more work", async () => {
  let clock = 0, searches = 0, scores = 0;
  const found = await lookUp({ text: "Synthetic roundup", index, now: () => clock, timeBudgetMs: 25,
    model: { read: async () => { clock = 30; return reading; }, score: async () => { scores++; return []; } },
    registry: { ...quiet, search: async () => { searches++; return []; } } });
  assert.ok(found.claims.every(one => one.check_state === "unchecked" && one.check_reason === "timeout"));
  assert.equal(searches, 0);
  assert.equal(scores, 0);
});

test("a failed linked paper makes every affected group incomplete rather than a negative finding", async () => {
  const found = await lookUp({ text: "Synthetic roundup", index, registry: quiet,
    model: { read: async () => reading, score: async () => [] }, page: { dois: ["10.1234/synthetic"] },
    papers: { trialNumbers: async () => { throw new Error("Synthetic paper source failure"); } } });
  assert.ok(found.claims.every(one => one.check_state === "unchecked" && one.check_reason === "source_unavailable"));
  assert.ok(describeAnswer(found).claims.every(one => one.none === null));
  assert.equal(completed(found), false);
});
