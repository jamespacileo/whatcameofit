// The site's wording for trial facts, checked against openspec trial-facts and
// site-publishing: codes are worded here, numbers are the registry's, and no wording
// says how a trial turned out or that it is open to join.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  TRIAL_STATE_WORDS,
  assertNoOutcomeVerdict,
  comparisonText,
  countTrials,
  designText,
  groupValueText,
  isPaperMatch,
  largestText,
  measureText,
  orderTrials,
  participantsText,
  sponsorText,
  studiedText,
  trialCountText,
  unlabelledTrialCodes,
  withResults,
} from "../src/lib/trial-facts.ts";

const facts = (extra = {}) => ({
  study_kind: "interventional",
  participants: { count: 83, basis: "actual" },
  allocation: "randomised",
  masking: "double",
  comparators: ["placebo"],
  healthy_volunteers: false,
  age_groups: ["adult"],
  sponsor: { name: "Synthetic Institute", kind: "other" },
  primary_outcomes: [],
  primary_outcomes_total: 0,
  why_stopped: null,
  results: null,
  ...extra,
});

const trial = (id, phases, extra = {}) => ({
  trial_id: id,
  source_name: "clinicaltrials.gov",
  url: `https://registry.example/${id}`,
  title: null,
  phases,
  state: "completed",
  facts_as_of: null,
  facts: null,
  ...extra,
});

test("Scenario: Completed trial and trial not yet started", () => {
  assert.equal(participantsText(facts()), "83 participants enrolled");
  assert.equal(
    participantsText(facts({ participants: { count: 1200, basis: "planned" } })),
    "1,200 participants planned",
  );
  assert.equal(participantsText(facts({ participants: null })), null);
});

test("design is worded from its codes, and a single-arm trial says nothing", () => {
  assert.equal(designText(facts()), "Randomised, double-blind, compared with placebo");
  assert.equal(
    designText(facts({ allocation: null, masking: "none", comparators: ["sham", "active"] })),
    "Open label, compared with a sham procedure and another treatment",
  );
  assert.equal(designText(facts({ allocation: null, masking: null, comparators: [] })), null);
});

test("who was studied and who ran it; a person is named by kind only", () => {
  assert.equal(
    studiedText(facts({ healthy_volunteers: true, age_groups: ["adult", "older_adult"] })),
    "Healthy volunteers; Adults and older adults",
  );
  assert.equal(studiedText(facts({ age_groups: [] })), null);
  assert.equal(
    sponsorText(facts()),
    "Synthetic Institute (university, hospital or other body)",
  );
  assert.equal(
    sponsorText(facts({ sponsor: { name: null, kind: "individual" } })),
    "An individual researcher",
  );
});

test("posted numbers are shown as the registry wrote them", () => {
  const outcome = { spread_kind: "Standard Deviation" };
  const group = { title: "Placebo", analysed: "10", value: "3.4", spread: "1.1", lower: null, upper: null };
  assert.equal(groupValueText(group, outcome), "3.4 (Standard Deviation 1.1)");
  assert.equal(
    groupValueText({ ...group, value: "33", spread: null, lower: "22", upper: "47" }, { spread_kind: "Inter-Quartile Range" }),
    "33 (Inter-Quartile Range 22 to 47)",
  );
  assert.equal(groupValueText({ ...group, spread: null }, { spread_kind: null }), "3.4");
});

test("the kind of measure is named with its unit, once", () => {
  assert.equal(measureText({ measure: "median", unit: "score on a scale" }), "Median, score on a scale");
  assert.equal(measureText({ measure: "count_of_participants", unit: "Participants" }), "Number of participants");
  assert.equal(measureText({ measure: null, unit: null }), null);
});

test("Scenario: Posted comparison with a p value", () => {
  const said = comparisonText({ groups: ["A", "B"], p_value: "0.03", method: "t-test, 2 sided", test: "superiority" });
  assert.equal(said, "p = 0.03, t-test, 2 sided (superiority test)");
  assert.equal(comparisonText({ groups: [], p_value: "<0.001", method: "Log Rank", test: null }), "p < 0.001, Log Rank");
  assert.equal(
    comparisonText({ groups: [], p_value: null, method: null, test: null }),
    "Comparison posted with no p value",
  );
  // Whatever the number, the site adds no word on what it means.
  assert.doesNotMatch(said, /met|missed|significant|success|fail/i);
});

test("Scenario: Wording with a verdict", () => {
  assert.throws(() => assertNoOutcomeVerdict(["A successful trial"]), /"A successful trial"/);
  assert.throws(() => assertNoOutcomeVerdict(["Recruiting now"]), /Recruiting/);
  assert.doesNotThrow(() => assertNoOutcomeVerdict(Object.values(TRIAL_STATE_WORDS)));
  // A trial the registry shows as recruiting is worded as under way.
  assert.equal(TRIAL_STATE_WORDS.under_way, "Under way");
});

test("Scenario: Fact code without site wording", () => {
  const unknown = trial("NCT1", ["phase_2"], { facts: facts({ masking: "sextuple" }) });
  assert.deepEqual(unlabelledTrialCodes([unknown]), ["masking: sextuple"]);
  assert.deepEqual(unlabelledTrialCodes([trial("NCT2", ["phase_1"], { facts: facts() })]), []);
  assert.deepEqual(unlabelledTrialCodes([trial("NCT3", ["phase_9"], { state: "paused" })]), [
    "phase: phase_9",
    "state: paused",
  ]);
});

test("trials are ordered furthest phase first, then posted results, then size, then identifier", () => {
  const results = { outcomes: [], outcomes_total: 1 };
  const ordered = orderTrials([
    trial("NCT3", ["phase_1"]),
    trial("NCT2", ["phase_2"], { facts: facts({ participants: { count: 40, basis: "actual" } }) }),
    trial("NCT1", ["phase_2"], { facts: facts() }),
    trial("NCT5", ["phase_2"], { facts: facts({ participants: { count: 12, basis: "actual" }, results }) }),
    trial("NCT4", ["phase_2", "phase_3"]),
    trial("NCT0", []),
  ]);
  assert.deepEqual(
    ordered.map((entry) => entry.trial_id),
    ["NCT4", "NCT5", "NCT1", "NCT2", "NCT3", "NCT0"],
  );
  assert.equal(withResults(ordered), 1);
});

test("Scenario: Three trials, the largest of 1,200", () => {
  const claim = {
    trials: [
      trial("NCT1", ["phase_1"], { facts: facts({ participants: { count: 30, basis: "actual" } }) }),
      trial("NCT2", ["phase_3"], { facts: facts({ participants: { count: 1200, basis: "actual" } }) }),
      trial("NCT3", ["phase_2"], { facts: facts() }),
    ],
  };
  // A count and the largest: never 30 + 1,200 + 83.
  const tally = countTrials(claim);
  assert.equal(trialCountText(tally), "3 on record");
  assert.equal(largestText(tally), "The largest, 1,200 participants enrolled");
  assert.equal(largestText(countTrials({ trials: claim.trials.slice(0, 1) })), "30 participants enrolled");
});

test("Scenario: Trials that state no number", () => {
  const claim = { trials: [trial("NCT1", ["phase_1"]), trial("NCT2", ["phase_1"])] };
  assert.equal(trialCountText(countTrials(claim)), "2 on record");
  assert.equal(largestText(countTrials(claim)), null);
  assert.equal(countTrials({}).count, 0);
});

test("a paper is not a registry record", () => {
  assert.equal(isPaperMatch({ source_name: "crossref" }), true);
  assert.equal(isPaperMatch({ source_name: "clinicaltrials.gov" }), false);
});
