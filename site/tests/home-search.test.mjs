import assert from "node:assert/strict";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import vm from "node:vm";
import { test } from "node:test";
import { parseHTML } from "linkedom";
import { readAddress, closestClaims } from "../src/lib/lookup-match.mjs";
import { SUGGEST_SUBJECT, contactLink } from "../src/lib/contact.mjs";
import { LIVE, describeAnswer, refusalMessage, textWouldHelp } from "../src/lib/live-lookup.mjs";
import { NO_REPORT, PHASE_WORDS, SEARCH_WORDS, STATE_WORDS, findListed, forbiddenWord, searchListing } from "../src/lib/trial-page.mjs";

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
  <div class="row-main"><p class="row-source"><span class="outlet"><a href="https://example.org/germ-report">Example Outlet</a></span></p>
  <h4 class="row-title"><a href="/germ" style="view-transition-name: r-germ">“Synthetic report title”</a></h4></div></li></ol></div></div></section>`;

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
let SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
// The trial listing a build carries: synthetic. None unless a test sets it.
let LISTING = null;
let listingRequests = 0;
const FIXTURE_LISTING = JSON.parse(fs.readFileSync(new URL("./fixture-trials-listing.json", import.meta.url), "utf8"));

// What each synthetic claim's reports and trials are, as the search detail file has them.
const SEARCH_DETAIL = {
  claims: {
    germ: {
      reports: [
        { title: "Synthetic report title", outlet: "Example Outlet", domain: "example.org", icon: "/outlet-icons/example.org.png", url: "https://example.org/germ-report", date: "1 Jan 2020" },
        { title: "Regrowing teeth from germs", outlet: "Second Outlet", domain: "second.example", icon: null, url: "https://second.example/teeth", date: "5 Jan 2020" },
      ],
      trials: [],
    },
    antibody: {
      reports: [{ title: "New drug to regrow lost teeth", outlet: "Example University", domain: "uni.example", icon: "/outlet-icons/uni.example.ico", url: "https://uni.example/news", date: "2 Feb 2021" }],
      trials: [{ id: "NCT00000003", title: "Antibody for missing teeth", registry: "ClinicalTrials.gov", url: "https://clinicaltrials.gov/study/NCT00000003", phases: ["Phase 1"] }],
    },
    sheet: { reports: [{ title: "Cell sheets for gums", outlet: "Gum News", domain: "gum.example", icon: null, url: "https://gum.example/a", date: "3 Mar 2022" }], trials: [] },
  },
};

function setup(liveAnswer = null, body = PAGE, searching = body !== PAGE) {
  const history = { replaceState() {} };
  const { document, window } = parseHTML(`<html><body>${body}</body></html>`);
  let resolveLookup, rejectLookup;
  const pending = new Promise((resolve, reject) => { resolveLookup = resolve; rejectLookup = reject; });
  let requests = 0;
  let searches = 0;
  const results = document.querySelector("#results");
  results.scrollIntoView = () => {};
  const context = {
    document, URL, setTimeout, BRAND: { name: "Example tracker" }, readAddress, closestClaims,
    LIVE, describeAnswer, refusalMessage, textWouldHelp, SUGGEST_SUBJECT, contactLink,
    NO_REPORT, PHASE_WORDS, SEARCH_WORDS, STATE_WORDS, findListed, searchListing,
    location: { href: "https://example.test/", origin: "https://example.test" }, history,
    innerHeight: 800, matchMedia: () => ({ matches: false }),
    loadSearchIndex: async () => {
      searches++;
      return {
        search: async () => ({ results: SEARCH_HITS.map((url) => ({ data: async () => ({ url, meta: {} }) })) }),
      };
    },
    fetch: (url) => {
      requests++;
      if (url === "/api/lookup") return Promise.resolve({ status: 200, json: async () => liveAnswer });
      if (!searching) return pending;
      if (url === "/search-detail.json") return Promise.resolve({ ok: true, json: async () => SEARCH_DETAIL });
      if (url === "/trials-listing.json") {
        listingRequests++;
        return Promise.resolve(LISTING ? { ok: true, json: async () => LISTING } : { ok: false, status: 404 });
      }
      return Promise.resolve({ json: async () => SEARCH_LOOKUP });
    },
  };
  vm.runInNewContext(script, context);
  return {
    document,
    window,
    history,
    results,
    get requests() { return requests; },
    get searches() { return searches; },
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

async function searched(page, words) {
  for (const node of page.document.querySelectorAll("*")) node.getBoundingClientRect = () => ({ top: 0 });
  page.submit(words);
  for (let turn = 0; turn < 4; turn++) await settle();
  return page.document.querySelector("[data-search-answer]");
}

test("a search on the home page answers in the list's place: the closest match, then the rest", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  const page = setup(null, HOME);
  const { document } = page;
  const answer = await searched(page, "tooth regrowth");
  assert.equal(answer.hidden, false);
  assert.ok(document.querySelector("[data-days]").hasAttribute("data-searching"));
  assert.match(page.results.textContent, /Results for “tooth regrowth” are shown below\./);
  // The count is said once, beside the one way out.
  assert.match(answer.querySelector(".search-count").textContent, /^3 tracked claims/);
  assert.equal(answer.querySelectorAll("button.search-clear").length, 1);
  // A word search leads with a row, labelled, not a digest.
  assert.equal(answer.querySelector(".digest"), null);
  const rows = [...answer.querySelectorAll(".hit-row")];
  assert.equal(rows.length, 3);
  assert.match(rows[0].querySelector(".hit-now").textContent, /Closest match.*Preclinical only.*First reported 1 Jan 2020/);
  assert.equal(rows[0].querySelector("h3 a").getAttribute("href"), "/germ");
  assert.equal(rows[0].querySelector("mark").textContent, "Tooth");
  assert.equal(answer.querySelector("#other-matches").textContent, "Other matches");
  assert.match(answer.querySelector(".search-more").textContent, /Mouth and teeth, 18 claims · Gum disease, 8 claims/);
  // The topics narrow the answer from the side column and from the row under the heading.
  const topics = document.querySelector("[data-search-topics]");
  assert.equal(topics.hidden, false);
  const picks = [...topics.querySelectorAll("button")];
  assert.deepEqual(picks.map((pick) => pick.textContent), ["All results 3", "Mouth and teeth 2", "Gum disease 1"]);
  assert.equal(answer.querySelectorAll(".search-topic-row button").length, 3);
  picks[2].dispatchEvent(new page.window.Event("click"));
  assert.match(answer.querySelector(".search-count").textContent, /1 of 3 tracked claims, in Gum disease/);
  assert.equal(answer.querySelectorAll(".hit-row").length, 1);
  // Clearing brings the list back.
  answer.querySelector("button.search-clear").dispatchEvent(new page.window.Event("click"));
  assert.equal(answer.hidden, true);
  assert.equal(document.querySelector("[data-days]").hasAttribute("data-searching"), false);
  assert.equal(page.results.textContent, "");
});

test("a search elsewhere answers under the box, with the same rows and the way out", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  const page = setup(null, PAGE, true);
  page.submit("tooth regrowth");
  for (let turn = 0; turn < 4; turn++) await settle();
  assert.equal(page.results.querySelectorAll(".hit-row").length, 3);
  assert.ok(page.results.querySelector("button.search-clear"));
  assert.equal(page.results.querySelectorAll(".search-topic-row button").length, 3);
});

test("matches are ordered by where the words stand side by side, and say what they were found in", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  const page = setup(null, HOME);
  const answer = await searched(page, "regrowing teeth");
  // "regrow teeth" in the antibody claim's own headline puts it ahead of the index's first.
  const rows = [...answer.querySelectorAll(".hit-row")];
  assert.deepEqual(rows.map((row) => row.querySelector("h3 a").getAttribute("href")), ["/antibody", "/germ", "/sheet"]);
  // A report line names its outlet with the outlet's icon over a letter tile, and its date.
  const [report, trial] = rows[0].querySelectorAll(".match-reason");
  assert.match(report.textContent, /“New drug to regrow lost teeth”/);
  assert.equal(report.querySelector(".outlet-icon img").getAttribute("src"), "/outlet-icons/uni.example.ico");
  assert.equal(report.querySelector(".outlet-icon .tile").textContent, "U");
  assert.match(report.textContent, /Example University.*2 Feb 2021/);
  assert.deepEqual([...report.querySelectorAll("mark")].map((mark) => mark.textContent), ["regrow", "teeth"]);
  assert.match(trial.textContent, /Trial.*Antibody for missing teeth.*ClinicalTrials\.gov NCT00000003 · Phase 1/);
  assert.match(rows[1].textContent, /Regrowing teeth from germs/);
  // A match whose reports and trials hold none of the words has no such lines.
  assert.equal(rows[2].querySelector(".match-reasons"), null);
});

test("words that are a tracked report's headline lead with that report, then its claim", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/"];
  const page = setup(null, HOME);
  const answer = await searched(page, "cell sheets for GUMS!");
  assert.match(answer.querySelector(".exact-says").textContent, /A tracked report has this headline/);
  const report = answer.querySelector(".search-report");
  assert.match(report.textContent, /Gum News.*3 Mar 2022.*Gum disease/);
  assert.deepEqual([...report.querySelectorAll("mark")].map((mark) => mark.textContent), ["Cell", "sheets", "for", "gums"]);
  const digest = answer.querySelector(".digest");
  assert.match(digest.textContent, /Its claim · on record now/);
  assert.equal(digest.querySelector("h3 a").getAttribute("href"), "/sheet");
  assert.equal(answer.querySelector("#other-matches").textContent, "Other claims with these words");
  assert.match(answer.querySelector(".jump-others").textContent, /2 other claims with these words/);
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
});

test("a topic picked is kept in the page's address and cleared with the search", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  const page = setup(null, HOME);
  const addresses = [];
  page.history.replaceState = (_, __, url) => addresses.push(String(url));
  const answer = await searched(page, "tooth regrowth");
  [...answer.querySelectorAll(".search-topic-row button")][2].dispatchEvent(new page.window.Event("click"));
  assert.match(addresses.at(-1), /[?&]topic=gums/);
  answer.querySelector("button.search-clear").dispatchEvent(new page.window.Event("click"));
  assert.doesNotMatch(addresses.at(-1), /topic=|q=/);
});

test("a registry identifier is answered with its trial and the claim it belongs to", async () => {
  const page = setup(null, HOME);
  const answer = await searched(page, "nct00000003");
  assert.equal(page.searches, 0, "an identifier never goes to the word search");
  assert.equal(answer.querySelector(".search-title").textContent, "NCT00000003");
  assert.match(answer.querySelector(".search-count").textContent, /On record for one tracked claim/);
  const record = answer.querySelector(".trial-record");
  assert.match(record.textContent, /ClinicalTrials\.gov NCT00000003.*Phase 1.*Antibody for missing teeth.*A trial on record is not a treatment option\./);
  assert.match(answer.querySelector(".digest").textContent, /Phase 1 trial/);
  assert.match(answer.querySelector(".search-report").textContent, /“New drug to regrow lost teeth”/);
});

test("an identifier with no trial on record says so and links to its registry", async () => {
  const page = setup(null, PAGE, true);
  page.submit("nct99999999");
  for (let turn = 0; turn < 4; turn++) await settle();
  assert.match(page.results.textContent, /No trial with the identifier NCT99999999 is matched to a claim tracked here\./);
  const link = [...page.results.querySelectorAll("a")].find((anchor) => /ClinicalTrials\.gov/.test(anchor.textContent));
  assert.equal(link.getAttribute("href"), "https://clinicaltrials.gov/study/NCT99999999");
  assert.equal(page.searches, 0);
});

test("a search that finds nothing says so plainly and points to pasting a link", async () => {
  SEARCH_HITS = [];
  const page = setup(null, PAGE, true);
  page.submit("zzzqqq");
  for (let turn = 0; turn < 4; turn++) await settle();
  assert.match(page.results.textContent, /Nothing tracked here matches “zzzqqq”\./);
  assert.match(page.results.textContent, /paste the article's link/);
  assert.doesNotMatch(page.results.textContent, /We say that a lot/);
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
});

test("Scenario: A search for an identifier no claim cites", async () => {
  LISTING = FIXTURE_LISTING;
  listingRequests = 0;
  const page = setup(null, HOME);
  assert.equal(listingRequests, 0, "the listing is fetched before any search");
  const answer = await searched(page, "nct09000001");
  assert.equal(page.searches, 0);
  assert.equal(listingRequests, 1);
  assert.equal(answer.querySelector(".search-title").textContent, "NCT09000001");
  const row = answer.querySelector(".listed-trial");
  assert.equal(row.querySelector("a.listed-title").getAttribute("href"), "/trials/NCT09000001");
  assert.match(row.textContent, /SYNTH-1: A synthetic study of zetamab.*ClinicalTrials\.gov NCT09000001 · Phase 3 · Under way.*No news report is linked to this record yet\./);
  assert.match(answer.textContent, /A trial on record is not a treatment option\./);
  assert.equal(forbiddenWord(answer.textContent.replace("A trial on record is not a treatment option.", "")), null);
  LISTING = null;
});

test("words are answered with listed trials after the claims, and a cited one leads to its claim", async () => {
  LISTING = structuredClone(FIXTURE_LISTING);
  // The fixture's cited trial, named for a claim this page's index holds.
  LISTING.trials[0][8] = "antibody";
  listingRequests = 0;
  const page = setup(null, HOME);
  const answer = await searched(page, "synthetic");
  for (let turn = 0; turn < 4; turn++) await settle();
  assert.equal(listingRequests, 1);
  const group = answer.querySelector(".listed-trials");
  assert.ok(group, "no listed trials are shown");
  // After every claim that matched.
  const claims = [...answer.querySelectorAll(".hit-row")];
  assert.ok(claims.length > 0 && answer.innerHTML.lastIndexOf("hit-row") < answer.innerHTML.indexOf("listed-trials"));
  assert.equal(group.querySelector("h3").textContent, "Registered trials with these words");
  const rows = [...group.querySelectorAll(".listed-trial")];
  assert.equal(rows.length, 4);
  const cited = rows.find((row) => /NCT00000002/.test(row.textContent));
  assert.equal(cited.querySelector("a.listed-title").getAttribute("href"), "/antibody");
  assert.match(cited.textContent, /See the tracked claim: An antibody was reported to regrow teeth/);
  assert.doesNotMatch(cited.textContent, /No news report/);
  for (const row of rows.filter((other) => other !== cited)) {
    assert.match(row.querySelector("a.listed-title").getAttribute("href"), /^\/trials\/NCT0900000\d$/);
    assert.match(row.textContent, /No news report is linked to this record yet\./);
  }
  assert.doesNotMatch(group.textContent, /recruit/i);
  // Narrowing the claims by topic keeps the listed trials.
  [...answer.querySelectorAll(".search-topic-row button")][1]?.dispatchEvent(new page.window.Event("click"));
  assert.ok(page.document.querySelector("[data-search-answer] .listed-trials"));
  LISTING = null;
});

test("words no claim holds are still answered with listed trials; none found adds nothing", async () => {
  LISTING = FIXTURE_LISTING;
  SEARCH_HITS = [];
  const page = setup(null, PAGE, true);
  page.submit("zetamab kidney");
  for (let turn = 0; turn < 6; turn++) await settle();
  assert.match(page.results.textContent, /Nothing tracked here matches “zetamab kidney”\./);
  const rows = [...page.results.querySelectorAll(".listed-trial")];
  assert.equal(rows.length, 1);
  assert.match(rows[0].textContent, /NCT09000003/);
  page.submit("zzzqqq");
  for (let turn = 0; turn < 6; turn++) await settle();
  assert.equal(page.results.querySelector(".listed-trials"), null);
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  LISTING = null;
});
