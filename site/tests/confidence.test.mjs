import assert from "node:assert/strict";
import { test } from "node:test";

import { bandOf, confidenceLabel, readingOf, stageReadingNote } from "../src/lib/confidence.ts";

test("scores are worded by band, with the percentage", () => {
  assert.equal(confidenceLabel(0.92), "High match · 92%");
  assert.equal(confidenceLabel(0.8), "High match · 80%");
  assert.equal(confidenceLabel(0.5), "Medium match · 50%");
  assert.equal(confidenceLabel(0.049), "Low match · 5%");
  assert.equal(bandOf(0), "Low match");
});

test("a reading becomes a reason, and an unknown one says how it was scored", () => {
  assert.match(readingOf("match"), /this treatment for this condition/);
  assert.match(readingOf("other_indication"), /different condition/);
  assert.match(readingOf("not_what_is_tested"), /does not test it/);
  assert.match(readingOf(null), /before the condition/);
});

test("no confidence wording is a verdict", () => {
  const words = [0, 0.5, 0.8].map(bandOf).join(" ") + readingOf("match") + readingOf("not_a_match") + readingOf("not_what_is_tested");
  assert.doesNotMatch(words, /dead|abandoned|works|failed|cure|proven/i);
});

test("an unconfirmed stage reading says its score, that it decides nothing, and what else it could be", () => {
  const names = { animal: "Animal study" };
  const note = stageReadingNote({ score: 0.7, also: [{ stage: "animal", score: 0.28 }] }, (code) => names[code] ?? code);
  assert.equal(note, "Low confidence · 70%. Not confirmed, so it does not decide the status. Also read as: animal study, 28%.");
  assert.equal(
    stageReadingNote({ score: 0.9, also: [] }, (code) => code),
    "Low confidence · 90%. Not confirmed, so it does not decide the status.",
  );
  assert.doesNotMatch(note, /dead|abandoned|works|failed|cure|proven/i);
});
