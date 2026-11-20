import assert from "node:assert/strict";
import { test } from "node:test";
import { CARD_NOTICE, clip, shareSentence } from "../src/lib/card.ts";
import { assertNeutral } from "../src/lib/status.ts";

test("a long title ends at a word with an ellipsis", () => {
  const long = "word ".repeat(60).trim();
  const cut = clip(long, 150);
  assert.ok(cut.length <= 151);
  assert.match(cut, /word…$/);
  assert.equal(clip("short", 150), "short");
});

test("the card's own words are held to the verdict rule", () => {
  // The card module checks its fixed strings when it loads; this is the check it runs.
  assert.doesNotThrow(() => assertNeutral([CARD_NOTICE, "Status now"]));
  assert.throws(() => assertNeutral(["Status now", "Debunked"]), /Verdict wording/);
});

test("the sentence to copy is dated and carries the page's address", () => {
  const sentence = shareSentence("Ambroxol for dementia.", "Phase 2 trial", "2026-11-11T09:00:00Z", "https://example.org/ambroxol--dementia");
  assert.equal(
    sentence,
    "Ambroxol for dementia. Status when checked in Nov 2026: Phase 2 trial. Not medical advice. https://example.org/ambroxol--dementia",
  );
});
