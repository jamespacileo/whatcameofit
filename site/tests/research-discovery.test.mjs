// On-demand research discovery and citation lookup, with fakes for OpenAlex and the
// cache. No network. All text and records are synthetic.
import assert from "node:assert/strict";
import { test } from "node:test";

import { lookUp } from "../worker/lookup.mjs";
import { makeResearch } from "../worker/research.mjs";
import { previousResult, storeResult } from "../worker/results.mjs";

const BUDGET = {
  daily_budget_usd: 1, daily_remaining_usd: 0.9, prepaid_balance_usd: 0, prepaid_remaining_usd: 0,
  endpoint_costs_usd: { singleton: 0, search: 0.001 },
};
const work = (n, extra = {}) => ({ id: `https://openalex.org/W${n}`, title: `Synthetic work ${n}`, doi: `https://doi.org/10.5555/w${n}`, publication_year: 2024, type: "article", ...extra });
const BASE = { intervention: "EX-1", indication: "example condition" };

/** A fake OpenAlex. `works(url)` answers each search; `single(url)` each identifier lookup. */
function setup({ works = () => Response.json({ results: [] }), single = () => new Response("", { status: 404 }), budget = BUDGET, ...options } = {}) {
  const calls = [], entries = new Map();
  const cache = { get: async (k) => JSON.parse(entries.get(k) ?? "null"), put: async (k, v) => { entries.set(k, v); } };
  const fetch = async (address, init) => {
    const url = new URL(address); calls.push({ url, init });
    if (url.hostname === "api.ror.org") return Response.json({ items: [] });
    if (url.pathname === "/rate-limit") return Response.json({ rate_limit: budget });
    if (url.pathname === "/works") return works(url);
    return single(url);
  };
  const research = makeResearch({ fetch, cache, apiKey: "key", contact: "operator@example.org", ...options });
  const searches = () => calls.filter((c) => c.url.pathname === "/works").map((c) => c.url);
  const singles = () => calls.filter((c) => c.url.pathname.startsWith("/works/")).map((c) => c.url);
  return { calls, entries, research, searches, singles };
}

test("paper queries are searched as they are, without researchers or the condition appended", async () => {
  const s = setup();
  const result = await s.research.search({ ...BASE, paperQueries: ["cell signalling scaffold", "hydrogel culture method"] });
  assert.deepEqual(s.searches().map((u) => u.searchParams.get("search")), ["cell signalling scaffold", "hydrogel culture method"]);
  assert(s.searches().every((u) => !u.searchParams.has("filter")));
  assert.equal(result.availability.openalex, "ok");
});

test("researcher-scoped searches come first, then the unscoped fallbacks, at most four", async () => {
  const s = setup({ works: (u) => Response.json({ results: u.searchParams.get("filter")?.includes("Ada Lovel") ? [work(1)] : [work(2)] }) });
  const result = await s.research.search({ ...BASE, paperQueries: ["first topic words", "second topic words", "third topic words"],
    researchers: ["Ada Lovel", "Grace Hopperton", "Third Person"], publishedBefore: "2025-04-14T09:00:00" });
  const sent = s.searches().map((u) => [u.searchParams.get("search"), u.searchParams.get("filter")]);
  assert.deepEqual(sent, [
    ["first topic words", 'raw_author_name.search:"Ada Lovel",to_publication_date:2025-04-14'],
    ["first topic words", 'raw_author_name.search:"Grace Hopperton",to_publication_date:2025-04-14'],
    ["first topic words", "to_publication_date:2025-04-14"],
    ["second topic words", "to_publication_date:2025-04-14"],
  ]);
  assert.deepEqual(result.papers.map((p) => p.id), ["https://openalex.org/W1", "https://openalex.org/W2"]);
});

test("without paper queries the legacy treatment-and-condition searches are unchanged", async () => {
  const s = setup();
  await s.research.search({ ...BASE, searchPhrases: ["a phrase", "another phrase"], researchers: ["Ada Lovel"] });
  assert.deepEqual(s.searches().map((u) => u.searchParams.get("search")), ["EX-1 example condition", "a phrase example condition"]);
  assert(s.searches().every((u) => !u.searchParams.has("filter")));
  const none = setup();
  const result = await none.research.search({ intervention: "EX-1", researchers: ["Ada Lovel"] });
  assert.equal(none.calls.length, 0); assert.equal(result.availability.openalex, "not_needed");
});

test("missing or invalid new fields are ignored safely", async () => {
  for (const extra of [
    { paperQueries: "not a list", researchers: "Ada Lovel", publishedBefore: 20250414 },
    { paperQueries: null, researchers: null, publishedBefore: null, dois: null, pubmedIds: null },
    { paperQueries: [1, {}, "single", "cats AND dogs", 'quoted "words"', "a|b c", "(group) words", "x".repeat(200) + " y"],
      researchers: ["Dr Ada Lovel", "Madonna", 'Ada" OR "x', "Ada|Lovel", "Lovel, Ada", "Ada: Lovel", "A. B."],
      publishedBefore: "2025-02-30" },
    { publishedBefore: "14 April 2025" }, { publishedBefore: "2025-04-14 junk" }, { publishedBefore: "2025-04-14T99" },
  ]) {
    const s = setup();
    const result = await s.research.search({ ...BASE, ...extra });
    assert.deepEqual(s.searches().map((u) => [u.searchParams.get("search"), u.searchParams.get("filter")]), [["EX-1 example condition", null]]);
    assert.equal(s.singles().length, 0); assert.equal(result.availability.openalex, "ok");
  }
});

test("names that could change the filter never reach it", async () => {
  const s = setup();
  await s.research.search({ ...BASE, paperQueries: ["topic words here"],
    researchers: ['Ada Lovel",type:dataset', "Ada Lovel|Other Name", "Ada\nLovel,x", "Ada Lovel\"", "Grace O'Hara"] });
  const filters = s.searches().map((u) => u.searchParams.get("filter"));
  assert.deepEqual(filters, ["raw_author_name.search:\"Grace O'Hara\"", null]);
});

test("author and date constraints have their own cache entries", async () => {
  const s = setup({ works: () => Response.json({ results: [work(1)] }) });
  const ask = (extra) => s.research.search({ ...BASE, paperQueries: ["topic words here"], ...extra });
  await ask({}); await ask({ researchers: ["Ada Lovel"] }); await ask({ researchers: ["Grace Hopperton"] });
  await ask({ researchers: ["Ada Lovel"], publishedBefore: "2024-01-01" }); await ask({ publishedBefore: "2024-01-01T00:00:00Z" });
  const first = s.searches().length;
  // Unscoped, each author, the first author before the date, and the dated fallback; a
  // timestamp on the same day reuses the dated entry.
  assert.equal(first, 1 + 1 + 1 + 2 + 0);
  await ask({}); await ask({ researchers: ["ada lovel"] }); await ask({ researchers: ["Ada Lovel"], publishedBefore: "2024-01-01" });
  assert.equal(s.searches().length, first);
  assert.equal(new Set([...s.entries.keys()].filter((k) => k.includes(":openalex:"))).size, 5);
});

test("duplicate queries are searched once and results are deduplicated by id and link, at most twenty", async () => {
  let page = 0;
  const s = setup({ works: () => { const start = page++ * 10; return Response.json({ results: Array.from({ length: 10 }, (_, n) => work(start + n)) }); } });
  const result = await s.research.search({ ...BASE, paperQueries: ["Topic Words Here", "topic words here", "other topic words", "more topic words"],
    researchers: ["Ada Lovel", "ada lovel", "Grace Hopperton"] });
  // The first two pages fill the cap; the fallbacks are still asked.
  assert.equal(s.searches().length, 4);
  assert.equal(result.papers.length, 20);
  assert.deepEqual(result.papers.slice(0, 2).map((p) => p.id), ["https://openalex.org/W0", "https://openalex.org/W1"]);

  const dup = setup({ works: (u) => Response.json({ results: u.searchParams.has("filter")
    ? [work(1), work(2, { doi: "https://doi.org/10.5555/shared" })]
    : [work(1, { title: "Later copy" }), work(3, { doi: "https://doi.org/10.5555/shared" }), work(4)] }) });
  const deduped = await dup.research.search({ ...BASE, paperQueries: ["topic words here"], researchers: ["Ada Lovel"] });
  assert.deepEqual(deduped.papers.map((p) => p.id), ["https://openalex.org/W1", "https://openalex.org/W2", "https://openalex.org/W4"]);
  assert.equal(deduped.papers[0].title, "Synthetic work 1");
});

test("cited DOIs and PubMed numbers are looked up first, free, and validated", async () => {
  const s = setup({ single: (u) => Response.json(work(u.pathname.includes("pmid") ? 9 : 8)) });
  const result = await s.research.search({ dois: ["10.5555/ABC.1", "https://doi.org/10.5555/abc.1", '10.5555/x"y', "10.5555/a?b", "10.1/short", "not a doi"],
    pubmedIds: ["123456", "0123", "12a", 123456, "1234567890"] });
  assert.deepEqual(s.singles().map((u) => u.pathname), ["/works/doi:10.5555%2Fabc.1", "/works/pmid:123456"]);
  assert(s.singles().every((u) => u.searchParams.get("select") === "id,title,doi,publication_year,type,primary_location"));
  assert(!s.calls.some((c) => c.url.pathname === "/rate-limit"));
  assert.deepEqual(result.papers.map((p) => p.id), ["https://openalex.org/W8", "https://openalex.org/W9"]);
  const many = setup();
  await many.research.search({ dois: ["10.5555/a", "10.5555/b"], pubmedIds: ["1", "2", "3"] });
  assert.equal(many.singles().length, 3);
  const unkeyed = setup({ apiKey: "" });
  await unkeyed.research.search({ dois: ["10.5555/a"] });
  assert.equal(unkeyed.calls.length, 0);
  const overlong = setup();
  await overlong.research.search({dois:["10.5555/" + "x".repeat(300)]});
  assert.equal(overlong.singles().length, 0, "Never truncate an identifier into a different paper");
});

test("a cited work survives a failing charged search and stays first", async () => {
  for (const failing of [{ works: () => new Response("", { status: 500 }) }, { budget: { ...BUDGET, daily_remaining_usd: 0 } },
    { works: () => new Response("", { status: 429, headers: { "Retry-After": "120" } }) }]) {
    const s = setup({ single: () => Response.json(work(7)), works: () => Response.json({ results: [work(7), work(1)] }), ...failing });
    const result = await s.research.search({ ...BASE, pubmedIds: ["123456"], paperQueries: ["topic words here"] });
    assert.deepEqual(result.papers.map((p) => p.id), ["https://openalex.org/W7"]);
    assert.notEqual(result.availability.openalex, "ok");
  }
  const ok = setup({ single: () => Response.json(work(7)), works: () => Response.json({ results: [work(1), work(7)] }) });
  const both = await ok.research.search({ ...BASE, pubmedIds: ["123456"] });
  assert.deepEqual(both.papers.map((p) => p.id), ["https://openalex.org/W7", "https://openalex.org/W1"]);
});

test("a missing cited work is cached as none; an outage or malformed record is not, and discovery goes on", async () => {
  for (const [single, cachedAsNone] of [
    [() => new Response("", { status: 404 }), true],
    [() => new Response("upstream", { status: 503 }), false],
    [() => Response.json({ id: "javascript:alert(1)", title: "x" }), false],
    [() => new Response("not json", { status: 200 }), false],
  ]) {
    const s = setup({ single, works: () => Response.json({ results: [work(1)] }) });
    const result = await s.research.search({ ...BASE, dois: ["10.5555/missing"] });
    assert.deepEqual(result.papers.map((p) => p.id), ["https://openalex.org/W1"]);
    assert.equal(result.availability.openalex, cachedAsNone ? "ok" : "unavailable");
    await s.research.search({ ...BASE, dois: ["10.5555/missing"] });
    assert.equal(s.singles().length, cachedAsNone ? 1 : 2);
    assert.equal(s.searches().length, 1);
  }
});

test("a rate-limited cited lookup stops discovery and pauses the source", async () => {
  const s = setup({ single: () => new Response("", { status: 429, headers: { "Retry-After": "300" } }) });
  const result = await s.research.search({ ...BASE, dois: ["10.5555/a", "10.5555/b"], paperQueries: ["topic words here"] });
  assert.equal(result.availability.openalex, "limit");
  assert.equal(s.singles().length, 1); assert.equal(s.searches().length, 0);
  await s.research.search({ dois: ["10.5555/c"] });
  assert.equal(s.singles().length, 1);
});

test("a failed citation cannot become a shared cached miss after successful keyword fallback", async () => {
  let available = false;
  const s = setup({single:() => available ? Response.json(work(7)) : new Response("", {status:503})});
  const values = new Map();
  const shared = {get:async key => JSON.parse(values.get(key) ?? "null"), put:async (key, value) => values.set(key, value)};
  const address = "https://example.org/research-report";
  const lookup = () => lookUp({text:"A synthetic report describes EX-1 for an example condition.",
    page:{dois:["10.5555/w7"],pubmedIds:[],registryNumbers:[]},research:s.research,index:{claims:{}},
    model:{read:async () => ({about_a_treatment:true,...BASE})},registry:{search:async () => []},
  });
  const first = await lookup();
  assert.equal(first.research.availability.openalex, "unavailable");
  await storeResult(shared, address, first, true, 1000);
  assert.equal(await previousResult(shared, address, 1001), null);
  available = true;
  const recovered = await lookup();
  assert.equal(recovered.research.papers[0]?.id, "https://openalex.org/W7");
  assert.equal(s.singles().length, 2);
  assert.equal(s.searches().length, 1, "Successful keyword metadata remains cached");
  await storeResult(shared, address, recovered, true, 1002);
  assert.equal((await previousResult(shared, address, 1003)).research.papers[0].id, "https://openalex.org/W7");
  // Older whole-answer entries that already report an outage must not hide recovery.
  const [key, value] = [...values][0];
  const old = JSON.parse(value); old.found.research.availability.openalex = "unavailable";
  values.set(key, JSON.stringify(old));
  assert.equal(await previousResult(shared, address, 1004), null);
});

test("cited lookups send the key only to OpenAlex and refuse redirects", async () => {
  const s = setup({ single: () => new Response("", { status: 302, headers: { Location: "https://elsewhere.example/" } }) });
  const result = await s.research.search({ dois: ["10.5555/a"] });
  assert.deepEqual(result.papers, []);
  assert.equal(result.availability.openalex, "unavailable");
  assert(s.calls.every((c) => c.init.redirect === "manual" && c.url.hostname.endsWith("openalex.org")));
  assert(![...s.entries.values()].some((v) => v.includes("key")));
});

test("lookup forwards extracted research fields and page metadata, never the text", async () => {
  const given = [];
  const research = { search: async (input) => (given.push(input), { papers: [], organisations: [], availability: {} }) };
  const reading = { about_a_treatment: true, gist: "g", intervention: "EX-1", indication: "example condition",
    paper_queries: ["topic words here", 7], researchers: ["Ada Lovel"] };
  const page = { published: "2025-04-14T09:00:00", dois: ["10.5555/a"], pubmedIds: ["123456"], registryNumbers: [] };
  await lookUp({ text: "SECRET ARTICLE TEXT", page, research, index: { claims: {} }, model: { read: async () => reading }, registry: { search: async () => [] } });
  assert.deepEqual(given, [{ intervention: "EX-1", indication: "example condition", searchPhrases: [], organisations: [],
    paperQueries: ["topic words here"], researchers: ["Ada Lovel"], publishedBefore: "2025-04-14T09:00:00", dois: ["10.5555/a"], pubmedIds: ["123456"] }]);
  assert(!JSON.stringify(given).includes("SECRET"));

  // Unrelated text: no extraction, no request of any kind.
  const s = setup();
  await lookUp({ text: "A post about the weather.", page, research: s.research, index: { claims: {} },
    model: { read: async () => ({ about_a_treatment: false, intervention: null, paper_queries: [], researchers: [] }) }, registry: { search: async () => [] } });
  assert.equal(s.calls.length, 0);
});
