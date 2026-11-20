// The site's own words for a registry's codes, and the rule that they say nothing of how a
// trial turned out. Pure.
import assert from "node:assert/strict";
import { test } from "node:test";
import { TRIAL_STATE_WORDS, assertNoOutcomeVerdict, comparisonText } from "../src/lib/trial-facts.ts";

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
