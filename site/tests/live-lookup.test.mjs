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
  assert.deepEqual(shown.subject, { treatment: "EX-1", condition: "tooth agenesis" });
  assert.deepEqual(shown.likely, [
    {
      title: "Study NCT00000001",
      url: "https://clinicaltrials.gov/study/NCT00000001",
      detail: "Phase 2/Phase 3 · active, not recruiting · NCT00000001",
      phase: "Phase 2/Phase 3",
      state: "active, not recruiting",
      registryId: "NCT00000001",
      why: null,
      confidence: 97,
      confidenceLabel: "97% match confidence",
    },
  ]);
  assert.equal(shown.rest, "2 other records were found and read as not being trials of this treatment for this condition.");
  // The standing notice about trials is part of every answer.
  assert.ok(shown.notices.some((notice) => /not a treatment option/.test(notice)));
});

test("match confidence belongs to each record and is not a treatment rating", () => {
  const shown = describeAnswer(answer({ candidates: [
    candidate("NCT00000001", 0.946),
    candidate("NCT00000002", 0, { agrees: ["stated"] }),
    candidate("NCT00000003", 1),
    candidate("NCT00000004", null, { agrees: ["stated"] }),
    candidate("NCT00000005", 1.5, { agrees: ["stated"] }),
  ] }));
  assert.deepEqual(shown.likely.map(({ confidence, confidenceLabel }) => [confidence, confidenceLabel]), [
    [100, "100% match confidence"],
    [95, "95% match confidence"],
  ]);
  assert.deepEqual(shown.mentioned.map(({ confidence, confidenceLabel }) => [confidence, confidenceLabel]), [
    [0, "0% match confidence"],
    [null, "Match confidence unavailable"],
    [null, "Match confidence unavailable"],
  ]);
  assert.match(LIVE.confidenceMeaning, /not a verified probability/);
  assert.match(LIVE.confidenceMeaning, /treatment effectiveness or trial quality/);
});

test("a trial with no phase, and names the model added, are said plainly", () => {
  const shown = describeAnswer(
    answer({ known_names: ["TRG-035"], candidates: [candidate("NCT00000001", 0.9, { phases: ["NA"], state: null })] }),
  );

  assert.equal(shown.likely[0].detail, "No phase · NCT00000001");
  assert.equal(shown.searchedAlso, "Also searched under a name the article does not give: TRG-035.");
});

test("a record is said to agree with the article only on what was compared", () => {
  const shown = describeAnswer(
    answer({
      details: { trial_name: "REGROW-2", participants: 2539, sponsor: null },
      candidates: [
        candidate("NCT00000003", 0.2, { agrees: ["stated"] }),
        candidate("NCT00000001", 0.9, { agrees: ["paper", "trial_name", "participants", "sponsor"] }),
        candidate("NCT00000002", 0.8, { agrees: ["participants"] }),
        candidate("NCT00000004", 0.1, { agrees: ["sponsor"] }),
      ],
    }),
  );

  assert.equal(shown.trialSaid, "Of the trial itself, the article says: it is called REGROW-2 and 2,539 people took part.");
  // Low-confidence citations remain inspectable, outside the possible matches.
  assert.deepEqual(shown.likely.map((record) => record.why), [
    "A paper the article links to gives this record's number. Its registration agrees with the article on the trial's name, the number of participants and who ran it.",
    "Its registration agrees with the article on the number of participants.",
  ]);
  assert.equal(shown.mentioned[0].why, "The article gives this record's number.");
  assert.equal(shown.rest, "1 other record was found and read as not being trials of this treatment for this condition.");
  assertNeutral([shown.trialSaid, ...shown.likely.map((record) => record.why)]);
});

test("no record found is not worded as no trial existing", () => {
  const shown = describeAnswer(answer());

  assert.deepEqual(shown.likely, []);
  assert.equal(shown.none, LIVE.none);
  assert.match(shown.none, /not evidence that no trial exists/);
});

test("a cited different-setting trial is separate from possible matches", () => {
  const shown = describeAnswer(answer({ candidates: [
    candidate("NCT00000001", 0, { agrees: ["stated"], answer: "other_indication" }),
    candidate("NCT00000002", 0.99),
    candidate("NCT00000003", 0.6),
  ] }));
  assert.deepEqual(shown.likely.map(record => record.registryId), ["NCT00000002", "NCT00000003"]);
  assert.deepEqual(shown.mentioned.map(record => record.registryId), ["NCT00000001"]);
  assert.equal(shown.mentioned[0].confidence, 0);
  assert.match(shown.mentioned[0].why, /record's number/);
  assert.equal(shown.rest, null);
});

test("a cited trial alone cannot suppress the no-match notice", () => {
  const shown = describeAnswer(answer({ candidates: [
    candidate("NCT00000001", 0.9, { agrees: ["paper"], answer: "other_indication" }),
  ] }));
  assert.deepEqual(shown.likely, []);
  assert.equal(shown.none, LIVE.none);
  assert.equal(shown.mentioned[0].registryId, "NCT00000001");
});

test("possible matches lead in score order without mutating the response", () => {
  const candidates = [candidate("NCT00000001", 0.6), candidate("NCT00000002", 0.99)];
  const shown = describeAnswer(answer({ candidates }));
  assert.deepEqual(shown.likely.map(record => record.registryId), ["NCT00000002", "NCT00000001"]);
  assert.equal(candidates[0].id, "NCT00000001");
});

test("the display cap is shared by possible matches and other citations", () => {
  const shown = describeAnswer(answer({ candidates: [
    ...Array.from({ length: 9 }, (_, index) => candidate(`NCT${index}`, 0.9)),
    candidate("NCTCITED1", 0, { agrees: ["stated"] }),
    candidate("NCTCITED2", 0, { agrees: ["stated"] }),
  ] }));
  assert.equal(shown.likely.length, 9);
  assert.equal(shown.mentioned.length, 1);
});

test("Scenario: Reader is told a linked paper was not looked up", () => {
  assert.equal(describeAnswer(answer()).papersUnchecked, null);
  assert.equal(describeAnswer(answer({ papers_unchecked: 0 })).papersUnchecked, null);
  const one = describeAnswer(answer({ papers_unchecked: 1 })).papersUnchecked;
  const two = describeAnswer(answer({ papers_unchecked: 2 })).papersUnchecked;

  assert.equal(one, "A linked paper could not be looked up just now, so a trial it reports may be missing from this list. Try again in a minute.");
  assert.match(two, /^2 linked papers could not be looked up just now, so trials they report may be missing/);
  assertNeutral([one, two]);
  // Nothing was searched for a text with no treatment, so nothing is said to be missing.
  assert.equal(describeAnswer(answer({ about_a_treatment: false, treatment: null, papers_unchecked: 0 })).papersUnchecked, null);
});

test("papers and organisation identities have no clinical confidence or status", () => {
  const result=describeAnswer(answer({research:{
    papers:[{title:"Synthetic research",year:2024,kind:"article",journal:"Example Journal",url:"https://doi.org/10.1234/example"}],
    organisations:[{name:"Example University",country:"UK",url:"https://ror.org/02kpeqv85",score:1}],
    availability:{openalex:"ok",ror:"ok"},
  }}));
  assert.equal(result.research.papers[0].detail,"2024 · article · Example Journal");
  assert.match(result.research.paperNote,/Unreviewed/);
  assert.equal(describeAnswer(answer({research:{papers:[{title:"Synthetic research",year:2024,linked:true}]}})).research.papers[0].detail,"Linked from the article · 2024");
  assert.equal(describeAnswer(answer({research:{papers:[{title:"Synthetic research",year:2024,institutions:["Example University"]}]}})).research.papers[0].detail,"Authors at Example University · 2024");
  assert.equal(result.research.organisations[0].title,"Example University");
  assert(!JSON.stringify(result.research).includes("confidence"));
  assert.equal(result.none,LIVE.none);
  assert.equal(describeAnswer(answer()).research,null);
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
