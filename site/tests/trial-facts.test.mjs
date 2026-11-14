// The site's wording for trial facts, checked against openspec trial-facts and
// site-publishing: codes are worded here, numbers are the registry's, and no wording
// says how a trial turned out or that it is open to join.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  TRIAL_STATE_WORDS,
  assertNoOutcomeVerdict,
  comparisonText,
  designText,
  foldLabel,
  measureLead,
  groupValueText,
  isPaperMatch,
  measureText,
  orderTrials,
  participantsText,
  plainFacts,
  resultTable,
  sponsorText,
  studiedText,
  trialDates,
  trialHeading,
  unlabelledTrialCodes,
  withResults,
} from "../src/lib/trial-facts.ts";
import { measureWords } from "../src/lib/readings.ts";
import { recordBrief } from "../src/lib/record-brief.ts";

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

test("a paper is not a registry record", () => {
  assert.equal(isPaperMatch({ source_name: "crossref" }), true);
  assert.equal(isPaperMatch({ source_name: "clinicaltrials.gov" }), false);
});

// Openspec site-publishing, change plain-trial-entries: an entry in plain words.
const plain = (text) => text.replace(/\u00a0/g, " ");
const none = { finished: null, posted: null };

test("Scenario: Trial with a named comparison", () => {
  const sham = trial("NCT1", [], {
    facts: facts({ participants: { count: 135, basis: "actual" }, comparators: ["sham", "no_treatment"] }),
  });
  assert.deepEqual(trialHeading(sham, "device"), {
    text: "135 people, compared with a sham device and with no treatment",
    isTitle: false,
  });
  // A sham is a procedure when the treatment is not a device.
  assert.equal(trialHeading(sham, "drug").text, "135 people, compared with a sham procedure and with no treatment");
});

test("Scenario: Trial whose record names no comparison", () => {
  const bare = trial("NCT1", [], { facts: facts({ participants: { count: 34, basis: "actual" }, comparators: [] }) });
  assert.equal(trialHeading(bare, "device").text, "34 people");
});

test("Scenario: Planned size", () => {
  const planned = trial("NCT1", [], { facts: facts({ participants: { count: 400, basis: "planned" } }) });
  assert.equal(trialHeading(planned, "drug").text, "400 people planned, compared with a placebo");
});

test("Scenario: Trial that states no size", () => {
  const unsized = trial("NCT1", [], { title: "A synthetic study", facts: facts({ participants: null }) });
  assert.deepEqual(trialHeading(unsized, "drug"), { text: "A synthetic study", isTitle: true });
});

test("Scenario: Randomised, quadruple-blind, completed, results posted", () => {
  const done = trial("NCT1", ["not_applicable"], {
    facts: facts({ allocation: "randomised", masking: "quadruple", results: { outcomes: [], outcomes_total: 1 } }),
  });
  const events = [
    { type: "trial_status_change", trial_state: "completed", trial_id: "NCT1", event_date: "2023-03-05" },
    { type: "trial_results_posted", trial_id: "NCT1", event_date: "2023-10-05" },
    { type: "trial_results_posted", trial_id: "NCT1", event_date: "2026-06-30" },
    { type: "trial_results_posted", trial_id: "NCT2", event_date: "2027-01-01" },
  ];
  const dates = trialDates(events, "NCT1");
  assert.deepEqual(dates, { finished: "2023-03-05", posted: "2026-06-30" });
  assert.deepEqual(plainFacts(done, dates).map(plain), [
    "Assigned at random",
    "Blinded",
    "Finished 5 Mar 2023",
    "Results posted 30 Jun 2026",
  ]);
  // The level of blinding is the registry's term, kept for the fold.
  assert.equal(designText(done.facts), "Randomised, quadruple-blind, compared with placebo");
  assert.equal(foldLabel(done), "Who took part, who ran it, and the posted results");
});

test("Scenario: Open-label trial", () => {
  const open = trial("NCT1", [], { facts: facts({ allocation: null, masking: "none" }) });
  assert.deepEqual(plainFacts(open, none), ["Open label: everyone knew what they had", "Finished"]);
});

test("Scenario: Trial under way", () => {
  const running = trial("NCT1", ["phase_3"], { state: "under_way", facts: facts({ allocation: "randomised", masking: "double" }) });
  const said = plainFacts(running, { finished: "2020-01-01", posted: null });
  // No finishing date for a trial that has not finished, and never "recruiting".
  assert.deepEqual(said, ["Assigned at random", "Blinded", "Under way", "Phase 3"]);
  assert.doesNotMatch(said.join(" "), /recruit|open to/i);
});

test("Scenario: Design the record does not state", () => {
  const unstated = trial("NCT1", [], { facts: facts({ allocation: null, masking: null }) });
  assert.deepEqual(plainFacts(unstated, none), ["Finished"]);
  assert.equal(foldLabel(trial("NCT2", [])), "More from its record");
});

const measured = (readings) =>
  trial("NCT1", [], {
    facts: facts({
      participants: { count: 135, basis: "actual" },
      primary_outcomes: [{ measure: "Change in Synthetic Severity Score", time_frame: "Baseline and week 4" }],
      primary_outcomes_total: 1,
    }),
    readings,
  });
const kindReading = { kind: "measure", outcome: 0, field: "measure", words: "Synthetic Severity Score", number: null, unit: null, code: "symptom_score", confidence: 0.92, read_on: "2026-11-13" };
const timeReading = { kind: "follow_up", outcome: 0, field: "time_frame", words: "week 4", number: 4, unit: "weeks", code: null, confidence: 0.95, read_on: "2026-11-13" };

test("Scenario: Symptom score followed for four weeks", () => {
  const words = measureWords(measured([kindReading, timeReading]), 0);
  assert.equal(plain(`${words.phrase}${words.over}`), "The change in a symptom score over 4 weeks");
  assert.equal(words.confidence, 0.92);
});

test("Scenario: Measure of a trial that has not ended", () => {
  // Past tense only once a trial has ended.
  assert.equal(measureLead(trial("NCT1", [])), "It measured");
  assert.equal(measureLead(trial("NCT1", [], { state: "terminated" })), "It measured");
  assert.equal(measureLead(trial("NCT1", [], { state: "under_way" })), "It sets out to measure");
  assert.equal(measureLead(trial("NCT1", [], { state: "not_started" })), "It sets out to measure");
  // A trial under way that has posted results has measured something.
  const posted = trial("NCT1", [], { state: "under_way", facts: facts({ results: { outcomes: [], outcomes_total: 1 } }) });
  assert.equal(measureLead(posted), "It measured");
});

test("Scenario: Time until an event, followed for years", () => {
  const followed = measured([{ ...kindReading, code: "survival" }, { ...timeReading, number: 4, unit: "years" }]);
  const words = measureWords(followed, 0);
  assert.equal(
    plain(`${words.phrase}${words.over}`),
    "How long until an event, such as the illness getting worse or death, followed for 4 years",
  );
});

test("Scenario: Same wording as the record in brief", () => {
  const subject = measured([kindReading, timeReading]);
  const words = measureWords(subject, 0);
  const brief = recordBrief({ approach: "device", evidence_stage: null, status: { code: "trial_registered" }, events: [], trials: [subject] }, null);
  const answer = brief.flatMap((group) => group.rows).find((row) => row.code === "measure").answer;
  assert.equal(answer, `${words.phrase}${words.over}`);
});

test("Scenario: No usable reading", () => {
  assert.equal(measureWords(measured([]), 0), null);
  assert.equal(measureWords(measured([{ ...kindReading, confidence: 0.3 }]), 0), null);
  assert.equal(measureWords(measured([{ ...kindReading, code: "other" }]), 0), null);
  // A follow-up alone says nothing of what was measured.
  assert.equal(measureWords(measured([timeReading]), 0), null);
});

const outcome = (extra = {}) => ({
  title: "Change in Synthetic Severity Score",
  time_frame: "Baseline and week 4",
  measure: "mean",
  unit: "score on a scale",
  spread_kind: "Standard Deviation",
  rows: 1,
  groups: [
    { title: "Active", analysed: "39", value: "-7.13", spread: "1.1", lower: null, upper: null },
    { title: "Sham", analysed: "39", value: "-2.13", spread: "0.32", lower: null, upper: null },
    { title: "Waitlist", analysed: "39", value: "-2.26", spread: "0.34", lower: null, upper: null },
  ],
  comparisons: [],
  ...extra,
});

test("Scenario: Three groups with a mean change", () => {
  const table = resultTable(outcome());
  assert.equal(table.statistic, "Mean");
  assert.equal(table.spread, "Standard Deviation");
  assert.deepEqual(table.rows[0], { group: "Active", value: "-7.13", spread: "1.1", analysed: "39" });
  assert.equal(table.rows.length, 3);
});

test("Scenario: Measure that is a change", () => {
  assert.equal(resultTable(outcome()).fall, true);
  // Not said of a measure that is not a change, or when no value is below zero.
  assert.equal(resultTable(outcome({ title: "Synthetic Severity Score" })).fall, false);
  const rising = outcome();
  for (const group of rising.groups) group.value = group.value.slice(1);
  assert.equal(resultTable(rising).fall, false);
});

test("Scenario: Outcome posted in several rows", () => {
  assert.equal(resultTable(outcome({ rows: 4, groups: [] })), null);
});

test("Scenario: Fold with no results", () => {
  const planning = trial("NCT1", [], {
    facts: facts({ primary_outcomes: [{ measure: "Synthetic score", time_frame: null }], primary_outcomes_total: 1 }),
  });
  assert.equal(foldLabel(planning), "Who took part, who ran it, and what it planned to measure");
  assert.doesNotMatch(foldLabel(planning), /results/);
});

test("plain wording says nothing of how a trial turned out", () => {
  assert.throws(() => assertNoOutcomeVerdict(["Results were significant"]), /Verdict wording/);
});
