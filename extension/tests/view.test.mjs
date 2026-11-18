import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import { render } from "../src/view.js";
import { answerOf, candidatesOf } from "../src/kept.js";
import { describeAnswer, LIVE } from "../../site/src/lib/live-lookup.mjs";

// Record the standard DOM operations the renderer emits. Layout is checked in Chrome.
class Element {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.listeners = {};
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  set textContent(value) { this.children = [value]; }
  get textContent() {
    return this.children.map((child) => typeof child === "string" ? child : child.textContent).join("");
  }
}

function elements(root, tagName) {
  return root.children.flatMap((child) => typeof child === "string"
    ? []
    : [...(child.tagName === tagName ? [child] : []), ...elements(child, tagName)]);
}

const originalDocument = globalThis.document;
beforeEach(() => { globalThis.document = { createElement: (tag) => new Element(tag), createElementNS: (_, tag) => new Element(tag) }; });
afterEach(() => { globalThis.document = originalDocument; });

const site = { name: "What came of it?", url: "https://whatcameofit.example" };
const actions = { open() {}, retry() {}, search() {} };
const shown = {
  marked: "Automatic search. This has not been checked by a person.",
  lead: "This appears to report EX-1 for tooth agenesis.",
  tracked: [],
  likelyLead: "Likeliest records first.",
  confidenceMeaning: "Confidence estimates how closely each record matches this report.",
  likely: [],
  notices: ["A registered clinical trial is not a treatment option."],
};

test("a roundup renders separate claim headings, cards and unchecked notices", () => {
  const found = { about_a_treatment: true, claims: [
    { about_a_treatment: true, treatment: "EX-1", condition: "condition one", tracked: [{ headline: "First card", page: "/first" }],
      candidates: [{ id: "NCT00000001", title: "First trial", url: "https://clinicaltrials.gov/study/NCT00000001", answer: "match", score: .9 }] },
    { about_a_treatment: true, treatment: "EX-2 plus EX-3", condition: "condition two", tracked: [], candidates: [], check_state: "unchecked", check_reason: "work_limit" },
  ] };
  const described = describeAnswer(found);
  const root = new Element("main");
  render(root, { kind: "answer", shown: described }, site, actions);
  const sections = elements(root, "section").filter(one => one.className === "independent-claim");
  assert.equal(sections.length, 2);
  assert.match(sections[0].textContent, /EX-1.*condition one.*First card.*First trial/);
  assert.doesNotMatch(sections[0].textContent, /condition two|EX-2/);
  assert.match(sections[1].textContent, /EX-2 plus EX-3.*condition two.*remains unchecked/);
  assert.doesNotMatch(sections[1].textContent, /No matching trial|First trial/);
  assert.equal(elements(root, "h1").length, 1);
  assert.deepEqual(sections.map(section => elements(section, "h2")[0].textContent), ["EX-1", "EX-2 plus EX-3"]);
  assert.equal(elements(sections[0], "h3").length, 2);
  const answer = answerOf({ kind: "answer", shown: described });
  assert.equal(answer.groups.length, 2);
  assert.ok(candidatesOf({ answer }, site).every(candidate => candidate.title.startsWith("EX-1 for condition one")));
  assert.match(answer.limitation, /EX-2 plus EX-3.*remains unchecked/);
  render(root, { kind: "recent", entries: [{ answer, candidates: candidatesOf({ answer }, site),
    title: "Synthetic roundup", url: "https://example.org/roundup", outlet: "example.org", at: Date.now() }] }, site, actions);
  assert.match(root.textContent, /EX-2 plus EX-3.*remains unchecked/);
});

test("search and privacy controls announce that their destination opens in a new tab", () => {
  for (const [state, label, path] of [
    [{ kind: "untracked" }, "Search tracked claims", "/"],
    [{ kind: "sharing", enabled: false }, "Privacy", "/privacy"],
  ]) {
    const root = new Element("main");
    render(root, state, site, actions);
    const link = elements(root, "a").find((item) => item.href === site.url + path);
    assert.ok(link);
    assert.equal(link.textContent, `${label} (opens in a new tab)`);
    assert.equal(elements(link, "svg").length, 1);
  }
});

test("each candidate card owns its title, confidence, record details and source link", () => {
  const root = new Element("main");
  render(root, { kind: "answer", shown: { ...shown, likely: [
    { title: "Study one", url: "https://clinicaltrials.gov/study/NCT00000001", confidenceLabel: "94% match confidence", detail: "Phase 2 · recruiting · NCT00000001", why: "The article gives this record's number." },
    { title: "Study two", url: "https://clinicaltrials.gov/study/NCT00000002", confidenceLabel: "61% match confidence", detail: "Phase 1 · completed · NCT00000002" },
  ] } }, site, actions);

  const cards = elements(root, "li");
  assert.equal(cards.length, 2);
  assert.ok(cards.every((card) => card.className === "result-card"));
  assert.match(cards[0].textContent, /Study one.*NCT00000001.*94% match confidence.*article gives/);
  assert.doesNotMatch(cards[0].textContent, /Study two|61%|NCT00000002/);
  assert.match(cards[1].textContent, /Study two.*NCT00000002.*61% match confidence/);
  assert.equal(elements(cards[0], "a")[0].href, "https://clinicaltrials.gov/study/NCT00000001");
  assert.equal(elements(cards[0], "h2").length, 1);
  assert.equal(root.attributes["aria-busy"], "false");
});

test("older candidates show unavailable confidence and reviewed claims get no invented score", () => {
  const root = new Element("main");
  render(root, { kind: "answer", shown: { ...shown,
    tracked: [{ headline: "Reviewed report", page: "/reviewed" }],
    likely: [{ title: "Older answer", url: "https://clinicaltrials.gov/study/NCT00000001" }],
  } }, site, actions);
  const cards = elements(root, "li");
  assert.match(cards[0].textContent, /Reviewed claim/);
  assert.doesNotMatch(cards[0].textContent, /confidence|100%/);
  assert.match(cards[1].textContent, /Match confidence unavailable/);
});

function visibleText(node) {
  if (typeof node === "string") return node;
  const children = node.tagName === "details" ? node.children.slice(0, 1) : node.children;
  return children.map(visibleText).join(" ");
}

test("a cited mismatch stays inspectable without inflating possible matches", () => {
  const root = new Element("main");
  const described = describeAnswer({ about_a_treatment: true, treatment: "EX-1", condition: "Condition A", candidates: [
    { id: "NCT00000001", title: "Different setting", url: "https://clinicaltrials.gov/study/NCT00000001", score: 0, answer: "other_indication", agrees: ["stated"] },
    { id: "NCT00000002", title: "Matching trial", url: "https://clinicaltrials.gov/study/NCT00000002", score: 0.99, answer: "match" },
  ] });
  render(root, { kind: "answer", shown: described }, site, actions);
  assert.match(visibleText(root), /1 possible match.*Matching trial.*Other records mentioned/s);
  assert.doesNotMatch(visibleText(root), /Different setting|0% match confidence/);
  const mentioned = elements(root, "details").find(item => item.textContent.startsWith(LIVE.mentionedLead));
  assert.match(mentioned.textContent, /Different setting.*0% match confidence.*record's number/);
  assert.equal(elements(mentioned, "a")[0].href, "https://clinicaltrials.gov/study/NCT00000001");
});

test("research titles remain behind collapsed, source-labelled sections with usable links", () => {
  const root = new Element("main"); const opened=[];
  render(root,{kind:"answer",shown:{...shown,research:{
    papers:[{title:"A synthetic paper",url:"https://doi.org/10.1234/example",detail:"2025 · article"}],
    organisations:[{title:"Example University",url:"https://ror.org/02kpeqv85",detail:"Japan"}],
    paperNote:"OpenAlex · Unreviewed",organisationNote:"ROR identity, not endorsement",
  }}},site,{...actions,open:url=>opened.push(url)});
  assert.match(visibleText(root),/Related papers · 1.*Organisations · 1/);
  assert.doesNotMatch(visibleText(root),/synthetic paper|Example University/);
  assert.match(root.textContent,/OpenAlex · Unreviewed.*A synthetic paper.*ROR identity/);
  const links=elements(root,"a");
  links[0].listeners.click({preventDefault(){}});
  assert.equal(opened[0],"https://doi.org/10.1234/example");
});

test("candidates lead the compact view while disclosures retain provenance and confidence limits", () => {
  const root = new Element("main");
  render(root, { kind: "answer", cachedAt: Date.UTC(2026, 10, 13), shown: { ...shown,
    subject: { treatment: "EX-1", condition: "Tooth agenesis" },
    source: "Read from a visible screenshot.", trialSaid: "The article names trial ONE.",
    confidenceMeaning: "A model estimate, not a treatment effectiveness rating.",
    likely: [{ title: "A complete candidate title", url: "https://clinicaltrials.gov/study/NCT00000001",
      confidenceLabel: "61% match confidence", phase: "Phase 1", state: "recruiting", registryId: "NCT00000001", why: "The article names this trial." }],
  } }, site, actions);
  const visible = visibleText(root);
  assert.match(visible, /Automatic · Unreviewed.*Previous result · 13 Nov 2026.*EX-1.*Tooth agenesis.*1 possible match.*A complete candidate title.*Phase 1.*recruiting.*61% match confidence/s);
  assert.match(visible, /Sources & privacy.*Not medical advice.*not a treatment option/s);
  assert.doesNotMatch(visible, /OpenAI reads|The article names|NCT00000001|model estimate/);
  const card = elements(root, "li")[0];
  const detail = elements(card, "details")[0];
  assert.match(detail.textContent, /NCT00000001.*The article names.*not a treatment effectiveness/);
  assert.match(root.textContent, /Read from a visible screenshot.*OpenAI reads.*safety checks/);
  assert.ok(elements(root, "details").every((node) => !node.attributes.open));
  assert.ok(elements(root, "svg").every((node) => node.attributes["aria-hidden"] === "true"));
});

test("compact answer actions retain retry, screenshot preview and sharing settings", () => {
  const root = new Element("main");
  const called = [];
  render(root, { kind: "answer", canVisual: true, shown }, site, { ...actions,
    search: () => called.push("search"), previewVisual: () => called.push("preview"), sharingView: () => called.push("settings"),
  });
  for (const button of elements(root, "button")) button.listeners.click();
  assert.deepEqual(called, ["search", "preview", "settings"]);
});

test("no-match uncertainty and explicit first-use sharing stay visible", () => {
  const root = new Element("main");
  render(root, { kind: "answer", shown: { ...shown, none: "No matching record found. This does not rule out a trial." } }, site, actions);
  assert.match(visibleText(root), /No matching record found.*does not rule out/);
  // A linked paper that was not looked up is said in the open, beside the list.
  const unchecked = describeAnswer({ about_a_treatment: true, treatment: "EX-1", candidates: [], papers_unchecked: 1 }).papersUnchecked;
  render(root, { kind: "answer", shown: { ...shown, papersUnchecked: unchecked } }, site, actions);
  assert.match(visibleText(root), /A linked paper could not be looked up just now/);
  render(root, { kind: "sharing", enabled: false }, site, { ...actions, enableSharing() {}, disableSharing() {} });
  assert.match(visibleText(root), /text, links and cleaned address.*OpenAI.*screenshot automatically.*Allow and search.*Use reviewed claims only/s);
  assert.equal(elements(root, "details").length, 0);
});

test("automatic loading announces busy state and keeps OpenAI and privacy visible", () => {
  const root = new Element("main");
  render(root, { kind: "searching" }, site, actions);
  assert.equal(root.attributes["aria-busy"], "true");
  assert.match(root.textContent, /Reading this page/);
  assert.match(root.textContent, /OpenAI.*retain it for safety checks/);
  assert.equal(elements(root, "a")[0].href, "https://whatcameofit.example/privacy");
  assert.equal(elements(root, "button").length, 0);
});

test("page-change recovery opens a fresh attempt and budget exhaustion is explained", () => {
  const root = new Element("main");
  let retried = false;
  render(root, { kind: "refused", code: "page_changed" }, site, { ...actions, retry: () => { retried = true; } });
  elements(root, "button")[0].listeners.click();
  assert.equal(retried, true);
  render(root, { kind: "refused", code: "budget_exhausted" }, site, actions);
  assert.match(root.textContent, /monthly allowance/);
});

const kept = { recent: 2, following: 1, changed: 1, followed: [], was: {} };
const listActions = {
  ...actions,
  showRecent() {}, showEntry() {}, clearRecent() {}, showFollowing() {}, back() {},
  follow() {}, unfollow() {}, openFollowed() {},
};
const claim = { headline: "Reviewed claim", page: "/reviewed", status: "Phase 1 trial", place: 3, meaning: "Meaning." };
const trackedState = { kind: "tracked", claims: [claim], places: 6, notices: [], lastChecked: null, savedAt: null };

test("a registry claim shows evidence without inventing a first report or a promise", () => {
  const root = new Element("main");
  const registry = {
    ...claim,
    headline: "Registered trials of Example gel for synthetic enamel loss",
    first_reported: null,
    latest_promise: null,
  };
  render(root, { ...trackedState, claims: [registry] }, site, actions);
  assert.match(root.textContent, /Registered trials of Example gel for synthetic enamel loss/);
  assert.doesNotMatch(root.textContent, /First reported|Promised/i);

  const reported = { ...registry, first_reported: "18 Nov 2026" };
  render(root, { ...trackedState, claims: [reported] }, site, actions);
  assert.match(root.textContent, /First reported.*18 Nov 2026/i);
});

test("the lists are offered under an answer, and not while the page is being read", () => {
  const root = new Element("main");
  render(root, trackedState, site, listActions, kept);
  assert.match(root.textContent, /Recently checked.*Following.*1 changed/);
  assert.match(root.textContent, /Keep me up to date/);

  render(root, { kind: "searching" }, site, listActions, kept);
  assert.doesNotMatch(root.textContent, /Recently checked/);

  render(root, trackedState, site, actions);
  assert.doesNotMatch(root.textContent, /Recently checked|Keep me up to date/);
});

test("a wait is one line: the mark, then what is being waited for", () => {
  const root = new Element("main");
  for (const state of [{ kind: "checking" }, { kind: "searching" }, { kind: "capturing" }]) {
    render(root, state, site, listActions, kept);
    const line = root.children[0];
    assert.equal(line.className, "checking");
    assert.equal(line.children[0].attributes.class, "wait-mark");
    assert.equal(typeof line.children[1], "string");
  }
});

test("the tick is drawn for the claim just followed, and only for it", () => {
  const root = new Element("main");
  const mark = () => elements(root, "span").find((span) => span.className?.startsWith("followed-mark"));
  render(root, trackedState, site, listActions, { ...kept, followed: ["/reviewed"], fresh: "/reviewed" });
  assert.equal(mark().className, "followed-mark drawn");
  assert.equal(mark().children[0].children[0].attributes.pathLength, "1");

  render(root, trackedState, site, listActions, { ...kept, followed: ["/reviewed"], fresh: null });
  assert.equal(mark().className, "followed-mark");
});

test("a followed claim that moved says what it was, in words", () => {
  const root = new Element("main");
  render(root, trackedState, site, listActions, { ...kept, followed: ["/reviewed"], was: { "/reviewed": "Trial registered" } });
  assert.match(root.textContent, /Changed since you last looked\. Was: Trial registered\./);
  assert.match(root.textContent, /You follow this claim\..*Stop following/);
  assert.doesNotMatch(root.textContent, /Keep me up to date/);
});

test("a checked page leads to its one claim, its candidates, or back to the page", () => {
  const root = new Element("main");
  const entry = (candidates, answer = { kind: "none" }) => ({
    key: "news.example.org/a", url: "https://news.example.org/a", title: "A report",
    outlet: "news.example.org", at: Date.UTC(2026, 10, 13), answer, candidates,
  });
  let asked = null;
  render(root, { kind: "recent", entries: [
    entry([{ title: "Reviewed claim", url: "https://whatcameofit.example/reviewed", status: "Phase 1 trial" }]),
    entry([{ title: "One", url: "https://r.example/1", status: null }, { title: "Two", url: "https://r.example/2", status: null }],
      { kind: "searched", unreviewed: "Automatic search. Not checked by a person." }),
    entry([]),
  ] }, site, { ...listActions, showEntry: (key) => { asked = key; } }, kept);

  const cards = elements(root, "li");
  assert.equal(cards.length, 3);
  assert.equal(elements(cards[0], "a")[0].href, "https://news.example.org/a");
  assert.match(cards[0].textContent, /news\.example\.org · checked 13 Nov 2026.*Phase 1 trial.*See the evidence/);
  assert.equal(elements(cards[0], "a")[1].href, "https://whatcameofit.example/reviewed");
  assert.match(cards[1].textContent, /Not checked by a person.*2 possible records/);
  elements(cards[1], "button")[0].listeners.click();
  assert.equal(asked, "news.example.org/a");
  assert.match(cards[2].textContent, /No saved trial match/);
  assert.match(root.textContent, /Kept in this browser only.*Clear this list/);

  render(root, { kind: "recent", entries: [] }, site, listActions, kept);
  assert.match(root.textContent, /Nothing checked yet\./);
  assert.doesNotMatch(root.textContent, /Clear this list/);
});

test("the following list says what changed and what is no longer published", () => {
  const root = new Element("main");
  render(root, { kind: "following", claims: [
    { ...claim, gone: false, changed: true, was: "Trial registered" },
    { headline: "Withdrawn claim", page: "/withdrawn", status: "Phase 2 trial", gone: true, changed: false, was: null },
  ] }, site, listActions, kept);
  const cards = elements(root, "li");
  assert.match(cards[0].textContent, /Phase 1 trial.*Changed.*Was: Trial registered\. Now: Phase 1 trial\..*Stop following/);
  assert.match(cards[1].textContent, /This claim is no longer published\./);
  assert.doesNotMatch(cards[1].textContent, /Phase 2 trial/);
  assert.equal(elements(cards[1], "a").length, 0);
});

for (const identified of [false, true]) {
  test(`recent checks preserve whether the registry was searched (${identified})`, () => {
    const answer = answerOf({ kind: "answer", shown: describeAnswer({
      about_a_treatment: identified, treatment: identified ? "EX-1" : null,
      condition: "tooth agenesis", candidates: [], tracked: [],
    }) });
    const entry = { key: "news.example.org/check", url: "https://news.example.org/check",
      title: "Synthetic report", outlet: "news.example.org", at: Date.UTC(2026, 10, 13), answer };
    const root = new Element("main");
    render(root, { kind: "recent", entries: [{ ...entry, candidates: candidatesOf(entry, site) }] }, site, listActions, kept);
    assert.ok(root.textContent.includes(identified ? LIVE.none : LIVE.notATreatment));
    assert.doesNotMatch(root.textContent, /No record was found when this was checked/);
  });
}
