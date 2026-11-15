import assert from "node:assert/strict";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import vm from "node:vm";
import { test } from "node:test";
import { parseHTML } from "linkedom";
import { readAddress, closestClaims } from "../src/lib/lookup-match.mjs";
import { SUGGEST_SUBJECT, contactLink } from "../src/lib/contact.mjs";
import { LIVE, describeAnswer, refusalMessage, textWouldHelp } from "../src/lib/live-lookup.mjs";

// Exercise the actual home-page submit handler, with only its network boundary
// controlled. No real article text or live provider requests are used.
const source = fs.readFileSync(new URL("../src/components/Lookup.astro", import.meta.url), "utf8")
  .match(/<script>([\s\S]*?)<\/script>/)[1]
  .replace(/^\s*import .*;\s*$/gm, "");
// The search index is the one module loaded at run time; the test hands it in.
const PAGEFIND_IMPORT = "await import(/* @vite-ignore */ indexUrl)";
assert.ok(source.includes(PAGEFIND_IMPORT));
const script = stripTypeScriptTypes(source.replace(PAGEFIND_IMPORT, "await loadSearchIndex(indexUrl)"));
const settle = () => new Promise(resolve => setImmediate(resolve));

const PAGE = '<form id="search"><input id="query"></form><div id="results" data-live="/api/lookup"></div>';
// The home page's list, with one report row, and the places a search answers in.
const HOME = `${PAGE}<section data-days><aside><div class="side-group" data-side-topics></div><div class="side-group" hidden data-search-topics><ul></ul></div></aside>
  <div class="days-main"><div hidden data-search-answer></div><h2 class="days-title">Latest</h2>
  <div data-day-list><ol><li class="day-row report-row" data-day-row data-kind="report"><div class="row-now">On record now</div>
  <div class="row-main"><h4 class="row-title"><a href="/germ" style="view-transition-name: r-germ">“Synthetic report title”</a></h4></div></li></ol></div></div></section>`;

// Three synthetic claims and the search index's answer naming them, best first.
const SEARCH_LOOKUP = {
  articles: {},
  places: 6,
  topics: { teeth: { title: "Mouth and teeth", count: 18 }, gums: { title: "Gum disease", count: 8 } },
  claims: {
    germ: { headline: "Tooth germs were reported to grow teeth", page: "/germ", status: "Preclinical only", meaning: "Laboratory or animal work only.", place: 1, no_signal: null, first_reported: "1 Jan 2020", unchecked: null, names: ["Tooth germ"], indication: "Missing teeth", topic: "teeth" },
    antibody: { headline: "An antibody was reported to regrow teeth", page: "/antibody", status: "Phase 1 trial", meaning: "A Phase 1 trial has started.", place: 3, no_signal: null, first_reported: "2 Feb 2021", unchecked: null, names: ["Antibody X"], indication: "Tooth agenesis", topic: "teeth" },
    sheet: { headline: "A cell sheet was reported to rebuild gum around a tooth", page: "/sheet", status: "Preclinical only", meaning: "Laboratory or animal work only.", place: 1, no_signal: null, first_reported: "3 Mar 2022", unchecked: null, names: ["Cell sheet"], indication: "Periodontitis", topic: "gums" },
  },
};
const SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];

function setup(liveAnswer = null, body = PAGE, searching = body !== PAGE) {
  const { document, window } = parseHTML(`<html><body>${body}</body></html>`);
  let resolveLookup, rejectLookup;
  const pending = new Promise((resolve, reject) => { resolveLookup = resolve; rejectLookup = reject; });
  let requests = 0;
  const results = document.querySelector("#results");
  results.scrollIntoView = () => {};
  const context = {
    document, URL, setTimeout, BRAND: { name: "Example tracker" }, readAddress, closestClaims,
    LIVE, describeAnswer, refusalMessage, textWouldHelp, SUGGEST_SUBJECT, contactLink,
    location: { href: "https://example.test/", origin: "https://example.test" }, history: { replaceState() {} },
    innerHeight: 800, matchMedia: () => ({ matches: false }),
    loadSearchIndex: async () => ({
      search: async () => ({ results: SEARCH_HITS.map((url) => ({ data: async () => ({ url, meta: {} }) })) }),
    }),
    fetch: (url) => {
      requests++;
      if (url === "/api/lookup") return Promise.resolve({ status: 200, json: async () => liveAnswer });
      return searching ? Promise.resolve({ json: async () => SEARCH_LOOKUP }) : pending;
    },
  };
  vm.runInNewContext(script, context);
  return {
    document,
    window,
    results,
    get requests() { return requests; },
    submit(value) {
      document.querySelector("#query").value = value;
      document.querySelector("#search").dispatchEvent(new window.Event("submit", { cancelable: true }));
    },
    resolve() {
      resolveLookup({ json: async () => ({
        articles: { "example.org/old-report": ["old"] },
        claims: { old: { headline: "Earlier report", page: "/old", status: "Trial registered", meaning: "A trial is registered." } },
        places: 6,
      }) });
    },
    reject() { rejectLookup(new Error("offline")); },
    searchRegistry() { results.querySelector("button").dispatchEvent(new window.Event("click")); },
  };
}

test("live website results show each trial's own confidence and collapsed explanation", async () => {
  const page = setup({ about_a_treatment: true, treatment: "EX-1", condition: "tooth agenesis", tracked: [], unscored: 0,
    candidates: [
      { id: "NCT00000001", title: "Synthetic trial one", url: "https://clinicaltrials.gov/study/NCT00000001", score: .94, answer: "match", phases: ["PHASE2"], state: "RECRUITING" },
      { id: "NCT00000002", title: "Synthetic trial two", url: "https://clinicaltrials.gov/study/NCT00000002", score: null, agrees: ["stated"], phases: ["PHASE1"], state: "COMPLETED" },
    ] });
  page.submit("https://example.org/untracked");
  page.resolve();
  await settle();
  assert.match(page.results.textContent, /Search the trial registry/);
  page.searchRegistry();
  await settle();
  assert.equal(page.requests, 2);
  const candidates = [...page.results.querySelectorAll("li")];
  assert.equal(candidates.length, 2);
  assert.match(candidates[0].textContent, /94% match confidence/);
  assert.doesNotMatch(candidates[1].textContent, /94%/);
  assert.match(candidates[1].textContent, /Match confidence unavailable/);
  for (const card of candidates) {
    const details = card.querySelector("details");
    assert.ok(details);
    assert.equal(details.hasAttribute("open"), false);
    assert.match(details.textContent, /not a verified probability/);
    assert.match(details.textContent, /treatment effectiveness or trial quality/);
  }
});

test("the current article lookup still displays its matching claim", async () => {
  const page = setup();
  page.submit("https://example.org/old-report");
  page.resolve();
  await settle();
  assert.match(page.results.textContent, /Earlier report/);
  assert.match(page.results.textContent, /Trial registered/);
});

test("clearing a search prevents an earlier article lookup from reappearing", async () => {
  const page = setup();
  page.submit("https://example.org/old-report");
  assert.equal(page.requests, 1);
  page.submit("");
  assert.equal(page.results.textContent, "");
  page.resolve();
  await settle();
  assert.equal(page.results.textContent, "");
});

for (const outcome of ["resolve", "reject"]) {
  test(`a delayed article lookup ${outcome} cannot replace a later shortened-link answer`, async () => {
    const page = setup();
    page.submit("https://example.org/old-report");
    page.submit("https://bit.ly/new-report");
    assert.match(page.results.textContent, /shortened link/);
    page[outcome]();
    await settle();
    assert.match(page.results.textContent, /shortened link/);
    assert.doesNotMatch(page.results.textContent, /Earlier report|not available/);
  });
}

test("a search on the home page answers in the list's place: best match, its report, then the rest", async () => {
  const page = setup(null, HOME);
  const { document } = page;
  for (const node of document.querySelectorAll("*")) node.getBoundingClientRect = () => ({ top: 0 });
  page.submit("tooth regrowth");
  await settle();
  await settle();
  const answer = document.querySelector("[data-search-answer]");
  assert.equal(answer.hidden, false);
  assert.ok(document.querySelector("[data-days]").hasAttribute("data-searching"));
  assert.match(page.results.textContent, /3 tracked claims match “tooth regrowth”/);
  // The best match: its status in words, then the list's own report row without its status block.
  const digest = answer.querySelector(".digest");
  assert.match(digest.textContent, /Best match/);
  assert.match(digest.textContent, /Preclinical only/);
  assert.equal(digest.querySelector("mark").textContent, "Tooth");
  const row = answer.querySelector(".best-report .report-row");
  assert.match(row.textContent, /Synthetic report title/);
  assert.equal(row.querySelector(".row-now"), null);
  assert.equal(row.hasAttribute("data-day-row"), false);
  assert.equal(row.querySelector("a").getAttribute("style") ?? "", "");
  const others = [...answer.querySelectorAll(".hit-row")];
  assert.deepEqual(others.map((item) => item.querySelector("a").getAttribute("href")), ["/antibody", "/sheet"]);
  assert.match(others[0].textContent, /Phase 1 trial/);
  assert.match(answer.querySelector(".search-more").textContent, /Mouth and teeth, 18 claims · Gum disease, 8 claims/);
  // The topics narrow the answer from the side column.
  const topics = document.querySelector("[data-search-topics]");
  assert.equal(topics.hidden, false);
  const picks = [...topics.querySelectorAll("button")];
  assert.deepEqual(picks.map((pick) => pick.textContent), ["All results 3", "Mouth and teeth 2", "Gum disease 1"]);
  picks[2].dispatchEvent(new page.window.Event("click"));
  assert.match(answer.querySelector(".search-count").textContent, /1 of 3 tracked claims, in Gum disease/);
  assert.equal(answer.querySelectorAll(".hit-row").length, 0);
  // Clearing brings the list back.
  page.results.querySelector("button").dispatchEvent(new page.window.Event("click"));
  assert.equal(answer.hidden, true);
  assert.equal(document.querySelector("[data-days]").hasAttribute("data-searching"), false);
  assert.equal(page.results.textContent, "");
});

test("a search elsewhere answers under the box, with no report row", async () => {
  const page = setup(null, PAGE, true);
  page.submit("tooth regrowth");
  await settle();
  await settle();
  assert.ok(page.results.querySelector(".digest"));
  assert.equal(page.results.querySelector(".best-report"), null);
  assert.equal(page.results.querySelectorAll(".hit-row").length, 2);
});
