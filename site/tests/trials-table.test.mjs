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
    assert.equal(document.querySelectorAll(".trials-record details").length, view.trials.length);
  }
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

test("no phase is worded as an approval, and the table names no colour or verdict", () => {
  for (const words of Object.values(TRIAL_GROUPS)) assert.doesNotMatch(words, /approv/i);
  for (const view of views) {
    const html = trialsTable(view.trials);
    assert.doesNotMatch(html, /approved|style=|color/i, view.address);
  }
});
