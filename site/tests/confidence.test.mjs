import assert from "node:assert/strict";
import { test } from "node:test";

import { bandOf, confidenceLabel, readingOf } from "../src/lib/confidence.ts";

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
  assert.match(readingOf(null), /before the condition/);
});

test("no confidence wording is a verdict", () => {
  const words = [0, 0.5, 0.8].map(bandOf).join(" ") + readingOf("match") + readingOf("not_a_match");
  assert.doesNotMatch(words, /dead|abandoned|works|failed|cure|proven/i);
});
