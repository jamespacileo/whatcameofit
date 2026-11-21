// "What the record shows" on a pair page (lib/progress.ts, lib/pair-render.ts renderProgress;
// docs/adr/0015), on the fixture bundle's real pair pages: the step is the furthest of the five
// a record exists for, it names the record that put it there, and it is never drawn without
// its caution facts. No wording says how a trial turned out.
import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { parseHTML } from "linkedom";
import { readBundle } from "../src/lib/bundle.ts";
import { pairView } from "../src/lib/pair-view.ts";
import { CAUTIONS_LEAD, NO_CAUTIONS, PROGRESS_NOTE, STOP_REASON_LEAD, renderPairBand, renderPairSheet } from "../src/lib/pair-render.ts";
import { PROGRESS_STEPS, progressOf } from "../src/lib/progress.ts";
import { PAIR_PROGRESS_STEPS } from "../src/lib/pair-wording.ts";
import { assertNoOutcomeVerdict } from "../src/lib/trial-facts.ts";

const { pages } = readBundle(fileURLToPath(new URL("./bundle", import.meta.url)));
const files = pages.PairPage;
const pageOf = (view) => parseHTML(`<main>${renderPairBand(view)}${renderPairSheet(view)}</main>`).document;
const recordedKinds = (file) =>
  new Set(file.trials.flatMap((trial) => trial.events.filter((event) => event.day_basis !== "registry_date_estimated").map((event) => event.kind)));

test("each pair of the fixture stands on the step its records put it on", () => {
  // Read from the registry records in the bundle: the trial and day are the event that reached the step.
  const expected = {
    "curcumin--gastritis-atrophic": ["results", "NCT02782949", "2024-03-05"],
    "apitegromab--muscular-atrophy-spinal": ["results", "NCT03921528", "2022-11-17"],
    "apitegromab--obesity": ["finished", "NCT06445075", "2025-06-17"],
    "tulisokibart--hidradenitis-suppurativa": ["started", "NCT06956235", "2025-06-09"],
    "ambroxol--dementia": ["registered", "NCT02914366", "2016-09-26"],
  };
  for (const [address, [step, nctId, day]] of Object.entries(expected)) {
    const progress = progressOf(files[address]);
    assert.deepEqual([progress.step, progress.reason.nctId, progress.reason.day], [step, nctId, day], address);
    assert.equal(progress.place, PROGRESS_STEPS.indexOf(step) + 1, address);
  }
});

test("the step is the furthest a recorded event exists for, and never above it", () => {
  const kindOf = { results: "results_posted", finished: "completed", started: "started", registered: "registered" };
  for (const [address, file] of Object.entries(files)) {
    const progress = progressOf(file);
    const kinds = recordedKinds(file);
    // No regulator decision is in the fixture, so no pair is on the last step.
    assert.notEqual(file.row.status.code, "approved", address);
    assert.notEqual(progress.step, "regulator", address);
    // Every pair here reached its step by a dated event, which the page can point at.
    assert.ok(kinds.has(kindOf[progress.step]), `${address}: ${progress.step}`);
    assert.ok(file.trials.some((trial) => trial.events.some((event) => event.key === progress.reason.eventKey)), address);
    for (const later of PROGRESS_STEPS.slice(progress.place, 4)) assert.ok(!kinds.has(kindOf[later]), `${address}: a record for ${later} exists`);
  }
});

test("the page draws the level in one hue with its name, its record and, always, its caution facts", () => {
  for (const file of Object.values(files)) {
    const view = pairView(file);
    const document = pageOf(view);
    const panel = document.querySelector("[data-progress]");
    assert.ok(panel, view.address);
    assert.equal(document.querySelector("h2#record").textContent, "What the record shows");
    assert.ok(document.querySelector('.onpage a[href="#record"]'), `${view.address}: the section list names it`);
    assert.equal(panel.dataset.progress, view.progress.step);
    const steps = [...panel.querySelectorAll(".progress-steps span")];
    assert.equal(steps.length, 5);
    assert.equal(steps.filter((step) => step.className === "on").length, view.progress.place, view.address);
    // Filled or empty, nothing else: no step carries a colour of its own.
    assert.ok(steps.every((step) => step.className === "on" || step.className === ""));
    assert.equal(panel.querySelector("[data-progress-step]").textContent, `Step ${view.progress.place} of 5: ${PAIR_PROGRESS_STEPS[view.progress.step]}`);
    assert.equal(panel.querySelector("[data-progress-event]").textContent, view.progress.nctId);
    assert.match(panel.textContent, new RegExp(PROGRESS_NOTE.replace(/[.]/g, "\\.")));
    // Never the level alone: the caution facts, or the sentence that the records hold none.
    const cautions = panel.querySelector("[data-cautions]");
    assert.ok(cautions, `${view.address}: the level is drawn without its caution facts`);
    assert.equal(cautions.querySelectorAll("[data-caution]").length, Math.max(1, view.progress.cautions.length), view.address);
    assertNoOutcomeVerdict([...panel.querySelectorAll("p:not(.note), .note")].map((line) => line.textContent));
  }
});

test("a pair whose records hold no caution fact says so, in the one sentence", () => {
  for (const file of Object.values(files)) {
    // The small bundle's pairs hold no caution fact; four that do are in tests/caution-bundle.
    assert.ok(file.trials.every((trial) => !["terminated", "suspended", "withdrawn"].includes(trial.facts.overall_status)));
    assert.ok(file.trials.every((trial) => trial.findings?.due?.code !== "no_results_a_year_after_completion"));
    const view = pairView(file);
    assert.deepEqual(view.progress.cautions, []);
    assert.equal(pageOf(view).querySelector('[data-caution="none"]').textContent, NO_CAUTIONS);
  }
});

// Four real pairs with caution facts, copied byte for byte from the lab's store at lab commit
// 3274611d, with that version's own schemas (docs/adr/0015, known defect 6). A bundle of their
// own, because the small bundle's schemas are an older lab version's and the two are never mixed.
const caution = readBundle(fileURLToPath(new URL("./caution-bundle", import.meta.url))).pages.PairPage;
const NBSP = " ";
const cautionLines = (address) =>
  [...pageOf(pairView(caution[address])).querySelectorAll("[data-cautions] li")].map((line) => [line.dataset.caution, line.textContent]);

test("a trial with no results a year after primary completion is said so, with the day checked and the days since", () => {
  // The day and the days are the lab's `findings.due` for the trial (as_of, days_since_completion).
  assert.deepEqual(cautionLines("zilganersen--alexander-disease"), [
    [
      "no_results",
      `NCT04849741: no summary results were on ClinicalTrials.gov when checked on 21${NBSP}Nov${NBSP}2026, 456 days after primary completion. Results may be available elsewhere.`,
    ],
  ]);
  // Both of the pair's trials, each on its own line.
  assert.deepEqual(cautionLines("evorpacept--squamous-cell-carcinoma-of-head-and-neck"), [
    [
      "no_results",
      `NCT04675294: no summary results were on ClinicalTrials.gov when checked on 21${NBSP}Nov${NBSP}2026, 628 days after primary completion. Results may be available elsewhere.`,
    ],
    [
      "no_results",
      `NCT04675333: no summary results were on ClinicalTrials.gov when checked on 21${NBSP}Nov${NBSP}2026, 628 days after primary completion. Results may be available elsewhere.`,
    ],
  ]);
});

test("a trial that ended early is said so in the registry's state, with no reason clause when the record carries none", () => {
  // The store at 3274611d carries no why_stopped for any trial (docs/adr/0015, known defects),
  // so neither the reason's lead nor an empty quotation is drawn.
  assert.equal(caution["metformin--colonic-neoplasms"].trials[0].facts.why_stopped, null);
  assert.deepEqual(cautionLines("metformin--colonic-neoplasms"), [["ended_early", "NCT01440127: stopped early."]]);
  const withdrawn = caution["semaglutide--polycystic-ovary-syndrome"].trials.find((trial) => trial.nct_id === "NCT06222437");
  assert.equal(withdrawn.facts.why_stopped, null);
  assert.deepEqual(cautionLines("semaglutide--polycystic-ovary-syndrome"), [["ended_early", "NCT06222437: withdrawn before it started."]]);
  for (const address of ["metformin--colonic-neoplasms", "semaglutide--polycystic-ovary-syndrome"]) {
    const cautions = pageOf(pairView(caution[address])).querySelector("[data-cautions]");
    assert.equal(cautions.querySelector("q"), null, address);
    assert.ok(!cautions.textContent.includes(STOP_REASON_LEAD), address);
  }
});

test("a caution fact never moves the step: each pair stands where its recorded events put it", () => {
  const expected = {
    "zilganersen--alexander-disease": ["started", "NCT04849741", "2021-06-01"],
    "evorpacept--squamous-cell-carcinoma-of-head-and-neck": ["started", "NCT04675294", "2021-04-02"],
    // Terminated with 9 taking part, but its start is a month with no basis, so it has no
    // started event and stays on the first step (docs/adr/0015, known defects).
    "metformin--colonic-neoplasms": ["registered", "NCT01440127", "2011-09-26"],
    "semaglutide--polycystic-ovary-syndrome": ["started", "NCT05702905", "2023-05-09"],
  };
  assert.deepEqual(Object.keys(caution).sort(), Object.keys(expected).sort());
  for (const [address, [step, nctId, day]] of Object.entries(expected)) {
    const file = caution[address];
    const progress = progressOf(file);
    assert.ok(progress.cautions.length > 0, address);
    assert.deepEqual([progress.step, progress.reason.nctId, progress.reason.day], [step, nctId, day], address);
    const panel = pageOf(pairView(file)).querySelector("[data-progress]");
    assert.equal(panel.dataset.progress, step, address);
    assert.equal(panel.querySelector("[data-progress-step]").textContent, `Step ${progress.place} of 5: ${PAIR_PROGRESS_STEPS[step]}`, address);
    assert.equal(panel.querySelectorAll(".progress-steps span.on").length, progress.place, address);
    // The caution facts are drawn under their lead, and the sentence that there are none is not.
    assert.equal(panel.querySelector('[data-caution="none"]'), null, address);
    assert.equal(panel.querySelector("[data-cautions] > p").textContent, CAUTIONS_LEAD, address);
    assertNoOutcomeVerdict([...panel.querySelectorAll("li")].map((line) => line.textContent));
  }
});
