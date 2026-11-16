import assert from "node:assert/strict";
import { test } from "node:test";

import { NO_PHASE_GIVEN, groupByReading, standingOf } from "../src/lib/registry-records.ts";
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
  assert.deepEqual(standingOf(record), [NO_PHASE_GIVEN, "Under way"]);
  assert.deepEqual(standingOf({ ...record, phases: ["phase_1", "phase_2"] }), ["Phase 1/Phase 2", "Under way"]);
});

test("no reading heading is a verdict or says a trial is open to join", () => {
  const words = [...Object.values(READING_HEADINGS), UNREAD_HEADING].join(" ");
  assert.doesNotMatch(words, /dead|abandoned|works|failed|cure|proven|recruit|join|eligib/i);
});
