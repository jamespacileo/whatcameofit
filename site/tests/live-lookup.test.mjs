// The words a live lookup answer is shown in. Pure functions, synthetic answers.
import assert from "node:assert/strict";
import { test } from "node:test";
import { LIVE, describeAnswer, refusalMessage } from "../src/lib/live-lookup.mjs";
import { assertNeutral } from "../src/lib/status.ts";

const candidate = (id, score, more = {}) => ({
  id,
  url: `https://clinicaltrials.gov/study/${id}`,
  score,
  answer: score >= 0.5 ? "match" : "other_indication",
  title: `Study ${id}`,
  conditions: ["Tooth Agenesis"],
  interventions: ["EX-1"],
  phases: ["PHASE2", "PHASE3"],
  state: "ACTIVE_NOT_RECRUITING",
  ...more,
});
const answer = (more = {}) => ({
  about_a_treatment: true,
  gist: "An antibody was reported to regrow missing teeth.",
  treatment: "EX-1",
  condition: "tooth agenesis",
  names: ["EX-1"],
  known_names: [],
  tracked: [],
  candidates: [],
  unscored: 0,
  ...more,
});

test("Scenario: Reader sees an automatic answer", () => {
  const shown = describeAnswer(
    answer({ candidates: [candidate("NCT00000001", 0.97), candidate("NCT00000002", 0.02), candidate("NCT00000003", 0.01)] }),
  );

  // The marking comes first and says what the answer is not.
  assert.equal(shown.marked, LIVE.marked);
  assert.match(shown.marked, /automatic/i);
  assert.match(shown.marked, /not been checked by a person/i);
  assert.equal(shown.lead, "This appears to report EX-1 for tooth agenesis.");
  assert.deepEqual(shown.likely, [
    {
      title: "Study NCT00000001",
      url: "https://clinicaltrials.gov/study/NCT00000001",
      detail: "Phase 2/Phase 3 · active, not recruiting · NCT00000001",
    },
  ]);
  assert.equal(shown.rest, "2 other records were found and read as not being trials of this treatment for this condition.");
  // The standing notice about trials is part of every answer.
  assert.ok(shown.notices.some((notice) => /not a treatment option/.test(notice)));
});

test("a trial with no phase, and names the model added, are said plainly", () => {
  const shown = describeAnswer(
    answer({ known_names: ["TRG-035"], candidates: [candidate("NCT00000001", 0.9, { phases: ["NA"], state: null })] }),
  );

  assert.equal(shown.likely[0].detail, "No phase · NCT00000001");
  assert.equal(shown.searchedAlso, "Also searched under a name the article does not give: TRG-035.");
});

test("no record found is not worded as no trial existing", () => {
  const shown = describeAnswer(answer());

  assert.deepEqual(shown.likely, []);
  assert.equal(shown.none, LIVE.none);
  assert.match(shown.none, /not evidence that no trial exists/);
});

test("a tracked claim is offered first, and text about no treatment is said to be so", () => {
  const tracked = [{ slug: "tooth-regrowth-ex1", headline: "Antibody regrows teeth", page: "/tooth-regrowth-ex1" }];

  assert.deepEqual(describeAnswer(answer({ tracked })).tracked, tracked);
  const none = describeAnswer(answer({ about_a_treatment: false, treatment: null, condition: null }));
  assert.deepEqual([none.lead, none.likely, none.none], [LIVE.notATreatment, [], null]);
});

test("every refusal has words, and an unknown one falls back", () => {
  for (const code of ["unreadable_robots", "unreadable", "post", "short", "busy", "too_long", "not_set_up", "failed", "address"]) {
    assert.ok(refusalMessage(code).length > 20, code);
  }
  assert.equal(refusalMessage("something-new"), refusalMessage("failed"));
  assert.match(refusalMessage("unreadable_robots"), /does not allow/);
});

test("no wording judges a claim", () => {
  const all = [
    ...Object.values(LIVE),
    ...["unreadable_robots", "unreadable", "post", "short", "busy", "too_long", "not_set_up", "failed", "address"].map(refusalMessage),
  ];
  assertNeutral(all);
});
