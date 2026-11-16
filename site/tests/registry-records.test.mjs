import assert from "node:assert/strict";
import { test } from "node:test";

import { NO_PHASE_GIVEN, groupByReading, notCounted, phaseOf, sizeOf, stateOf } from "../src/lib/registry-records.ts";
import { possibleMatchNote } from "../src/lib/confidence.ts";
import { READING_HEADINGS, UNREAD_HEADING } from "../src/lib/confidence.ts";

const match = (external_id, reading, record = null) => ({
  source_name: "clinicaltrials.gov",
  external_id,
  url: `https://clinicaltrials.gov/study/${external_id}`,
  score: 0.7,
  state: "candidate",
  reading,
  decided_by: null,
  summary: null,
  record,
});

test("records are grouped by reading, closest to the claim first, each in the order given", () => {
  const groups = groupByReading([
    match("NCT1", "other_indication"),
    match("NCT2", "match"),
    match("NCT3", null),
    match("NCT4", "other_indication"),
  ]);

  assert.deepEqual(
    groups.map((group) => [group.reading, group.matches.map((m) => m.external_id)]),
    [
      ["match", ["NCT2"]],
      ["other_indication", ["NCT1", "NCT4"]],
      [null, ["NCT3"]],
    ],
  );
  assert.equal(groups[2].heading, UNREAD_HEADING);
});

test("a record's phase and state are in the site's words, and a missing phase says so", () => {
  const record = { title: "T", conditions: [], interventions: [], phases: [], state: "under_way" };
  assert.equal(phaseOf(record), NO_PHASE_GIVEN);
  assert.equal(phaseOf({ ...record, phases: ["phase_1", "phase_2"] }), "Phase 1/Phase 2");
  assert.equal(stateOf(record), "Under way");
});

test("no reading heading is a verdict or says a trial is open to join", () => {
  const words = [...Object.values(READING_HEADINGS), UNREAD_HEADING, notCounted(0.8), notCounted(null), possibleMatchNote(0.78)].join(" ");
  assert.doesNotMatch(words, /dead|abandoned|works|failed|cure|proven|recruit|join|eligib/i);
});

test("a possible record's size is in the trials table's words, and the rule names its score", () => {
  const record = { title: "T", conditions: [], interventions: [], phases: [], state: "under_way" };
  assert.equal(sizeOf({ ...record, participants: { count: 780, basis: "planned" } }), "780 people planned");
  assert.equal(sizeOf({ ...record, participants: { count: 1, basis: "actual" } }), "1 person");
  assert.equal(sizeOf(record), null);
  assert.match(notCounted(0.8), /its match is 80% or more\./);
  assert.match(notCounted(null), /only once a person confirms it\./);
});
