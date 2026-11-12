import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import { render } from "../src/view.js";

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
beforeEach(() => { globalThis.document = { createElement: (tag) => new Element(tag) }; });
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

test("each candidate card owns its title, confidence, record details and source link", () => {
  const root = new Element("main");
  render(root, { kind: "answer", shown: { ...shown, likely: [
    { title: "Study one", url: "https://clinicaltrials.gov/study/NCT00000001", confidenceLabel: "94% match confidence", detail: "Phase 2 · recruiting · NCT00000001", why: "The article gives this record's number." },
    { title: "Study two", url: "https://clinicaltrials.gov/study/NCT00000002", confidenceLabel: "61% match confidence", detail: "Phase 1 · completed · NCT00000002" },
  ] } }, site, actions);

  const cards = elements(root, "li");
  assert.equal(cards.length, 2);
  assert.ok(cards.every((card) => card.className === "result-card"));
  assert.match(cards[0].textContent, /Study one.*94% match confidence.*NCT00000001.*article gives/);
  assert.doesNotMatch(cards[0].textContent, /Study two|61%|NCT00000002/);
  assert.match(cards[1].textContent, /Study two.*61% match confidence.*NCT00000002/);
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

test("automatic loading announces busy state and keeps OpenAI and privacy visible", () => {
  const root = new Element("main");
  render(root, { kind: "searching" }, site, actions);
  assert.equal(root.attributes["aria-busy"], "true");
  assert.match(root.textContent, /Reading this page/);
  assert.match(root.textContent, /OpenAI.*retain text for safety checks/);
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
