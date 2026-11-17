import { createHash } from "node:crypto";
import assert from "node:assert/strict";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import vm from "node:vm";
import { test } from "node:test";
import { parseHTML } from "linkedom";
import { readAddress, closestClaims } from "../src/lib/lookup-match.mjs";
import { ranked, searchWords, wordPattern, wordsIn } from "../src/lib/search-order.ts";
import { suggest, suggestParts, suggestWords } from "../src/lib/suggest.ts";
import { SUGGEST_SUBJECT, contactLink } from "../src/lib/contact.mjs";
import { LIVE, describeAnswer, refusalMessage, textWouldHelp } from "../src/lib/live-lookup.mjs";
import {
  NOT_AN_OPTION, NO_REPORT, PHASE_WORDS, SEARCH_WORDS, STATE_WORDS, changedShort, findListed, forbiddenWord, listingWords,
  registryDate, searchListing, setNote,
} from "../src/lib/trial-page.mjs";
import { PARTS_SEARCHED_AT_ONCE, PART_BYTES, partFor, splitListing } from "../src/lib/trial-listing-parts.mjs";

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
// Words the search index does not hold whole, in a test; none unless a test names them.
// As the real index does, it still answers for such a word alone, with a shorter one.
let NOT_WHOLE = [];
// The media queries that match, in a test: none, so a wide screen worked by a mouse.
let MEDIA = [];
// The pages the search index was asked to read, in the order asked.
let pagesRead = [];
// How a page found is read, in a test: at once unless a test holds it back or fails it.
const readNow = async (url) => ({ url, meta: {}, content: SEARCH_LOOKUP.claims[url.replaceAll("/", "")]?.headline });
let readHit = readNow;
// What the index is asked before it answers, in a test: nothing held back unless a test
// holds a search, as a slow network would.
let beforeSearch = async () => {};
// The search index as the built site's answers: every page found, each read only when
// asked for, with how many of them each topic holds; narrowed to one topic on request.
function searchIndex() {
  const topicOf = (url) => SEARCH_LOOKUP.claims[url.replaceAll("/", "")]?.topic;
  return {
    filters: async () => ({}),
    search: async (words, options) => {
      await beforeSearch(words, options);
      if (NOT_WHOLE.some((word) => words === `"${word}"`)) return { results: [], filters: {} };
      const topic = {};
      for (const url of SEARCH_HITS) if (topicOf(url)) topic[topicOf(url)] = (topic[topicOf(url)] ?? 0) + 1;
      const found = SEARCH_HITS.filter((url) => !options?.filters || topicOf(url) === options.filters.topic);
      return {
        results: found.map((url) => ({ data: () => { pagesRead.push(url); return readHit(url); } })),
        filters: { topic },
      };
    },
  };
}
// The trial listing a build carries: synthetic. None unless a test sets it.
let LISTING = null;
// Which claims cite which trials, as the build's trial index has it.
let TRIAL_INDEX = { trials: {} };
let listingRequests = 0;
// How large a part of the listing is in a test, the parts asked for, and whether they answer.
let PART_SIZE = PART_BYTES;
let PARTS_UNREADABLE = false;
let retainedParts = {};
let partRequests = [];
function listingFiles() {
  const cut = splitListing(LISTING.trials, PART_SIZE);
  const { trials, ...head } = LISTING;
  const file = (part) => {
    const hash = createHash("sha256").update(JSON.stringify({ ...head, trials: part.trials })).digest("hex");
    return `/trials-listing/${part.name}-${hash}.json`;
  };
  return {
    manifest: { ...head, total: trials.length, parts: cut.map((part) => ({ file: file(part), first: part.first, last: part.last, trials: part.trials.length })) },
    parts: Object.fromEntries(cut.map((part) => [file(part), { ...head, trials: part.trials }])),
  };
}
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

function setup(liveAnswer = null, body = PAGE, searching = body !== PAGE, initial = "https://example.test/") {
  const location = { href: initial, origin: "https://example.test" };
  const entries = [{ state: null, url: initial }];
  let position = 0;
  const history = {
    get length() { return entries.length; },
    get state() { return entries[position].state; },
    replaceState(state, _, url = location.href) {
      entries[position] = { state, url: String(url) };
      location.href = String(url);
    },
    pushState(state, _, url) {
      entries.splice(++position, entries.length, { state, url: String(url) });
      location.href = String(url);
    },
    go(delta) {
      position += delta;
      location.href = entries[position].url;
      listeners.popstate({ state: history.state });
    },
  };
  // What the script listens for on the window, by event name.
  const listeners = {};
  const { document, window } = parseHTML(`<html><head><title>Example tracker</title></head><body>${body}</body></html>`);
  let resolveLookup, rejectLookup;
  const pending = new Promise((resolve, reject) => { resolveLookup = resolve; rejectLookup = reject; });
  let requests = 0;
  let searches = 0;
  const results = document.querySelector("#results");
  results.scrollIntoView = () => {};
  const context = {
    document, URL, crypto, setTimeout, BRAND: { name: "Example tracker" }, readAddress, closestClaims,
    suggest, suggestParts, suggestWords, ranked, searchWords, wordPattern, wordsIn,
    LIVE, describeAnswer, refusalMessage, textWouldHelp, SUGGEST_SUBJECT, contactLink,
    NOT_AN_OPTION, NO_REPORT, PHASE_WORDS, SEARCH_WORDS, STATE_WORDS, changedShort, findListed, listingWords, registryDate,
    searchListing, setNote, PARTS_SEARCHED_AT_ONCE, partFor,
    location, history, addEventListener: (type, heard) => { listeners[type] = heard; },
    innerHeight: 800, matchMedia: (query) => ({ matches: MEDIA.includes(query) }),
    loadSearchIndex: async () => {
      searches++;
      return searchIndex();
    },
    fetch: (url) => {
      requests++;
      if (url === "/api/lookup") return Promise.resolve({ status: 200, json: async () => liveAnswer });
      if (!searching) return pending;
      if (url === "/search-detail.json") return Promise.resolve({ ok: true, json: async () => SEARCH_DETAIL });
      if (url === "/trial-index.json") return Promise.resolve(TRIAL_INDEX ? { ok: true, json: async () => TRIAL_INDEX } : { ok: false, status: 404 });
      // The listing as the build serves it: a manifest, and the parts it names.
      if (url === "/trials-listing.json") {
        listingRequests++;
        return Promise.resolve(LISTING ? { ok: true, json: async () => listingFiles().manifest } : { ok: false, status: 404 });
      }
      if (url.startsWith("/trials-listing/")) {
        partRequests.push(url);
        const part = LISTING && !PARTS_UNREADABLE ? (listingFiles().parts[url] ?? retainedParts[url]) : null;
        return Promise.resolve(part ? { ok: true, json: async () => part } : { ok: false, status: 404 });
      }
      return Promise.resolve({ json: async () => SEARCH_LOOKUP });
    },
  };
  vm.runInNewContext(script, context);
  return {
    document,
    window,
    history,
    location,
    listeners,
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

test("a lookup that cannot be read offers the same question again, never the box that failed", async () => {
  const page = setup();
  page.submit("https://example.org/old-report");
  page.reject();
  await settle();
  assert.match(page.results.textContent, /The lookup is not available right now\./);
  assert.doesNotMatch(page.results.textContent, /typed in the box/);
  assert.equal(page.results.querySelector("a").getAttribute("href"), "/topics");
  const again = page.results.querySelector("button");
  assert.equal(again.textContent, "Try again");
  again.dispatchEvent(new page.window.Event("click"));
  assert.match(page.results.textContent, /Looking up/);
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
  assert.match(page.results.textContent, /^3 tracked claims for “tooth regrowth”, shown below\.$/);
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
  await settle();
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
  // Its marks are the page's own, softer than the words; inside a line neither hangs.
  assert.deepEqual([...report.querySelectorAll("a .quote-mark")].map((mark) => mark.className), ["quote-mark", "quote-mark"]);
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
  assert.equal(answer.querySelector(".search-count span").textContent, "2 tracked claims");
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
});

test("each search looked up is a step Back returns to, and an emptied field leaves no answer", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  const page = setup(null, HOME);
  const answer = await searched(page, "tooth regrowth");
  assert.match(page.location.href, /[?&]q=tooth\+regrowth/);
  // The line under the box leads to the answer's heading.
  assert.equal(page.results.querySelector("a").getAttribute("href"), "#search-answer-title");
  assert.equal(answer.querySelector("h2").id, "search-answer-title");

  // Back: the address has no words again, and the list is back in the answer's place.
  page.history.go(-1);
  assert.equal(answer.hidden, true);
  assert.equal(page.results.textContent, "");
  assert.equal(page.document.querySelector("#query").value, "");

  // Forward: the words are in the field and answered again.
  page.history.go(1);
  for (let turn = 0; turn < 4; turn++) await settle();
  assert.equal(page.document.querySelector("#query").value, "tooth regrowth");
  assert.equal(answer.hidden, false);

  // The field emptied, as its cross or Escape leaves it.
  const field = page.document.querySelector("#query");
  field.value = "";
  field.focus = () => {};
  field.dispatchEvent(new page.window.Event("input"));
  assert.equal(answer.hidden, true);
  assert.equal(page.results.textContent, "");
  assert.doesNotMatch(page.location.href, /q=/);
});

test("the count is of every claim found; the rest are drawn under the first at a press", async (t) => {
  manyHits(t, 25, () => "teeth");
  const page = setup(null, HOME);
  const answer = await searched(page, "tooth regrowth");
  assert.equal(shownCount(answer), "First 20 of 25 tracked claims");
  assert.match(page.results.textContent, /^The first 20 of 25 tracked claims for “tooth regrowth” are shown below\.$/);
  const first = shownClaims(answer);
  assert.equal(first.length, 20);
  const more = answer.querySelector("button.show-more");
  assert.equal(more.textContent, "Show 5 more");
  assert.match(answer.querySelector(".show-more-says").textContent, /^5 more tracked claims hold these words\.$/);

  more.dispatchEvent(new page.window.Event("click"));
  for (let turn = 0; turn < 4; turn++) await settle();
  // Those on screen keep their order; the new one follows them, and nothing is left.
  assert.deepEqual(shownClaims(answer).slice(0, 20), first);
  assert.equal(new Set(shownClaims(answer)).size, 25);
  assert.equal(shownCount(answer), "25 tracked claims");
  assert.equal(answer.querySelector("button.show-more"), null);
  assert.match(page.results.textContent, /^25 tracked claims for “tooth regrowth”, shown below\.$/);
});

test("topics count every claim found, and a topic picked shows its claims, reading those not yet read", async () => {
  // The index finds 25 claims: 22 on teeth, 3 on gums. The first twenty read are all on
  // teeth; the three on gums are among the five not read.
  const lookup = structuredClone(SEARCH_LOOKUP);
  const kept = SEARCH_LOOKUP.claims;
  for (let at = 0; at < 22; at++) {
    lookup.claims[`tooth-${at}`] = { ...kept.germ, headline: `Synthetic tooth claim ${at}`, page: `/tooth-${at}`, topic: "teeth" };
  }
  for (let at = 0; at < 3; at++) {
    lookup.claims[`gum-${at}`] = { ...kept.sheet, headline: `Synthetic gum claim ${at}`, page: `/gum-${at}`, topic: "gums" };
  }
  SEARCH_LOOKUP.claims = lookup.claims;
  const teeth = Array.from({ length: 22 }, (_, at) => `/tooth-${at}/`);
  const gums = Array.from({ length: 3 }, (_, at) => `/gum-${at}/`);
  SEARCH_HITS = [...teeth.slice(0, 20), ...gums, ...teeth.slice(20)];
  pagesRead = [];
  try {
    const page = setup(null, HOME);
    const answer = await searched(page, "synthetic");
    assert.match(answer.querySelector(".search-count").textContent, /^First 20 of 25 tracked claims/);
    // Each topic's count is of every claim found, not of the twenty read.
    const picks = () => [...answer.querySelectorAll(".search-topic-row button")];
    assert.deepEqual(picks().map((pick) => pick.textContent), ["All results 25", "Mouth and teeth 22", "Gum disease 3"]);
    assert.equal(pagesRead.length, 20, "only the first twenty pages are read for the counts");

    // Gum disease: none of its claims was among those read. They are read and shown.
    picks()[2].dispatchEvent(new page.window.Event("click"));
    for (let turn = 0; turn < 4; turn++) await settle();
    assert.deepEqual([...answer.querySelectorAll("a.hit-title")].map((link) => link.getAttribute("href")), ["/gum-0", "/gum-1", "/gum-2"]);
    assert.match(answer.querySelector(".search-count").textContent, /^3 of 25 tracked claims, in Gum disease/);
    assert.equal(answer.querySelector("button.show-more"), null);
    assert.deepEqual(pagesRead.slice(20), gums);
    assert.equal(picks()[2].getAttribute("aria-pressed"), "true");

    // Mouth and teeth holds more than are drawn at once: its count says so, and the
    // rest of that topic's claims follow at a press.
    picks()[1].dispatchEvent(new page.window.Event("click"));
    for (let turn = 0; turn < 4; turn++) await settle();
    assert.match(answer.querySelector(".search-count").textContent, /^First 20 of 22 in Mouth and teeth, of 25 tracked claims/);
    assert.equal(answer.querySelectorAll(".hit-row").length, 20);
    assert.match(answer.querySelector(".show-more-says").textContent, /^2 more tracked claims in Mouth and teeth hold these words\.$/);
    answer.querySelector("button.show-more").dispatchEvent(new page.window.Event("click"));
    for (let turn = 0; turn < 4; turn++) await settle();
    assert.equal(answer.querySelectorAll(".hit-row").length, 22);
    assert.match(answer.querySelector(".search-count").textContent, /^22 of 25 tracked claims, in Mouth and teeth/);
    assert.equal(picks()[1].getAttribute("aria-pressed"), "true");

    // Back on every claim, the first twenty stand as they did.
    picks()[0].dispatchEvent(new page.window.Event("click"));
    for (let turn = 0; turn < 4; turn++) await settle();
    assert.match(answer.querySelector(".search-count").textContent, /^First 20 of 25 tracked claims/);
    assert.equal(answer.querySelectorAll(".hit-row").length, 20);
  } finally {
    SEARCH_LOOKUP.claims = kept;
    SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  }
});

test("a searched word no tracked claim holds is named; the start of a word that is held is not", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  // Neither is in the index whole. No page has a word starting "toothtooth"; "too" starts "tooth".
  NOT_WHOLE = ["toothtooth", "too"];
  try {
    const answer = await searched(setup(null, HOME), "tooth toothtooth");
    assert.equal(answer.querySelector(".search-unheld").textContent, "No tracked claim holds “toothtooth”. These claims were found without that word.");
    assert.equal(answer.querySelectorAll(".hit-row").length, 3);
    const started = await searched(setup(null, HOME), "too");
    assert.equal(started.querySelector(".search-unheld"), null);
    // Words that are all held say nothing of it.
    const held = await searched(setup(null, HOME), "tooth regrowth");
    assert.equal(held.querySelector(".search-unheld"), null);
  } finally {
    NOT_WHOLE = [];
  }
});

test("a search is named in the page's title until it is cleared; a pasted link never is", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  const page = setup(null, HOME);
  const answer = await searched(page, "tooth regrowth");
  assert.equal(page.document.title, "“tooth regrowth” · Example tracker");
  answer.querySelector("button.search-clear").dispatchEvent(new page.window.Event("click"));
  assert.equal(page.document.title, "Example tracker");
  page.submit("https://example.org/old-report");
  assert.equal(page.document.title, "Example tracker");
});

test("on a narrow touch screen the line under the box is kept for a screen reader only, and a typed search puts the reader on the answer", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  MEDIA = ["(max-width: 34rem)", "(pointer: coarse)"];
  try {
    const page = setup(null, HOME);
    const focused = [];
    page.window.HTMLElement.prototype.focus = function () { focused.push(this.id || this.tagName); };
    const field = page.document.querySelector("#query");
    // The reader typed in the field and sent it: the field holds the focus.
    Object.defineProperty(page.document, "activeElement", { get: () => field, configurable: true });
    const answer = await searched(page, "tooth regrowth");
    const note = page.results.querySelector(".search-note");
    assert.ok(note.classList.contains("visually-hidden"));
    assert.equal(note.textContent, "3 tracked claims for “tooth regrowth”, shown below.");
    assert.equal(note.querySelector("a"), null, "a line that is not drawn holds no link");
    assert.equal(answer.querySelector(".search-title").id, "search-answer-title");
    assert.deepEqual(focused, ["search-answer-title"]);
  } finally {
    MEDIA = [];
  }
});

test("a search typed with a mouse and keys leaves the reader in the field", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  const page = setup(null, HOME);
  const focused = [];
  page.window.HTMLElement.prototype.focus = function () { focused.push(this.id || this.tagName); };
  const field = page.document.querySelector("#query");
  Object.defineProperty(page.document, "activeElement", { get: () => field, configurable: true });
  await searched(page, "tooth regrowth");
  assert.deepEqual(focused, []);
  assert.equal(page.results.querySelector(".search-note").classList.contains("visually-hidden"), false);
});

test("the suggestions stand in the form, after its hint, and each row says what taking it does", async () => {
  const page = setup(null, HOME);
  for (const node of page.document.querySelectorAll("*")) node.getBoundingClientRect = () => ({ top: 0 });
  const field = page.document.querySelector("#query");
  field.value = "tooth";
  field.dispatchEvent(new page.window.Event("input"));
  for (let turn = 0; turn < 4; turn++) await settle();
  const panel = page.document.querySelector("#suggestions");
  assert.equal(panel.hidden, false);
  assert.equal(panel.parentElement.id, "search");
  assert.equal(panel.nextElementSibling, null, "the rows come after everything else in the form");
  const row = (kind) => panel.querySelector(`.suggest-row.is-${kind}`).textContent;
  assert.match(row("treatment"), /Opens its page\.$/);
  assert.match(row("condition"), /Searches here\.$/);
  assert.match(panel.querySelector(".suggest-all").textContent, /^Search everything for “tooth”$/);
});

test("a topic picked is kept in the page's address and cleared with the search", async () => {
  SEARCH_HITS = ["/germ/", "/antibody/", "/sheet/"];
  const page = setup(null, HOME);
  const answer = await searched(page, "tooth regrowth");
  [...answer.querySelectorAll(".search-topic-row button")][2].dispatchEvent(new page.window.Event("click"));
  await settle();
  assert.match(page.location.href, /[?&]topic=gums/);
  answer.querySelector("button.search-clear").dispatchEvent(new page.window.Event("click"));
  assert.doesNotMatch(page.location.href, /topic=|q=/);
});

function manyHits(t, count, topicAt) {
  const previous = SEARCH_HITS;
  const claims = SEARCH_LOOKUP.claims;
  t.after(() => {
    SEARCH_HITS = previous;
    SEARCH_LOOKUP.claims = claims;
    readHit = readNow;
  });
  SEARCH_LOOKUP.claims = { ...claims };
  SEARCH_HITS = Array.from({ length: count }, (_, at) => {
    const slug = `synthetic-${at}`;
    const page = `/${slug}`;
    SEARCH_LOOKUP.claims[slug] = { ...claims.germ, page, topic: topicAt(at) };
    return `${page}/`;
  });
}

const shownCount = (answer) => answer.querySelector(".search-count span").textContent;
const shownClaims = (answer) => [...answer.querySelectorAll("a.hit-title")].map((link) => link.getAttribute("href"));
const click = (page, node) => node.dispatchEvent(new page.window.Event("click"));

test("changing topic during Show more cannot advance the same batch twice", async (t) => {
  manyHits(t, 62, (at) => at % 2 ? "gums" : "teeth");
  const pending = Promise.withResolvers();
  const nextBatch = SEARCH_HITS.slice(20, 40);
  const reads = [];
  readHit = async (url) => {
    reads.push(url);
    if (nextBatch.includes(url)) await pending.promise;
    return { url, meta: {} };
  };
  const page = setup(null, HOME);
  const answer = await searched(page, "tooth regrowth");
  assert.equal(reads.length, 20);
  const first = shownClaims(answer);
  click(page, answer.querySelector(".show-more"));
  // The topic is picked while every claim's next batch is on its way. The topic has
  // pages of its own; the batch already asked for is the only one in flight.
  click(page, answer.querySelector('button[data-topic="gums"]'));
  const during = answer.querySelector(".show-more");
  pending.resolve();
  assert.equal(during.disabled, true);
  click(page, during);
  for (let turn = 0; turn < 4; turn++) await settle();
  // Twenty of every claim, twenty more of them once, and the topic's own first twenty.
  assert.equal(reads.length, 60);
  assert.equal(answer.querySelector('button[data-topic="gums"]').getAttribute("aria-pressed"), "true");
  assert.equal(shownCount(answer), "First 20 of 31 in Gum disease, of 62 tracked claims");
  click(page, answer.querySelector('button[data-topic=""]'));
  await settle();
  assert.equal(reads.length, 60);
  assert.equal(shownCount(answer), "First 40 of 62 tracked claims");
  assert.deepEqual(shownClaims(answer).slice(0, 20), first);
  click(page, answer.querySelector(".show-more"));
  await settle();
  assert.equal(shownCount(answer), "First 60 of 62 tracked claims");
  click(page, answer.querySelector(".show-more"));
  await settle();
  assert.equal(shownCount(answer), "62 tracked claims");
  assert.equal(new Set(shownClaims(answer)).size, 62);
});

test("retrying a failed batch preserves the first page and loads the same next claims", async (t) => {
  manyHits(t, 41, () => "teeth");
  let unavailable = true;
  readHit = async (url) => {
    if (unavailable && url === "/synthetic-39/") throw new Error("offline");
    return { url, meta: {} };
  };
  const page = setup(null, HOME);
  const answer = await searched(page, "tooth regrowth");
  const first = shownClaims(answer);
  click(page, answer.querySelector(".show-more"));
  await settle();
  assert.match(answer.querySelector(".show-more-says").textContent, /could not be read/);
  assert.deepEqual(shownClaims(answer), first);
  const retry = answer.querySelector(".show-more");
  assert.equal(retry.disabled, false);
  unavailable = false;
  click(page, retry);
  await settle();
  assert.equal(shownCount(answer), "First 40 of 41 tracked claims");
  assert.deepEqual(shownClaims(answer).slice(0, 20), first);
  assert.equal(shownClaims(answer).at(-1), "/synthetic-39");
});

test("an exact headline promotes one indexed claim without increasing the count", async (t) => {
  manyHits(t, 40, () => "teeth");
  SEARCH_HITS[24] = "/sheet/";
  const page = setup(null, HOME);
  const answer = await searched(page, "cell sheets for gums");
  assert.equal(answer.querySelector(".digest h3 a").getAttribute("href"), "/sheet");
  assert.equal(shownCount(answer), "First 20 of 40 tracked claims");
  const first = shownClaims(answer);
  assert.equal(first.length, 19);
  click(page, answer.querySelector(".show-more"));
  await settle();
  assert.equal(shownCount(answer), "40 tracked claims");
  assert.deepEqual(shownClaims(answer).slice(0, 19), first);
  assert.equal(new Set(shownClaims(answer)).size, 39);
  assert.equal(answer.querySelectorAll('a.hit-title[href="/sheet"]').length, 0);
});

test("Back and Forward restore loaded results and a topic first found on page two", async (t) => {
  manyHits(t, 42, (at) => at < 20 ? "teeth" : "gums");
  const page = setup(null, HOME);
  const answer = await searched(page, "tooth regrowth");
  click(page, answer.querySelector(".show-more"));
  await settle();
  click(page, answer.querySelector('button[data-topic="gums"]'));
  await settle();
  click(page, answer.querySelector(".show-more"));
  await settle();
  const chosen = shownClaims(answer);
  assert.equal(chosen.length, 22);
  const filtered = page.location.href;
  click(page, answer.querySelector(".search-clear"));
  page.history.go(-1);
  await settle();
  assert.equal(page.location.href, filtered);
  assert.deepEqual(shownClaims(answer), chosen);
  page.history.go(1);
  assert.equal(answer.hidden, true);
});

test("a late topic or batch never replaces a newer topic or search", async (t) => {
  manyHits(t, 62, (at) => at % 2 ? "gums" : "teeth");
  const gate = Promise.withResolvers();
  beforeSearch = async (_, options) => {
    if (options?.filters?.topic === "gums") await gate.promise;
  };
  t.after(() => { beforeSearch = async () => {}; });
  const page = setup(null, HOME);
  const answer = await searched(page, "tooth regrowth");
  // Gum disease is asked for and held back; Mouth and teeth is asked for after it.
  click(page, answer.querySelector('button[data-topic="gums"]'));
  click(page, answer.querySelector('button[data-topic="teeth"]'));
  for (let turn = 0; turn < 4; turn++) await settle();
  assert.equal(shownCount(answer), "First 20 of 31 in Mouth and teeth, of 62 tracked claims");
  gate.resolve();
  for (let turn = 0; turn < 4; turn++) await settle();
  assert.equal(answer.querySelector('button[data-topic="teeth"]').getAttribute("aria-pressed"), "true");
  assert.equal(shownCount(answer), "First 20 of 31 in Mouth and teeth, of 62 tracked claims");
  assert.match(page.location.href, /[?&]topic=teeth/);

  // A batch asked for under one search arrives after the next search has answered.
  const pending = Promise.withResolvers();
  const held = SEARCH_HITS.slice(20, 40);
  readHit = async (url) => {
    if (held.includes(url)) await pending.promise;
    return { url, meta: {} };
  };
  click(page, answer.querySelector('button[data-topic=""]'));
  await settle();
  click(page, answer.querySelector(".show-more"));
  await searched(page, "gum regrowth");
  pending.resolve();
  for (let turn = 0; turn < 4; turn++) await settle();
  assert.equal(answer.querySelector(".search-title").textContent, "Results for “gum regrowth”");
  assert.equal(shownCount(answer), "First 20 of 62 tracked claims");
  assert.equal(page.history.state.lookup.pages, undefined, "the new step keeps no depth from the old search");
  assert.match(page.location.href, /[?&]q=gum\+regrowth/);
});

test("a shared search can open on a topic first found on page two", async (t) => {
  manyHits(t, 42, (at) => at < 20 ? "teeth" : "gums");
  const initial = "https://example.test/?q=tooth+regrowth&topic=gums";
  const page = setup(null, HOME, true, initial);
  await settle();
  const answer = page.document.querySelector("[data-search-answer]");
  assert.equal(page.location.href, initial);
  assert.equal(answer.querySelector('button[data-topic="gums"]').getAttribute("aria-pressed"), "true");
  assert.equal(shownClaims(answer)[0], "/synthetic-20");
});

test("Back and Forward redraw an article lookup without writing its link to history", async () => {
  const article = "https://example.org/untracked-article";
  const page = setup(null, HOME);
  const field = page.document.querySelector("#query");
  page.submit(article);
  await settle();
  assert.match(page.results.textContent, /not one we track/);
  assert.equal(page.history.length, 2);
  assert.equal(page.location.href, "https://example.test/");
  assert.ok(!JSON.stringify(page.history.state).includes(article));

  field.value = "";
  field.dispatchEvent(new page.window.Event("input"));
  assert.equal(page.results.textContent, "");
  assert.equal(page.history.length, 3);
  page.history.go(-1);
  await settle();
  assert.equal(field.value, article);
  assert.match(page.results.textContent, /not one we track/);
  page.history.go(-1);
  assert.equal(field.value, "");
  page.history.go(1);
  await settle();
  assert.equal(field.value, article);
  page.history.go(1);
  assert.equal(field.value, "");
  assert.equal(page.results.textContent, "");
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
  // A title that leads its own line hangs its opening mark, as a row of the list does.
  assert.deepEqual(
    [...answer.querySelectorAll(".search-report-title .quote-mark")].map((mark) => mark.className),
    ["quote-mark open", "quote-mark"],
  );
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
  // Words were typed: the reader is not told a name can be typed.
  assert.doesNotMatch(page.results.textContent, /typed in the box/);
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

test("a listed trial a claim cites through an approved match leads to that claim", async () => {
  // The listing names no claim for it: its column knows only trials cited by an event.
  LISTING = structuredClone(FIXTURE_LISTING);
  LISTING.trials[1][8] = null;
  TRIAL_INDEX = { trials: {
    NCT09000001: [{ slug: "sheet", headline: "x", possible: true }, { slug: "germ", headline: "x" }],
    // Only a possible match: counted for nothing, so still no report linked.
    NCT09000003: [{ slug: "antibody", headline: "x", possible: true }],
  } };
  const page = setup(null, HOME);
  const answer = await searched(page, "zetamab");
  for (let turn = 0; turn < 4; turn++) await settle();
  const rows = [...answer.querySelectorAll(".listed-trial")];
  const matched = rows.find((row) => /NCT09000001/.test(row.textContent));
  assert.equal(matched.querySelector("a.listed-title").getAttribute("href"), "/germ");
  assert.match(matched.textContent, /See the tracked claim: Tooth germs were reported to grow teeth/);
  assert.doesNotMatch(matched.textContent, /No news report/);
  const possible = rows.find((row) => /NCT09000003/.test(row.textContent));
  assert.equal(possible.querySelector("a.listed-title").getAttribute("href"), "/trials/NCT09000003");
  assert.match(possible.textContent, /No news report is linked to this record yet\./);
  // By its number too.
  const byNumber = await searched(setup(null, HOME), "NCT09000001");
  assert.equal(byNumber.querySelector(".listed-trial a.listed-title").getAttribute("href"), "/germ");
  // Without the index of cited trials, no listed trial is shown at all.
  TRIAL_INDEX = null;
  const blind = setup(null, HOME);
  const unsure = await searched(blind, "zetamab");
  for (let turn = 0; turn < 4; turn++) await settle();
  assert.equal(unsure.querySelector(".listed-trial"), null);
  TRIAL_INDEX = { trials: {} };
  LISTING = null;
});

// A listing cut into more parts than are searched at once: every row its own part.
function large() {
  LISTING = FIXTURE_LISTING;
  PART_SIZE = 1;
  partRequests = [];
  PARTS_UNREADABLE = false;
  assert.ok(listingFiles().manifest.parts.length > PARTS_SEARCHED_AT_ONCE);
}
function small() {
  retainedParts = {};
  LISTING = null;
  PART_SIZE = PART_BYTES;
  PARTS_UNREADABLE = false;
}

test("a registry number in a large listing is found by reading the one part that holds it", async () => {
  large();
  const page = setup(null, HOME);
  const answer = await searched(page, "NCT09000002");
  assert.deepEqual(partRequests, [partFor(listingFiles().manifest, "NCT09000002").file]);
  assert.equal(answer.querySelector(".listed-trial a.listed-title").getAttribute("href"), "/trials/NCT09000002");
  // The day the registry last changed the record stands with its state.
  assert.match(answer.querySelector(".listed-trial .match-source").textContent, /Not started · Record last changed 30 Jun 2026$/);
  // A number between two parts' ranges, or past the last, is in no part: nothing is read.
  partRequests = [];
  await searched(page, "NCT09999999");
  assert.deepEqual(partRequests, []);
  small();
});

test("a large listing is searched for words only when the reader asks", async () => {
  large();
  const page = setup(null, HOME);
  const answer = await searched(page, "zetamab");
  const group = answer.querySelector(".listed-trials") ?? page.results.querySelector(".listed-trials");
  assert.ok(group, "the reader is not offered the search");
  assert.deepEqual(partRequests, [], "no part is read before the reader asks");
  assert.equal(group.querySelector(".listed-trial"), null);
  const button = group.querySelector("button");
  assert.equal(button.textContent, SEARCH_WORDS.ask(FIXTURE_LISTING.trials.length));
  assert.ok(group.textContent.includes(NOT_AN_OPTION));

  button.dispatchEvent(new page.window.Event("click"));
  await settle();
  assert.equal(partRequests.length, listingFiles().manifest.parts.length, "every part is read once");
  const rows = [...group.querySelectorAll(".listed-trial")];
  assert.deepEqual(rows.map((row) => row.querySelector(".match-source").textContent.match(/NCT\d{8}/)[0]).sort(), ["NCT09000001", "NCT09000003"]);
  assert.equal(group.querySelector("button"), null);
  assert.equal(forbiddenWord(group.textContent.replace(NOT_AN_OPTION, "")), null);

  // Once read, the listing answers the next search with nothing more fetched or asked.
  partRequests = [];
  const next = await searched(page, "EX-9");
  const again = next.querySelector(".listed-trials") ?? page.results.querySelector(".listed-trials");
  assert.equal(again.querySelectorAll(".listed-trial").length, 1);
  assert.deepEqual(partRequests, []);
  small();
});

test("a reader who asks is told when no listed trial has the words, or the listing cannot be read", async () => {
  large();
  const page = setup(null, HOME);
  await searched(page, "nonesuchword");
  const group = page.document.querySelector(".listed-trials");
  group.querySelector("button").dispatchEvent(new page.window.Event("click"));
  await settle();
  assert.ok(group.textContent.includes(SEARCH_WORDS.none));
  assert.equal(group.querySelector(".listed-trial"), null);

  large();
  PARTS_UNREADABLE = true;
  const other = setup(null, HOME);
  await searched(other, "zetamab");
  const asked = (other.document.querySelector("[data-search-answer] .listed-trials") ?? other.results.querySelector(".listed-trials"));
  asked.querySelector("button").dispatchEvent(new other.window.Event("click"));
  await settle();
  assert.ok(asked.textContent.includes(SEARCH_WORDS.unread));
  assert.equal(asked.querySelector("button").disabled, false);
  small();
});

test("the search's line on which trials are listed is worded from the set's name", () => {
  assert.equal(setNote("active-since-2025", "2026-11-17"), `Phase 2 and 3 studies that ClinicalTrials.gov lists as not finished. ${NOT_AN_OPTION}`);
  assert.equal(setNote("active-or-ended-this-year", "2026-11-17"), `Studies that ClinicalTrials.gov lists as not finished, or as ended in 2026. ${NOT_AN_OPTION}`);
  // A set with no words here is described as no more than it surely is.
  assert.equal(setNote("constructor", null), `Studies registered on ClinicalTrials.gov. ${NOT_AN_OPTION}`);
});

test("the listing is cut in registry-number order into parts no larger than asked, every row once", () => {
  const rows = Array.from({ length: 500 }, (_, at) => [`NCT${String(90000000 - at * 7).padStart(8, "0")}`, `A synthetic study ${at}`, null, [], "under_way", null, [], [], null]);
  const parts = splitListing(rows, 2000);
  assert.ok(parts.length > 10);
  const ids = parts.flatMap((part) => part.trials.map((row) => row[0]));
  assert.deepEqual(ids, rows.map((row) => row[0]).sort());
  assert.equal(new Set(parts.map((part) => part.name)).size, parts.length);
  for (const [at, part] of parts.entries()) {
    assert.ok(JSON.stringify(part.trials).length <= 2000 + 2, part.name);
    assert.deepEqual([part.first, part.last], [part.trials[0][0], part.trials.at(-1)[0]]);
    if (at) assert.ok(parts[at - 1].last < part.first);
    for (const row of part.trials) assert.equal(partFor({ parts }, row[0].toLowerCase()), part);
  }
  assert.equal(partFor({ parts }, "NCT00000001"), null);
  assert.deepEqual(splitListing([]), []);
  // A row larger than a part is a part of its own, never dropped.
  assert.equal(splitListing([["NCT00000001", "x".repeat(50)], ["NCT00000002", "y"]], 10).length, 2);
});



test("an open page follows a trial across deployments and searches one whole generation", async (t) => {
  const first = "NCT00000001", target = "NCT00000003";
  const row = (id, generation) => [id, `Zetamab ${generation} ${id}`, null, [], "under_way", null, [], [], null];
  const old = { ...FIXTURE_LISTING, trials: [row(first, "older"), row(target, "older")] };
  const newer = { ...FIXTURE_LISTING, trials: ["NCT00000000", first, target].map((id) => row(id, "newer")) };
  // This fixture's target is a listed trial without a published claim.
  const owner = SEARCH_DETAIL.claims.antibody;
  const cited = owner.trials;
  owner.trials = [];
  t.after(() => { owner.trials = cited; small(); });
  for (const keep of [false, true]) {
    PART_SIZE = 1;
    LISTING = old;
    retainedParts = keep ? listingFiles().parts : {};
    const byId = setup(null, HOME), byWords = setup(null, HOME);
    const oldFile = partFor(listingFiles().manifest, target).file;
    // Read one old part into each tab before changing what the server returns.
    for (const page of [byId, byWords]) {
      assert.match((await searched(page, first)).textContent, /Zetamab older NCT00000001/);
    }
    LISTING = newer;
    assert.match(oldFile, /\/01-/);
    assert.match(partFor(listingFiles().manifest, target).file, /\/02-/);
    const version = keep ? "older" : "newer";
    const result = (await searched(byId, target)).textContent;
    assert.ok(result.includes(`Zetamab ${version} ${target}`), result);
    const answer = await searched(byWords, "zetamab");
    const group = answer.querySelector(".listed-trials") ?? byWords.results.querySelector(".listed-trials");
    if (!keep) {
      // The replacement listing is large. Reading it still requires a press.
      assert.equal(group.querySelectorAll(".listed-trial").length, 0);
      group.querySelector(".listed-ask").dispatchEvent(new byWords.window.Event("click"));
      await settle();
    }
    const titles = [...group.querySelectorAll(".listed-trial .listed-title")].map((a) => a.textContent);
    assert.deepEqual(titles.sort(), (keep ? old : newer).trials.map((r) => r[1]).sort());
  }
});
