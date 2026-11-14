// What the records add to a report, as sentences on a home page row (openspec
// home-day-by-day). Pure functions over the fixture export (synthetic data).
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import {
  assertRowSentence,
  rowSentences,
  sampleSentences,
  sentencesFor,
} from "../src/lib/row-sentences.ts";

const fixture = JSON.parse(fs.readFileSync(new URL("./fixture-export.json", import.meta.url), "utf8"));
const claim = (slug) => structuredClone(fixture.claims.find((entry) => entry.slug === slug));
// Dates are set with spaces that do not break; the tests read them as plain spaces.
const plain = (texts) => texts.map((text) => text.replaceAll(" ", " "));

test("Scenario: A trial registered long before the report", () => {
  const phase = claim("phase-claim");
  phase.trials = phase.trials.slice(0, 5).map((trial, index) => ({
    ...trial,
    state: index < 3 ? "completed" : "under_way",
    facts: { ...trial.facts, results: index < 2 ? { outcomes: [], outcomes_total: 0 } : null },
  }));
  phase.events = [{ ...phase.events[0], type: "trial_registered", event_date: "2012-05-10" }];
  assert.deepEqual(plain(rowSentences(phase, "2026-11-05")), [
    "The first trial was registered in 2012, 14 years before this report.",
    "5 trials on record, 3 completed, 2 with results posted.",
  ]);
});

test("A trial registered the year before the report is not remarked on", () => {
  const phase = claim("phase-claim");
  phase.trials = [];
  phase.events = [{ ...phase.events[0], type: "trial_registered", event_date: "2025-03-01" }];
  assert.deepEqual(rowSentences(phase, "2026-11-05"), []);
});

test("Scenario: Nothing since the report", () => {
  const quiet = claim("quiet-claim");
  quiet.events = [];
  quiet.status.overlay_years = 9;
  assert.deepEqual(plain(rowSentences(quiet, quiet.articles[0].published_date)), [
    "No record is dated in the 9 years since the first report.",
  ]);
});

test("A claim with a record dated after its first report does not say nothing is dated since", () => {
  // The fixture's quiet claim has a paper from 2020, after its report of 2018.
  const quiet = claim("quiet-claim");
  assert.ok(quiet.events.some((event) => event.event_date > quiet.first_reported_date));
  assert.deepEqual(rowSentences(quiet, "2018-05-01"), []);
});

test("Scenario: An approval", () => {
  const approved = claim("approved-claim");
  const decision = approved.events.find((event) => event.type === "regulatory_decision");
  const [first] = plain(rowSentences(approved, "2017-05-04"));
  assert.ok(first.startsWith(decision.summary.replace(/\.$/, "")), first);
  assert.ok(first.endsWith("Dated 1 Apr 2024."), first);
});

test("Scenario: The order of preference", () => {
  const approved = claim("approved-claim");
  approved.events.push({ ...approved.events[0], id: 99, type: "trial_registered", event_date: "2010-01-01" });
  approved.trials = [claim("phase-claim").trials[0]];
  const all = plain(sentencesFor(approved, "2017-05-04"));
  assert.equal(all.length, 3);
  assert.match(all[0], /Dated 1 Apr 2024\.$/);
  assert.match(all[1], /^The first trial was registered in 2010, 7 years before this report\.$/);
  assert.match(all[2], /^1 trial on record/);
  // A row carries the first two.
  assert.deepEqual(plain(rowSentences(approved, "2017-05-04")), all.slice(0, 2));
});

test("A claim whose export carries no trials says nothing of how many there are", () => {
  const phase = claim("phase-claim");
  delete phase.trials;
  assert.ok(!sentencesFor(phase, "2019-05-03").some((text) => text.includes("on record")));
});

test("Scenario: Wording that judges", () => {
  assert.throws(() => assertRowSentence("trials", "Still 5 trials on record."), /"still".*"trials"/i);
  assert.throws(() => assertRowSentence("trials", "Only 2 with results posted."), /"only"/i);
  assert.throws(() => assertRowSentence("promise", "The promised date was missed."), /promise/);
  assert.throws(() => assertRowSentence("claim", "The work was abandoned."), /claim/);
  assert.throws(() => assertRowSentence("trial", "A trial you can join is registered."), /trial/);
});

test("The wording as written passes its own check", () => {
  const samples = sampleSentences();
  assert.ok(samples.length >= 4);
  for (const [name, text] of samples) assert.doesNotThrow(() => assertRowSentence(name, text));
  // No sentence says a promise was kept, missed or late.
  assert.ok(!samples.some(([, text]) => /kept|missed|late\b/i.test(text)));
});
