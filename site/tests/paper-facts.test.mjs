// The site's wording for papers, checked against openspec paper-facts and
// site-publishing: codes are worded here, an entry says what an index record states,
// and no wording says what a paper shows about a claim or ranks one paper above another.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  PAPER_KIND_WORDS,
  PAPERS_NOTE,
  assertNoPaperVerdict,
  countRecords,
  groupPapers,
  paperAnchor,
  paperName,
  paperStanding,
  studiedInText,
  recordCountText,
  unlabelledPaperCodes,
} from "../src/lib/paper-facts.ts";

const facts = (extra = {}) => ({
  title: "A synthetic paper",
  journal: "Journal of Synthetic Trials",
  year: 2022,
  kinds: ["article"],
  open_access: false,
  retracted: false,
  studied_in: [],
  ...extra,
});

const paper = (identifier, roles, extra = {}) => ({
  identifier,
  url: `https://doi.org/${identifier}`,
  record_url: null,
  roles: roles.map((role) => (typeof role === "string" ? { role } : role)),
  facts_as_of: "2026-10-03T08:00:00Z",
  facts: facts(),
  ...extra,
});

const trial = (id) => ({ trial_id: id });

test("Scenario: Randomised trial report", () => {
  const report = paper("10.5555/a", ["trial_result"], {
    facts: facts({ kinds: ["randomised_trial", "clinical_trial", "article"] }),
  });
  assert.equal(
    paperStanding(report),
    "Report of a randomised trial · Journal of Synthetic Trials · 2022",
  );
});

test("a paper with no journal or kind shows what its record does state", () => {
  const preprint = paper("10.5555/b", ["related"], { facts: facts({ journal: null, kinds: ["preprint"] }) });
  assert.equal(paperStanding(preprint), "Preprint · 2022");
  assert.equal(paperStanding(paper("10.5555/c", ["origin"], { facts: null })), null);
});

test("Scenario: Paper of a study in mice, and a paper with no statement", () => {
  const filed = (studied_in) => studiedInText(paper("10.5555/a", ["origin"], { facts: facts({ studied_in }) }));
  assert.equal(filed(["animals"]), "Europe PMC subject headings: animals");
  assert.equal(filed(["people"]), "Europe PMC subject headings: humans");
  assert.equal(filed(["people", "animals"]), "Europe PMC subject headings: humans and animals");
  assert.equal(filed([]), null);
  assert.equal(studiedInText(paper("10.5555/a", ["origin"], { facts: null })), null);
});

test("Scenario: Paper with two roles is listed once, in the group of its first", () => {
  const groups = groupPapers([
    paper("10.5555/origin", ["origin", { role: "trial_result", trial_id: "NCT1", listed: "listed_by_sponsor" }]),
    paper("10.5555/result", [{ role: "trial_result", trial_id: "NCT1", listed: "linked_by_registry" }]),
    paper("10.5555/related", ["related"]),
  ]);
  assert.deepEqual(
    groups.map((group) => [group.role, group.papers.map((entry) => entry.identifier)]),
    [
      ["origin", ["10.5555/origin"]],
      ["trial_result", ["10.5555/result"]],
      ["related", ["10.5555/related"]],
    ],
  );
  assert.equal(groups[0].heading, "The paper first reported");
  assert.deepEqual(groupPapers([]), []);
});

test("Scenario: Claim with three trials and one mouse paper", () => {
  const claim = {
    trials: [trial("NCT1"), trial("NCT2"), trial("NCT3")],
    papers: [paper("10.5555/mouse", ["origin"], { facts: facts({ studied_in: ["animals"] }) })],
  };
  assert.deepEqual(countRecords(claim), { trials: 3, papers: 1 });
  assert.equal(recordCountText(countRecords(claim)), "3 trial records · 1 paper");
});

test("human and animal subject headings do not add trial records", () => {
  const claim = {
    trials: [trial("NCT1")],
    papers: [
      paper("10.5555/a", ["trial_result"], { facts: facts({ studied_in: ["people"] }) }),
      paper("10.5555/b", ["related"], { facts: facts({ studied_in: ["people", "animals"] }) }),
      paper("10.5555/c", ["related"], { facts: null }),
    ],
  };
  assert.equal(recordCountText(countRecords(claim)), "1 trial record · 3 papers");
});

test("papers with missing facts still count, while an empty record set does not", () => {
  const claim = { trials: [], papers: [paper("10.5555/a", ["origin"])] };
  assert.equal(recordCountText(countRecords(claim)), "1 paper");
  assert.equal(recordCountText(countRecords({})), null);
});

test("laboratory material subject headings do not imply a human trial", () => {
  const claim = { trials: [], papers: [paper("10.5555/lab", ["origin", "related"], { facts: facts({ studied_in: ["people", "animals"] }) })] };
  assert.deepEqual(countRecords(claim), { trials: 0, papers: 1 });
  assert.equal(recordCountText(countRecords(claim)), "1 paper");
});

test("Scenario: Kind code without site wording", () => {
  const odd = paper("10.5555/a", [{ role: "trial_result", trial_id: "NCT1", listed: "found_by_luck" }], {
    facts: facts({ kinds: ["hologram", "article"], studied_in: ["plants"] }),
  });
  const related = paper("10.5555/b", [{ role: "related", reasons: ["named_in_title", "liked_it"] }]);
  assert.deepEqual(unlabelledPaperCodes([odd, related, paper("10.5555/c", ["cameo"])]), [
    "how listed: found_by_luck",
    "paper kind: hologram",
    "paper reason: liked_it",
    "paper role: cameo",
    "studied in: plants",
  ]);
  assert.deepEqual(unlabelledPaperCodes([paper("10.5555/d", ["origin"])]), []);
});

test("Scenario: Wording with a verdict", () => {
  assert.throws(() => assertNoPaperVerdict(["This paper proves the claim"]), /"proves"/);
  assert.throws(() => assertNoPaperVerdict(["A paper that supports it"]), /supports/);
  assert.throws(() => assertNoPaperVerdict(["The strongest paper"]), /strongest/);
  assert.doesNotThrow(() => assertNoPaperVerdict([...Object.values(PAPER_KIND_WORDS), PAPERS_NOTE]));
  assert.match(PAPERS_NOTE, /not a trial record and does not set the status/);
});

test("a paper the index does not hold is called by its identifier", () => {
  assert.equal(paperName(paper("pmid:26048637", ["trial_result"], { facts: null })), "PubMed 26048637");
  assert.equal(paperName(paper("10.5555/x", ["origin"], { facts: null })), "10.5555/x");
  assert.equal(paperName(paper("10.5555/x", ["origin"])), "A synthetic paper");
  assert.equal(paperAnchor("10.1056/NEJMoa2206038"), "paper-10-1056-NEJMoa2206038");
  assert.equal(paperAnchor("pmid:26048637"), "paper-pmid-26048637");
});
