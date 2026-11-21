// A pair's trials as a table (lib/trials-table.ts), from the fixture's real pair pages: every
// trial once, results posted first, then by furthest phase, then no phase; no colour or word
// says how a trial turned out, and no phase is worded as an approval.
import assert from "node:assert/strict";
import { test } from "node:test";
import { parseHTML } from "linkedom";
import { readBundle } from "../src/lib/bundle.ts";
import { pairView } from "../src/lib/pair-view.ts";
import { TRIAL_GROUPS, trialGroup, trialGroups, trialsTable } from "../src/lib/trials-table.ts";

const pages = Object.values(readBundle("tests/bundle").pages.PairPage);
const views = pages.map(pairView);

test("every trial of every pair is in the table once, under its group, groups in order", () => {
  const order = ["results", "phase_4", "phase_3", "phase_2", "phase_1", "early_phase_1", "none"];
  for (const view of views) {
    const document = parseHTML(`<main>${trialsTable(view.trials)}</main>`).document;
    const rows = [...document.querySelectorAll("tr[data-trial]")].map((row) => row.dataset.trial);
    assert.deepEqual([...rows].sort(), view.trials.map((trial) => trial.nctId).sort(), view.address);
    const groups = [...document.querySelectorAll("[data-trials-group]")].map((group) => group.dataset.trialsGroup);
    assert.deepEqual(groups, order.filter((key) => groups.includes(key)), view.address);
    for (const group of document.querySelectorAll("[data-trials-group]")) {
      for (const row of group.querySelectorAll("tr[data-trial]")) {
        const trial = view.trials.find((one) => one.nctId === row.dataset.trial);
        assert.equal(trialGroup(trial), group.dataset.trialsGroup, `${view.address} ${trial.nctId}`);
      }
    }
    // Each row opens to its record, the same record the pair page gives the trial.
    assert.equal(document.querySelectorAll(".trials-record > td > details").length, view.trials.length);
  }
});

test("a row's record holds the trial's posted outcomes and papers, written open for a page with no script", () => {
  const view = views.find((one) => one.trials.some((trial) => trial.outcomes.length > 0));
  assert.ok(view, "the fixture has a trial with posted outcomes");
  const document = parseHTML(`<main>${trialsTable(view.trials)}</main>`).document;
  for (const trial of view.trials) {
    const record = document.querySelector(`tr[data-trial="${trial.nctId}"]`).nextElementSibling;
    assert.ok(record.matches(".trials-record"));
    assert.equal(record.querySelectorAll("[data-outcome]").length, trial.outcomes.length, trial.nctId);
    assert.equal(record.querySelectorAll("[data-paper]").length, trial.papers.length, trial.nctId);
    assert.ok(record.querySelector("details").hasAttribute("open"), "open with no script");
  }
  assert.ok(view.trials.some((trial) => trial.outcomes.length > 0));
});

test("a trial that posted results leads, whatever its phase; one with no phase comes last", () => {
  const trial = (over) => ({ nctId: "NCT0", title: null, state: "Finished", phases: null, phaseCodes: [], participants: null, start: null, primaryCompletion: null, arms: [], pairArm: null, whyStopped: null, events: [], papers: [], resultsPosted: false, outcomes: [], registryUrl: "https://clinicaltrials.gov/study/NCT0", ...over });
  const groups = trialGroups([
    trial({ nctId: "NCT1", phaseCodes: ["not_applicable"] }),
    trial({ nctId: "NCT2", phaseCodes: ["phase_2", "phase_3"] }),
    trial({ nctId: "NCT3", phaseCodes: ["phase_1"], resultsPosted: true }),
    trial({ nctId: "NCT4", phaseCodes: ["phase_4"] }),
  ]);
  assert.deepEqual(groups.map((group) => [group.key, group.trials.map((one) => one.nctId)]), [
    ["results", ["NCT3"]],
    ["phase_4", ["NCT4"]],
    ["phase_3", ["NCT2"]],
    ["none", ["NCT1"]],
  ]);
});

test("no words the table writes itself say approved or how a trial turned out, and nothing is styled inline", () => {
  for (const words of Object.values(TRIAL_GROUPS)) assert.doesNotMatch(words, /approv/i);
  for (const view of views) {
    const document = parseHTML(`<main>${trialsTable(view.trials)}</main>`).document;
    // The site's own words: group headings, column heads, each row's results cell and the
    // record's summary; the registry's titles and records are its words, not the site's.
    const own = [
      ...[...document.querySelectorAll(".trials-group-head, thead th, summary")].map((element) => element.textContent),
      ...[...document.querySelectorAll('tr[data-trial] > td[data-label="Results"]')].map((element) => element.textContent),
    ];
    for (const words of own) assert.doesNotMatch(words, /approv|success|fail|positive|negative|work/i, `${view.address}: ${words}`);
    assert.equal(document.querySelectorAll("[style]").length, 0, view.address);
  }
});

test("each record's control names its trial for a screen reader", () => {
  for (const view of views) {
    const document = parseHTML(`<main>${trialsTable(view.trials)}</main>`).document;
    const names = [...document.querySelectorAll(".trials-record summary")].map((summary) => summary.textContent);
    assert.deepEqual(names, view.trials.map((trial) => `Its record: ${trial.nctId}`), view.address);
  }
});
