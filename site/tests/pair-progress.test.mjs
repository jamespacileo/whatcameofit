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
import { NO_CAUTIONS, PROGRESS_NOTE, renderPairBand, renderPairSheet } from "../src/lib/pair-render.ts";
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

test("a pair whose records hold no caution fact says so; the fixture holds no trial that ended early or is past its year", () => {
  for (const file of Object.values(files)) {
    // What the fixture can show. A pair with a trial ended early, or a year past completion with
    // no results, is on staging and not in this bundle (docs/adr/0015, "Known defects").
    assert.ok(file.trials.every((trial) => !["terminated", "suspended", "withdrawn"].includes(trial.facts.overall_status)));
    assert.ok(file.trials.every((trial) => trial.findings?.due?.code !== "no_results_a_year_after_completion"));
    const view = pairView(file);
    assert.deepEqual(view.progress.cautions, []);
    assert.equal(pageOf(view).querySelector('[data-caution="none"]').textContent, NO_CAUTIONS);
  }
});
