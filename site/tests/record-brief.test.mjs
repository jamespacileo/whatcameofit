// "The record in brief", checked against openspec site-publishing (change
// claim-at-a-glance): fixed questions in fixed places, answers read from the records,
// each with its source, and no result value anywhere. Synthetic records only.
import assert from "node:assert/strict";
import { test } from "node:test";

import { assertNeutral } from "../src/lib/status.ts";
import {
  DEFINITIONS,
  NONE,
  briefNote,
  digestBridge,
  recordBrief,
  sourceWords,
} from "../src/lib/record-brief.ts";

const facts = (extra = {}) => ({
  study_kind: "interventional",
  participants: null,
  allocation: null,
  masking: null,
  comparators: [],
  healthy_volunteers: false,
  age_groups: ["adult"],
  sponsor: { name: "Synthetic Institute", kind: "other" },
  primary_outcomes: [],
  primary_outcomes_total: 0,
  why_stopped: null,
  results: null,
  ...extra,
});

const trial = (id, extra = {}) => ({
  trial_id: id,
  source_name: "clinicaltrials.gov",
  url: `https://registry.example/${id}`,
  title: null,
  phases: [],
  state: "completed",
  facts_as_of: "2026-11-13T09:00:00Z",
  facts: facts(),
  ...extra,
});

const event = (type, extra = {}) => ({
  id: 1,
  type,
  event_date: "2023-03-05",
  date_basis: null,
  summary: "",
  source_name: "clinicaltrials.gov",
  source_url: "https://registry.example/record",
  trial_id: null,
  trial_phases: [],
  trial_state: null,
  regulatory_outcome: null,
  ...extra,
});

const claim = (extra = {}) => ({
  slug: "synthetic",
  approach: "device",
  evidence_stage: "early_human",
  first_reported_date: "2026-11-12",
  status: { code: "trial_registered", overlay_years: null, updated_at: null, explained_by: [] },
  events: [],
  trials: [],
  ...extra,
});

const posted = { outcomes: [], outcomes_total: 1 };

// Three finished trials of a device: the largest randomised against a sham, with a
// main measure a model has read; all three with results posted.
const device = claim({
  trials: [
    trial("NCT1", {
      facts: facts({
        participants: { count: 135, basis: "actual" },
        allocation: "randomised",
        masking: "quadruple",
        comparators: ["sham", "no_treatment"],
        primary_outcomes: [{ measure: "Change in Synthetic Severity Score", time_frame: "Baseline and week 4" }],
        primary_outcomes_total: 1,
        results: posted,
      }),
      readings: [
        { kind: "measure", outcome: 0, field: "measure", words: "Synthetic Severity Score", number: null, unit: null, code: "symptom_score", confidence: 0.92, read_on: "2026-11-13" },
        { kind: "follow_up", outcome: 0, field: "time_frame", words: "week 4", number: 4, unit: "weeks", code: null, confidence: 0.95, read_on: "2026-11-13" },
      ],
    }),
    trial("NCT2", {
      facts: facts({ participants: { count: 34, basis: "actual" }, allocation: "randomised", masking: "triple", results: posted }),
    }),
    trial("NCT3", { facts: facts({ participants: { count: 31, basis: "actual" }, masking: "none", results: posted }) }),
  ],
  events: [
    event("trial_status_change", { trial_id: "NCT1", trial_state: "completed", event_date: "2023-03-05" }),
    event("trial_status_change", { trial_id: "NCT2", trial_state: "completed", event_date: "2022-04-27" }),
    event("trial_results_posted", { trial_id: "NCT2", event_date: "2023-10-05" }),
    event("trial_results_posted", { trial_id: "NCT1", event_date: "2026-06-30" }),
  ],
});

const rows = (groups) => groups.flatMap((group) => group.rows);
const rowOf = (groups, code) => rows(groups).find((row) => row.code === code);
const plain = (text) => text.replace(/ /g, " ");

test("Scenario: Claim with trials", () => {
  const tested = rowOf(recordBrief(device, null), "tested");
  assert.equal(tested.answer, "In 3 trials. 135 people in the largest");
  assert.doesNotMatch(tested.answer, /^Yes/);
  // The sizes are listed, never added together.
  assert.deepEqual(tested.opened, [
    "The other two trials enrolled 34 and 31 people.",
    "The largest number is people who took part, not a planned size.",
  ]);
  assert.equal(tested.link.href, "#trials");
});

test("Scenario: Three trials, the largest of 1,200", () => {
  const large = claim({
    trials: [
      trial("NCT1", { facts: facts({ participants: { count: 30, basis: "actual" } }) }),
      trial("NCT2", { facts: facts({ participants: { count: 1200, basis: "planned" } }) }),
      trial("NCT3", { facts: facts({ participants: { count: 83, basis: "actual" } }) }),
    ],
  });
  const tested = rowOf(recordBrief(large, null), "tested");
  // A count and the largest: never 30 + 1,200 + 83.
  assert.equal(tested.answer, "In 3 trials. 1,200 people in the largest");
  assert.match(tested.opened.join(" "), /planned size, not people who took part/);
});

test("Scenario: Trials that state no number", () => {
  const unsized = claim({ trials: [trial("NCT1"), trial("NCT2")] });
  const tested = rowOf(recordBrief(unsized, null), "tested");
  assert.equal(tested.answer, "In 2 trials");
  // With no largest trial there is nothing to ask about a measure.
  assert.equal(rowOf(recordBrief(unsized, null), "measure"), undefined);
});

test("Scenario: Trial with no stated enrolment", () => {
  const one = claim({ trials: [trial("NCT1")] });
  assert.equal(rowOf(recordBrief(one, null), "tested").answer, "In 1 trial");
});

test("Scenario: Many trials", () => {
  const sizes = [640, 18, 90, 120, 44, 1204, 60, 75, 300, 210, 33, 150];
  const many = claim({
    trials: sizes.map((count, index) => trial(`NCT${index}`, { facts: facts({ participants: { count, basis: "actual" } }) })),
  });
  const tested = rowOf(recordBrief(many, null), "tested");
  assert.equal(tested.answer, "In 12 trials. 1,204 people in the largest");
  assert.equal(tested.opened[0], "The others enrolled between 18 and 640 people.");
});

test("Scenario: Comparison group", () => {
  const comparison = rowOf(recordBrief(device, null), "comparison");
  assert.equal(comparison.question, "Compared with a dummy device?");
  // Counts the records that name one; never "1 of 3 trials", which would say the
  // other two had no comparison.
  assert.equal(comparison.answer, "One record names a dummy device");
  assert.doesNotMatch(comparison.answer, /of 3/);
  assert.match(comparison.opened[0], /randomised, quadruple-blind, compared with a sham procedure and no treatment/);
  assert.ok(comparison.opened.includes(DEFINITIONS.sham));
  assert.ok(comparison.opened.includes("The other two records name no such comparison."));
  assert.deepEqual(comparison.source.records, [{ label: "NCT1", url: "https://registry.example/NCT1" }]);
  // A drug is compared with a placebo.
  const drug = claim({ approach: "drug", trials: [trial("NCT1", { facts: facts({ allocation: "randomised" }) })] });
  const none = rowOf(recordBrief(drug, null), "comparison");
  assert.equal(none.question, "Compared with a placebo?");
  assert.equal(none.answer, "No record names one");
});

test("Scenario: What the largest trial measured", () => {
  const measure = rowOf(recordBrief(device, null), "measure");
  // "Changed" because the registry's title names a change: read by rule, not by the model.
  assert.equal(plain(measure.answer), "The change in a symptom score over 4 weeks");
  assert.equal(
    measure.opened[0],
    "The registry names the measure “Change in Synthetic Severity Score” and gives its timing as “Baseline and week 4”.",
  );
  assert.equal(measure.source.how, "model");
  assert.equal(measure.source.confidence, 0.92);
  assert.equal(measure.link.href, "#trial-NCT1");
  assert.equal(measure.link.text, "See this trial's posted results");
});

test("Scenario: Answer read by a model", () => {
  const words = sourceWords(rowOf(recordBrief(device, null), "measure").source);
  assert.match(words.before, /A model read the plain wording from the quoted words, and a rule checked that they are in $/);
  assert.match(plain(words.after), /How sure the reading is: very likely · 92%\. Record read 13 Nov 2026\.$/);
});

test("Scenario: Reading the model is certain of", () => {
  const certain = structuredClone(device);
  for (const reading of certain.trials[0].readings) reading.confidence = 1;
  const words = sourceWords(rowOf(recordBrief(certain, null), "measure").source);
  // The figure is the model's own: never shown as certain.
  assert.match(words.after, /very likely · 99%/);
  assert.doesNotMatch(words.after, /100%/);
});

test("the kinds of measure are worded exactly", () => {
  const worded = (code, title) => {
    const subject = structuredClone(device);
    subject.trials[0].facts.primary_outcomes[0].measure = title;
    subject.trials[0].readings[0].code = code;
    subject.trials[0].readings.pop();
    return rowOf(recordBrief(subject, null), "measure").answer;
  };
  // The event can be death, so the phrase does not name a relapse alone.
  assert.equal(worded("survival", "Progression-Free Survival"), "How long until an event, such as the illness getting worse or death");
  assert.equal(worded("physical_test", "Percent Change from Baseline in the 10-Metre Walk Test"), "The change in a test of what the body can do, such as walking");
  assert.equal(worded("physical_test", "10-Metre Walk Test"), "A test of what the body can do, such as walking");
});

test("Scenario: Answer read directly", () => {
  const words = sourceWords(rowOf(recordBrief(device, null), "comparison").source);
  assert.equal(words.before, "Read directly from ");
  assert.equal(plain(words.after), ". Record read 13 Nov 2026.");
  const several = sourceWords(rowOf(recordBrief(device, null), "tested").source);
  assert.equal(several.before, "Read directly from 3 ClinicalTrials.gov records");
});

test("Scenario: Measure with no reading", () => {
  const unread = structuredClone(device);
  unread.trials[0].readings = [];
  const measure = rowOf(recordBrief(unread, null), "measure");
  assert.equal(measure.answer, "“Change in Synthetic Severity Score”");
  assert.deepEqual(measure.opened, [DEFINITIONS.registry_words]);
  assert.equal(measure.source.how, "direct");
  // A reading too unsure to use, or of a kind with no phrase, falls back the same way.
  const unsure = structuredClone(device);
  unsure.trials[0].readings[0].confidence = 0.3;
  assert.equal(rowOf(recordBrief(unsure, null), "measure").answer, "“Change in Synthetic Severity Score”");
  const other = structuredClone(device);
  other.trials[0].readings[0].code = "other";
  assert.equal(rowOf(recordBrief(other, null), "measure").answer, "“Change in Synthetic Severity Score”");
});

test("Scenario: Results posted", () => {
  const results = rowOf(recordBrief(device, null), "results");
  assert.equal(plain(results.answer), "By all 3 trials. The latest on 30 Jun 2026");
  // The link is shown without opening the answer.
  assert.deepEqual(results.shown, { href: "#trials", text: "See the posted results" });
  assert.deepEqual(results.opened, [DEFINITIONS.posted]);
});

test("Scenario: No trial under way", () => {
  const underWay = rowOf(recordBrief(device, null), "under_way");
  assert.equal(plain(underWay.answer), `${NONE}. The last finished on 5 Mar 2023`);
});

test("Scenario: A trial under way", () => {
  const running = structuredClone(device);
  running.trials[1].state = "under_way";
  running.trials[2].state = "under_way";
  const underWay = rowOf(recordBrief(running, null), "under_way");
  assert.equal(underWay.answer, "Two under way");
  const said = [underWay.answer, ...underWay.opened].join(" ");
  assert.doesNotMatch(said, /recruit/i);
  assert.match(said, /does not say a trial is open to new participants/);
});

test("Scenario: Approved claim", () => {
  const approved = claim({
    status: { code: "approved", overlay_years: null, updated_at: null, explained_by: [] },
    events: [event("regulatory_decision", { regulatory_outcome: "approved", source_name: "FDA", source_url: "https://regulator.example/approval", event_date: "2026-10-30" })],
  });
  const row = rowOf(recordBrief(approved, null), "approved");
  // The regulator and the date, and the caution without opening the answer.
  assert.equal(plain(row.answer), "By the FDA on 30 Oct 2026. An approval is not advice to take a treatment");
  assert.equal(row.source.records[0].url, "https://regulator.example/approval");
});

test("Scenario: Approval entered by hand", () => {
  const byHand = claim({
    events: [event("regulatory_decision", { regulatory_outcome: "approved", source_name: "manual entry", event_date: "2024-04-01" })],
  });
  const row = rowOf(recordBrief(byHand, null), "approved");
  assert.equal(plain(row.answer), "On 1 Apr 2024. An approval is not advice to take a treatment");
});

test("Scenario: Claim that is not approved", () => {
  const row = rowOf(recordBrief(device, "2026-11-14T08:00:00Z"), "approved");
  assert.equal(row.answer, NONE);
  assert.equal(row.source.onLabel, "Registries last checked");
});

test("Scenario: Same questions, opposite answers", () => {
  const opposite = structuredClone(device);
  opposite.trials[1].state = "under_way";
  opposite.events.push(event("regulatory_decision", { regulatory_outcome: "approved", source_name: "FDA" }));
  const places = (groups) => groups.map((group) => [group.name, group.rows.map((row) => row.question)]);
  // A question's place never depends on its answer.
  assert.deepEqual(places(recordBrief(device, null)), places(recordBrief(opposite, null)));
  assert.deepEqual(places(recordBrief(device, null)), [
    ["How it was tested", ["Tested in people?", "Compared with a dummy device?", "What did the largest trial measure?"]],
    ["Where the records stand now", ["Results posted to the registry?", "A trial under way?", "Approved by a regulator?"]],
  ]);
});

test("Scenario: Claim with no trial on record", () => {
  const groups = recordBrief(claim({ evidence_stage: "animal", status: { code: "preclinical_only" } }), "2026-11-14T08:00:00Z");
  assert.deepEqual(
    rows(groups).map((row) => [row.question, row.answer]),
    [
      ["Tested in people?", NONE],
      ["What was the first report about?", "A study in animals"],
      ["Approved by a regulator?", NONE],
    ],
  );
  assert.equal(briefNote(groups).startsWith("Three answers read from the records on this page."), true);
});

test("Scenario: Every answer opens to something", () => {
  for (const subject of [device, claim({ evidence_stage: "animal" }), claim({ trials: [trial("NCT1")] })]) {
    for (const row of rows(recordBrief(subject, "2026-11-14T08:00:00Z"))) {
      assert.ok(row.opened.length > 0, `${row.code} opens to nothing`);
      assert.ok(row.source.from || row.source.records.length > 0, `${row.code} names no record`);
    }
  }
});

test("Scenario: Largest trial with posted values", () => {
  const valued = structuredClone(device);
  valued.trials[0].facts.results = {
    outcomes_total: 1,
    outcomes: [{ title: "Change in Synthetic Severity Score", groups: [{ title: "Active", value: "-7.13" }], comparisons: [{ p_value: "<0.02" }] }],
  };
  const said = rows(recordBrief(valued, null))
    .flatMap((row) => [row.answer, ...row.opened])
    .join(" ");
  assert.doesNotMatch(said, /7\.13|0\.02|p\s*[<=]/);
});

test("Scenario: Three trials with no phase", () => {
  assert.equal(digestBridge(device), "3 trials are on record and all have finished. The registry gives none a phase.");
  // The registry's own mark for a trial with no phase counts as none.
  const marked = structuredClone(device);
  for (const entry of marked.trials) entry.phases = ["not_applicable"];
  assert.match(digestBridge(marked), /The registry gives none a phase\.$/);
  const staged = structuredClone(device);
  staged.trials[0].phases = ["phase_2"];
  assert.equal(digestBridge(staged), "3 trials are on record and all have finished.");
  const partly = structuredClone(device);
  partly.trials[2].state = "under_way";
  assert.equal(digestBridge(partly), "3 trials are on record and 2 have finished. The registry gives none a phase.");
});

test("Scenario: Status with a phase", () => {
  const phased = structuredClone(device);
  phased.status.code = "phase_2";
  assert.equal(digestBridge(phased), null);
  assert.equal(digestBridge(claim()), null);
});

test("Scenario: Wording with a verdict", () => {
  // The module's wording passes the check it runs when loaded; a verdict would not.
  assert.throws(() => assertNeutral(["The trial was abandoned"]), /Verdict wording "abandoned"/);
});
