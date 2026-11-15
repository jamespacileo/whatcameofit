// Faster lookups that stay correct: linked papers share one bounded allowance, the
// registry is asked by name while papers are pending, a completed clinical answer can be
// sent before enrichment, and public source answers are reused without keeping content.
// All text is synthetic; no network.
import assert from "node:assert/strict";
import { test } from "node:test";
import { handle } from "../worker/index.mjs";
import { lookUp } from "../worker/lookup.mjs";
import { makePapers } from "../worker/papers.mjs";
import { makeRegistry } from "../worker/registry.mjs";
import { makeShared, makeSourceCache } from "../worker/public-cache.mjs";
import { previousResult, storeResult } from "../worker/results.mjs";

const never = () => new Promise(() => {});
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function within(promise, ms = 500) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("still waiting")), ms); })]);
  } finally { clearTimeout(timer); }
}
const study = (id, title = `EX-1 study ${id}`) => ({
  protocolSection: {
    identificationModule: { nctId: id, briefTitle: title },
    conditionsModule: { conditions: ["tinnitus"] },
    armsInterventionsModule: { interventions: [{ name: "EX-1" }] },
    statusModule: { overallStatus: "COMPLETED" },
  },
});
const reading = { about_a_treatment: true, intervention: "EX-1", indication: "tinnitus", gist: "EX-1 for tinnitus", other_names: [], known_names: [], search_phrases: [] };
const scoreAll = async (_intro, records) => records.map(() => ({ answer: "match", probabilities: { match: 0.9 } }));
const model = (read = reading) => ({ read: async () => read, score: scoreAll });
const quiet = { fetch: async () => null, named: async () => [], search: async () => [] };
const index = { claims: {} };
const memory = () => {
  const values = new Map();
  const puts = [];
  return { values, puts, get: async (key) => (values.has(key) ? JSON.parse(values.get(key)) : null), put: async (key, value, options) => { puts.push({ key, options }); values.set(key, value); } };
};

// --- linked papers ----------------------------------------------------------------------

test("linked papers share one allowance: at most three, started apart, every unanswered one counted", async () => {
  const starts = [];
  const signals = [];
  const papers = { trialNumbers: (paper, { signal }) => { starts.push({ paper, at: Date.now() }); signals.push(signal); return never(); } };
  const page = { dois: ["10.1/a", "10.1/b", "10.1/c", "10.1/d"], pubmedIds: ["123456"] };
  const began = Date.now();
  const found = await within(lookUp({ text: "EX-1 for tinnitus", model: model(), registry: quiet, index, page, papers,
    paperAllowanceMs: 90, paperSpacingMs: 20 }), 400);
  assert.ok(Date.now() - began < 300, "one allowance for all of them, not one each");
  assert.deepEqual(starts.map((one) => one.paper), [{ doi: "10.1/a" }, { doi: "10.1/b" }, { doi: "10.1/c" }]);
  for (let at = 1; at < starts.length; at += 1) assert.ok(starts[at].at - starts[at - 1].at >= 18, "starts are spaced");
  assert.equal(found.papers_unchecked, 3);
  assert.ok(signals.every((signal) => signal.aborted), "every request still waiting is ended");
});

test("a later paper starts while the first stalls, and its trial is included", async () => {
  const registry = { ...quiet, fetch: async (number) => study(number) };
  const papers = { trialNumbers: ({ doi }) => (doi === "10.1/slow" ? never() : Promise.resolve(["NCT07654321"])) };
  const found = await within(lookUp({ text: "EX-1 for tinnitus", model: model(), registry, index,
    page: { dois: ["10.1/slow", "10.1/quick"] }, papers, paperAllowanceMs: 80, paperSpacingMs: 10 }));
  assert.deepEqual(found.paper_numbers, ["NCT07654321"]);
  assert.deepEqual(found.candidates.map((one) => [one.id, one.agrees]), [["NCT07654321", ["paper"]]]);
  assert.equal(found.papers_unchecked, 1);
});

test("a paper the allowance ends before it is asked is never asked, and is counted", async () => {
  const asked = [];
  const papers = { trialNumbers: (paper) => { asked.push(paper); return never(); } };
  const found = await within(lookUp({ text: "EX-1 for tinnitus", model: model(), registry: quiet, index,
    page: { dois: ["10.1/a", "10.1/b", "10.1/c"] }, papers, paperAllowanceMs: 25, paperSpacingMs: 20 }));
  await pause(30);
  assert.deepEqual(asked, [{ doi: "10.1/a" }, { doi: "10.1/b" }]);
  assert.equal(found.papers_unchecked, 3);
});

test("a registry failure ends waiting papers and asks the registry nothing further", async () => {
  const asked = [];
  let paperSignal;
  const papers = { trialNumbers: (_paper, { signal }) => { paperSignal = signal; return never(); } };
  const registry = {
    fetch: async () => null,
    named: async () => [],
    search: async (term) => { asked.push(term); throw new Error("registry 500"); },
  };
  await assert.rejects(within(lookUp({ text: "EX-1 for tinnitus", model: model({ ...reading, search_phrases: ["second phrase"] }), registry, index,
    page: { dois: ["10.1/a", "10.1/b"] }, papers, paperSpacingMs: 50 })), /registry 500/);
  await pause(70);
  assert.deepEqual(asked, ["EX-1"]);
  assert.equal(paperSignal.aborted, true);
});

// --- one registry queue ------------------------------------------------------------------

test("registry requests run one at a time, a paper's record ahead of waiting searches, candidates in the same order", async () => {
  let running = 0;
  let most = 0;
  const order = [];
  const paper = deferred();
  const slow = async (label, value) => {
    running += 1; most = Math.max(most, running); order.push(label);
    await pause(10);
    running -= 1;
    return value;
  };
  const registry = {
    fetch: (number) => slow(`fetch ${number}`, study(number)),
    named: (name) => slow(`named ${name}`, [study("NCT00000003")]),
    search: (term) => slow(`search ${term}`, [study(term === "EX-1" ? "NCT00000004" : "NCT00000005"), study("NCT00000002")]),
  };
  const looking = lookUp({ text: "EX-1 for tinnitus. NCT00000001", model: model({ ...reading, trial_name: "EXAMPLE-1", search_phrases: ["EX one"] }),
    registry, index, page: { dois: ["10.1/a"] }, papers: { trialNumbers: () => paper.promise } });
  await pause(15);
  paper.resolve(["NCT00000002"]);
  const found = await within(looking);
  assert.equal(most, 1, "one request at a time");
  assert.deepEqual(order.slice(0, 2), ["fetch NCT00000001", "named EXAMPLE-1"]);
  assert.ok(order.indexOf("fetch NCT00000002") < order.indexOf("search EX one"), "the paper's record is asked before a waiting search");
  assert.deepEqual(found.candidates.map((one) => one.id), ["NCT00000001", "NCT00000002", "NCT00000003", "NCT00000004", "NCT00000005"]);
  assert.deepEqual(found.candidates[0].agrees.slice(0, 1), ["stated"]);
  assert.deepEqual(found.candidates[1].agrees.slice(0, 1), ["paper"]);
});

// --- the completed core -------------------------------------------------------------------

test("the core is given after every search and score, before enrichment, and equals the answer without it", async () => {
  const research = deferred();
  const events = [];
  let scored = false;
  const looking = lookUp({ text: "EX-1 for tinnitus", index,
    model: { read: async () => reading, score: async (...args) => { const scores = await scoreAll(...args); scored = true; events.push("scored"); return scores; } },
    registry: { ...quiet, search: async () => [study("NCT00000009")] },
    research: { search: () => { events.push("research asked"); return research.promise; } },
    onCore: (core) => { events.push("core"); assert.ok(scored); assert.equal(core.candidates.length, 1); assert.equal(core.research, undefined); throw new Error("a listener cannot break the lookup"); },
    timings: {} });
  await pause(20);
  assert.deepEqual(events, ["research asked", "scored", "core"], "research starts once the treatment is read");
  research.resolve({ papers: [], organisations: [], availability: {} });
  const found = await within(looking);
  const { research: enrichment, ...clinical } = found;
  assert.deepEqual(enrichment, { papers: [], organisations: [], availability: {} });
  assert.equal(clinical.candidates[0].id, "NCT00000009");
});

test("stage durations are numbers only", async () => {
  const timings = {};
  await lookUp({ text: "EX-1 for tinnitus", model: model(), registry: quiet, index, timings, research: { search: async () => ({ papers: [], organisations: [] }) } });
  for (const stage of ["read_ms", "papers_ms", "registry_ms", "score_ms", "core_ms", "research_ms", "total_ms"]) {
    assert.equal(typeof timings[stage], "number", stage);
  }
});

test("stage durations exclude earlier work and idle registry time", async () => {
  let clock = 0;
  const read = deferred();
  const research = deferred();
  const core = deferred();
  const timings = {};
  const looking = lookUp({ text: "EX-1 for tinnitus", index, timings, now: () => clock,
    model: { read: () => read.promise, score: async (...args) => { clock += 5; return scoreAll(...args); } },
    registry: { ...quiet, search: async () => { clock += 10; return [study("NCT00000009")]; } },
    research: { search: () => research.promise }, onCore: core.resolve });
  // Let the empty paper stage finish while reading is still pending.
  await new Promise((resolve) => setImmediate(resolve));
  clock = 80;
  read.resolve(reading);
  await core.promise;
  assert.deepEqual(timings, { registry_ms: 10, papers_ms: 0, read_ms: 80, score_ms: 5, core_ms: 95 });
  clock = 120;
  research.resolve({ papers: [], organisations: [] });
  await looking;
  assert.equal(timings.research_ms, 40);
  assert.equal(timings.total_ms, 120);
});

test("paper origin starts remain spaced when cache misses take different times", async () => {
  const starts = [];
  let reads = 0;
  const papers = makePapers({ contact: "test@example.org", requestSpacingMs: 120,
    cache: { get: async () => { if (++reads === 1) await pause(90); return null; }, put: async () => {} },
    fetch: async () => {
      // Fetch setup can cross clock ticks before the request actually starts.
      if (!starts.length) {
        const ready = Date.now() + 10;
        while (Date.now() < ready) { /* synthetic synchronous request setup */ }
      }
      starts.push(Date.now());
      return Response.json({ resultList: { result: [] } });
    } });
  const first = papers.trialNumbers({ doi: "10.1/first" });
  await pause(120);
  await Promise.all([first, papers.trialNumbers({ doi: "10.1/second" })]);
  assert.equal(starts.length, 2);
  assert.ok(starts[1] - starts[0] >= 120, `origin starts only ${starts[1] - starts[0]}ms apart`);
});

test("a paper cancelled while waiting for its origin slot never starts", async () => {
  const starts = [];
  const papers = makePapers({ contact: "test@example.org", requestSpacingMs: 120,
    fetch: async (url) => { starts.push(url); return Response.json({ resultList: { result: [] } }); } });
  await papers.trialNumbers({ doi: "10.1/first" });
  const controller = new AbortController();
  const waiting = papers.trialNumbers({ doi: "10.1/cancelled" }, { signal: controller.signal });
  await pause(20);
  controller.abort();
  await assert.rejects(waiting, { name: "AbortError" });
  await pause(130);
  assert.equal(starts.length, 1);
});

// --- the service ------------------------------------------------------------------------

const env = (store) => ({
  OPENAI_API_KEY: "test-only", LLM_MODEL: "test-only", CONTACT_EMAIL: "test@example.org",
  LOOKUP_PER_READER: { limit: async () => ({ success: true }) },
  LOOKUP_IN_ALL: { limit: async () => ({ success: true }) },
  ASSETS: { fetch: async () => Response.json({ claims: {}, articles: {} }) },
  ...(store ? { LOOKUP_RESULTS: store } : {}),
});
const post = (body) => new Request("https://service.example.org/api/lookup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
async function eventsOf(response) {
  const text = await response.text();
  assert.ok(text.endsWith("\n"), "every event ends its line");
  return text.trim().split("\n").map((line) => JSON.parse(line));
}
const image = { dataUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jBzQAAAAASUVORK5CYII=", width: 1, height: 1 };

test("an ordinary JSON caller gets the whole answer as before, with numeric stage timings only", async () => {
  const tools = { model: model(), registry: quiet, research: { search: async () => ({ papers: [], organisations: [] }) } };
  const response = await handle(post({ text: "A report about EX-1 for tinnitus." }), env(), tools);
  assert.match(response.headers.get("content-type"), /application\/json/);
  const found = await response.json();
  assert.equal(found.treatment, "EX-1");
  assert.deepEqual(found.research, { papers: [], organisations: [] });
  assert.equal(found.timings, undefined, "durations are not part of the answer");
  assert.match(response.headers.get("server-timing"), /^([a-z]+;dur=\d+)(, [a-z]+;dur=\d+)*$/);
});

test("a stream's core and complete events carry the same source boundary, with one reading", async () => {
  let reads = 0;
  const tools = { model: { read: async () => { reads += 1; return reading; }, score: scoreAll }, registry: quiet,
    research: { search: async () => ({ papers: [], organisations: [] }) } };
  const response = await handle(post({ text: "Look at this", image, pageUrl: "https://www.reddit.com/r/test/comments/abc/", stream: true }), env(), tools);
  assert.match(response.headers.get("content-type"), /application\/x-ndjson/);
  const events = await eventsOf(response);
  assert.deepEqual(events.map((event) => event.type), ["core", "complete"]);
  for (const event of events) {
    assert.deepEqual(event.result.source, { kind: "screenshot", host: "www.reddit.com" });
    assert.equal(event.result.post, null);
    assert.ok(Object.values(event.timings).every((value) => Number.isInteger(value)));
  }
  assert.equal(events[0].result.research, undefined);
  assert.deepEqual(events[1].result.research, { papers: [], organisations: [] });
  assert.equal(reads, 1);
});

test("a stream failure before the core is an explicit error event, never an empty answer", async () => {
  const failing = await handle(post({ text: "A report about EX-1.", stream: true }), env(), { model: { read: async () => { throw new Error("PRIVATE provider detail"); } }, registry: quiet });
  const events = await eventsOf(failing);
  assert.deepEqual(events, [{ type: "error", status: 502, error: "failed" }]);
  const budget = await handle(post({ text: "A report about EX-1.", stream: true }), env(), { model: { read: async () => { throw Object.assign(new Error("x"), { code: "budget_exhausted" }); } }, registry: quiet });
  assert.deepEqual(await eventsOf(budget), [{ type: "error", status: 503, error: "budget_exhausted" }]);
});

test("a streamed public answer is stored once complete, and a later stream request gets the cached JSON", async () => {
  const store = memory();
  const tools = { model: model(), registry: quiet, proofTimeoutMs: 1_000,
    fetch: async (url) => new Response(String(url).endsWith("/robots.txt") ? "User-agent: *\nAllow: /" : "<main><p>EX-1 was studied for tinnitus in a synthetic public report.</p></main>") };
  const events = await eventsOf(await handle(post({ text: "PRIVATE ADDITION", pageUrl: "https://news.example.org/report", stream: true }), env(store), tools));
  assert.equal(events.at(-1).type, "complete");
  assert.equal(store.values.size, 1);
  assert.doesNotMatch([...store.values.values()][0], /PRIVATE ADDITION|EX-1 for tinnitus/);
  const again = await handle(post({ text: "PRIVATE ADDITION", pageUrl: "https://news.example.org/report", stream: true }), env(store), tools);
  assert.match(again.headers.get("content-type"), /application\/json/);
  assert.equal((await again.json()).cache.shared, true);
});

test("a completed non-treatment answer of a public page is shared; one missing a paper or failed is not", async () => {
  const store = memory();
  const negative = { about_a_treatment: false, gist: "PRIVATE GIST", treatment: null, condition: null, candidates: [], papers_unchecked: 0, registry_numbers: ["NCT00000001"] };
  await storeResult(store, "https://news.example.org/a", { error: "failed" }, true, 1000);
  await storeResult(store, "https://news.example.org/a", { ...negative, about_a_treatment: true, papers_unchecked: 2 }, true, 1000);
  await storeResult(store, "https://news.example.org/a", { article_tracked: true, candidates: [] }, true, 1000);
  assert.equal(store.values.size, 0);
  await storeResult(store, "https://news.example.org/a", negative, true, 1000);
  assert.doesNotMatch([...store.values.values()][0], /PRIVATE GIST/);
  const found = await previousResult(store, "https://news.example.org/a", 1001);
  assert.deepEqual([found.about_a_treatment, found.candidates, found.papers_unchecked, found.cache.checkedAt], [false, [], 0, 1000]);
  assert.match([...store.values.keys()][0], /^visual-v9:[0-9a-f]{64}$/);
});

test("shared results kept under the earlier rules are not read", async () => {
  for (const version of [1, 2, 3, 4, 5, 6, 7, 8]) {
    const old = { get: async () => ({ version, publicVerified: true, at: 1000, found: { about_a_treatment: true, treatment: "EX-1", candidates: [] } }) };
    assert.equal(await previousResult(old, "https://news.example.org/a", 1001), null);
  }
});

test("a stalled shared-result store is a miss within its bound, and a stalled write does not hold the answer", async () => {
  const stalled = { get: never, put: never };
  const started = Date.now();
  assert.equal(await within(previousResult(stalled, "https://news.example.org/a"), 1_000), null);
  await within(storeResult(stalled, "https://news.example.org/a", { about_a_treatment: true, candidates: [] }, true), 1_000);
  assert.ok(Date.now() - started < 1_500);
});

// --- public source reuse --------------------------------------------------------------------

const europe = (abstractText, calls) => async (_url, { signal }) => {
  calls.push(signal);
  return Response.json({ resultList: { result: abstractText === null ? [] : [{ abstractText, authorString: "PRIVATE AUTHOR" }] } });
};

test("a paper mapping is kept as trial numbers only, under a digest, for at most a day", async () => {
  const store = memory();
  const calls = [];
  const papers = makePapers({ fetch: europe("Abstract text that must not be kept. NCT07654321.", calls), contact: "t@example.org", cache: store });
  assert.deepEqual(await papers.trialNumbers({ doi: "10.1/kept" }), ["NCT07654321"]);
  const [[key, value]] = [...store.values];
  assert.match(key, /^source-v1:papers:[0-9a-f]{64}$/);
  assert.doesNotMatch(value, /Abstract|PRIVATE|10\.1\/kept/);
  assert.deepEqual(JSON.parse(value).value, ["NCT07654321"]);
  assert.ok(store.puts[0].options.expirationTtl <= 86_400);
  const later = makePapers({ fetch: europe("NCT00000000", calls), contact: "t@example.org", cache: store, now: undefined });
  assert.deepEqual(await later.trialNumbers({ doi: "10.1/kept" }), ["NCT07654321"]);
  assert.equal(calls.length, 1);
});

test("an expired or foreign cache entry is not reused", async () => {
  let now = 1_000_000;
  const store = memory();
  const cache = makeSourceCache(store, { kind: "papers", now: () => now });
  const key = await cache.key("q");
  await cache.put(key, ["NCT00000001"], 999_999);
  assert.equal(JSON.parse(store.values.get(key)).seconds, 86_400, "never kept longer than a day");
  now += 86_400_000;
  assert.equal(await cache.get(key), undefined);
  store.values.set(key, JSON.stringify({ version: 0, at: now, seconds: 60, value: ["NCT00000001"] }));
  assert.equal(await cache.get(key), undefined);
});

test("a failed or timed-out paper is not cached as having no trial, and is asked again", async () => {
  const store = memory();
  let calls = 0;
  const failing = makePapers({ contact: "t@example.org", cache: store, timeoutMs: 20,
    fetch: async (_url, { signal }) => { calls += 1; if (calls === 1) return new Response("", { status: 500 }); return new Promise((_, reject) => signal.addEventListener("abort", () => reject(signal.reason))); } });
  await assert.rejects(failing.trialNumbers({ doi: "10.1/x" }), /papers 500/);
  await assert.rejects(failing.trialNumbers({ doi: "10.1/x" }), { code: "timeout" });
  assert.equal(store.values.size, 0);
  const working = makePapers({ contact: "t@example.org", cache: store, fetch: async () => Response.json({ resultList: { result: [{ abstractText: "NCT07654321" }] } }) });
  assert.deepEqual(await working.trialNumbers({ doi: "10.1/x" }), ["NCT07654321"]);
});

test("a stalled source cache is passed over within its bound and the source is asked", async () => {
  const stalled = { get: never, put: never };
  const started = Date.now();
  const papers = makePapers({ contact: "t@example.org", cache: stalled, cacheTimeoutMs: 20, fetch: async () => Response.json({ resultList: { result: [{ abstractText: "NCT07654321" }] } }) });
  assert.deepEqual(await within(papers.trialNumbers({ doi: "10.1/x" }), 300), ["NCT07654321"]);
  const throwing = { get: async () => { throw new Error("cache down"); }, put: async () => { throw new Error("cache down"); } };
  const registry = makeRegistry({ contact: "t@example.org", cache: throwing, fetch: async () => Response.json({ studies: [study("NCT00000001")], totalCount: 1 }) });
  assert.equal((await within(registry.search("EX-1", "tinnitus"), 300)).length, 1);
  assert.ok(Date.now() - started < 600);
});

test("public registry answers are reused across lookups; failures and missing records are not kept", async () => {
  const store = memory();
  const asked = [];
  const fetch = async (url) => {
    asked.push(String(url));
    if (String(url).includes("/studies/NCT00000404")) return new Response("", { status: 404 });
    if (String(url).includes("/studies/NCT00000500")) return new Response("", { status: 500 });
    return Response.json({ studies: [study("NCT00000001")], totalCount: 1 });
  };
  const first = makeRegistry({ fetch, contact: "t@example.org", cache: store });
  const second = makeRegistry({ fetch, contact: "t@example.org", cache: store });
  await first.search("EX-1", "tinnitus");
  await second.search("EX-1", "tinnitus");
  assert.equal(asked.length, 1);
  assert.equal(await first.fetch("NCT00000404"), null);
  await assert.rejects(first.fetch("NCT00000500"), /registry 500/);
  assert.equal(store.values.size, 1);
  assert.match([...store.values.keys()][0], /^source-v1:registry:[0-9a-f]{64}$/);
});

test("the same paper asked twice at once is fetched once, and one caller leaving does not fail the other", async () => {
  const response = deferred();
  let calls = 0;
  let signal;
  const papers = makePapers({ contact: "t@example.org", fetch: async (_url, options) => { calls += 1; signal = options.signal; return response.promise; } });
  const leaving = new AbortController();
  const first = papers.trialNumbers({ doi: "10.1/same" }, { signal: leaving.signal });
  const second = papers.trialNumbers({ doi: "10.1/same" });
  await pause(5);
  leaving.abort();
  await assert.rejects(first, { name: "AbortError" });
  assert.equal(signal.aborted, false, "the request goes on for the caller still waiting");
  response.resolve(Response.json({ resultList: { result: [{ abstractText: "NCT07654321" }] } }));
  assert.deepEqual(await second, ["NCT07654321"]);
  assert.equal(calls, 1);
});

test("a shared request ends once every caller has left, and a later caller starts afresh", async () => {
  const shared = makeShared();
  const signals = [];
  const work = (signal) => { signals.push(signal); return never(); };
  const one = new AbortController();
  const two = new AbortController();
  const a = shared("k", work, one.signal);
  const b = shared("k", work, two.signal);
  await pause(1);
  one.abort();
  await assert.rejects(a);
  assert.equal(signals[0].aborted, false);
  two.abort();
  await assert.rejects(b);
  assert.equal(signals[0].aborted, true);
  const c = shared("k", async () => "fresh");
  assert.equal(await c, "fresh");
});
