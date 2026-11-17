// What the box offers while a reader types (openspec search-suggestions). Pure
// functions over a small synthetic index: no page, no network.
import assert from "node:assert/strict";
import { test } from "node:test";
import { SUGGEST_ROWS, suggest, suggestParts, suggestWords } from "../src/lib/suggest.ts";

const claim = (page, names, indication, topic, status = "Phase 2 trial") => ({ page, names, indication, topic, status });
const index = {
  topics: {
    lungs: { title: "Lungs and breathing", count: 24 },
    cancer: { title: "Cancer", count: 161 },
    one: { title: "Lung function tests", count: 1 },
  },
  claims: {
    a: claim("/a", ["double lung transplantation"], "Stage 4 lung cancer", "cancer", "No trial record found"),
    b: claim("/b", ["Agent B", "lungzumab"], "Lung cancer", "cancer", "Phase 3 trial"),
    c: claim("/c", ["Agent C"], "Lung cancer", "cancer"),
    d: claim("/d", ["Agent D"], "Non-small cell lung cancer", "cancer"),
    e: claim("/e", ["Agent E"], "Asthma", "lungs"),
    f: claim("/f", ["Lung patch"], "Lung cancer", "cancer"),
  },
};
const detail = {
  claims: {
    a: {
      reports: [{ title: "Synthetic lung report one", outlet: "Example Outlet", date: "8 Jul 2026" }],
      trials: [{ id: "NCT00000001", title: "A synthetic study of lung things", phases: ["Phase 2"] }],
    },
    b: {
      reports: [
        { title: "Synthetic lung report two", outlet: "Example Wire", date: "15 Nov 2026" },
        { title: "Synthetic lung report one", outlet: "Example Outlet", date: "8 Jul 2026" },
      ],
      trials: [
        { id: "NCT00000001", title: "A synthetic study of lung things", phases: ["Phase 2"] },
        { id: "NCT00000002", title: "Another study", phases: [] },
      ],
    },
    e: { reports: [{ title: "Synthetic report with no date, lungs", outlet: "Example Outlet", date: null }], trials: [] },
  },
};
const kinds = (groups) => groups.map((group) => group.kind);
const of = (groups, kind) => groups.find((group) => group.kind === kind)?.rows ?? [];

test("one letter suggests nothing, two do", () => {
  assert.deepEqual(suggestWords("l"), []);
  assert.deepEqual(suggestWords("  Lu  "), ["lu"]);
  assert.deepEqual(suggestWords("lung can"), ["lung", "can"]);
  assert.deepEqual(suggest("l", index, detail), []);
  assert.deepEqual(suggest("", index, detail), []);
});

test("the kinds come in one order, each under its name, two rows at most", () => {
  const groups = suggest("lung", index, detail);
  assert.deepEqual(kinds(groups), ["topic", "treatment", "condition", "report", "trial"]);
  assert.deepEqual(groups.map((group) => group.label), ["Topics", "Treatments", "Conditions", "Reports", "Trials on record"]);
  for (const group of groups) assert.ok(group.rows.length <= SUGGEST_ROWS, group.kind);
});

test("a topic says how many claims it holds and opens its page", () => {
  assert.deepEqual(of(suggest("lung", index, null), "topic"), [
    { kind: "topic", text: "Lungs and breathing", meta: "24 claims", href: "/topic/lungs" },
    { kind: "topic", text: "Lung function tests", meta: "1 claim", href: "/topic/one" },
  ]);
});

test("a treatment is named once for its claim, with what it is for and where the claim stands", () => {
  const rows = of(suggest("lung", index, null), "treatment");
  // A name that begins with the word comes first; the shorter of two first.
  assert.deepEqual(rows[0], { kind: "treatment", text: "Lung patch", sub: "Lung cancer", meta: "Phase 2 trial", href: "/f" });
  // A second name finds the claim; the first name is what is shown, then the name found.
  assert.deepEqual(of(suggest("lungz", index, null), "treatment"), [
    { kind: "treatment", text: "Agent B", also: "lungzumab", sub: "Lung cancer", meta: "Phase 3 trial", href: "/b" },
  ]);
});

test("a condition is one row however many claims are for it, and searches for itself", () => {
  assert.deepEqual(of(suggest("lung", index, null), "condition"), [
    { kind: "condition", text: "Lung cancer", meta: "3 claims", query: "Lung cancer" },
    { kind: "condition", text: "Non-small cell lung cancer", meta: "1 claim", query: "Non-small cell lung cancer" },
  ]);
});

test("every typed word must start a word", () => {
  assert.deepEqual(of(suggest("small lung", index, null), "condition").map((row) => row.text), ["Non-small cell lung cancer"]);
  // "ung" starts no word.
  assert.deepEqual(suggest("ung", index, detail), []);
  // A dot in what is typed is a letter to match, not a pattern.
  assert.deepEqual(suggest("lu.g", index, detail), []);
});

test("reports are newest first, each title once, and open the claim", () => {
  assert.deepEqual(of(suggest("lung", index, detail), "report"), [
    { kind: "report", text: "Synthetic lung report two", meta: "Example Wire · 15 Nov 2026", href: "/b" },
    { kind: "report", text: "Synthetic lung report one", meta: "Example Outlet · 8 Jul 2026", href: "/a" },
  ]);
  assert.deepEqual(of(suggest("lungs", index, detail), "report"), [
    { kind: "report", text: "Synthetic report with no date, lungs", meta: "Example Outlet", href: "/e" },
  ]);
});

test("a trial is found by its title or by the start of its identifier, once", () => {
  assert.deepEqual(of(suggest("lung", index, detail), "trial"), [
    { kind: "trial", text: "NCT00000001", sub: "A synthetic study of lung things", meta: "Phase 2", query: "NCT00000001" },
  ]);
  assert.deepEqual(of(suggest("nct0000000", index, detail), "trial").map((row) => row.text), ["NCT00000002", "NCT00000001"]);
});

test("until the search detail is loaded, reports and trials are left out", () => {
  assert.deepEqual(kinds(suggest("lung", index, null)), ["topic", "treatment", "condition"]);
});

test("the typed words are marked where they start a word", () => {
  assert.deepEqual(suggestParts("Lungs and lung", "lung"), [
    { text: "Lung", hit: true },
    { text: "s and ", hit: false },
    { text: "lung", hit: true },
  ]);
  assert.deepEqual(suggestParts("Flung far", "lung"), [{ text: "Flung far", hit: false }]);
  assert.deepEqual(suggestParts("Plain", ""), [{ text: "Plain", hit: false }]);
});
