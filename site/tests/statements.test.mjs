// The site's wording for reported statements, checked against openspec site-publishing:
// every code is worded here, a statement is always framed as its report's, and a code
// with no wording is named.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  BASIS_WORDS,
  KIND_WORDS,
  assertNoComparison,
  attributionText,
  statementConfidenceLabel,
  statementsHeading,
  statementsNote,
  unwordedStatementCodes,
} from "../src/lib/statements.ts";

const statement = (extra = {}) => ({
  kind: "effect",
  firmness: "fact",
  speaker: "article",
  basis: "people",
  ...extra,
});

test("Scenario: Possibility voiced by a researcher", () => {
  const said = attributionText(statement({ firmness: "possibility", speaker: "researcher" }));
  assert.equal(said, "The report had a researcher saying this could be so:");
});

test("a statement is always attributed to its report, by role", () => {
  assert.equal(attributionText(statement()), "The report said:");
  assert.equal(attributionText(statement({ firmness: "possibility" })), "The report said this could be so:");
  for (const speaker of ["researcher", "company", "patient", "other_expert"]) {
    for (const firmness of ["fact", "possibility"]) {
      assert.match(attributionText(statement({ speaker, firmness })), /^The report had (a|an|the|another) [a-z ]+ saying/);
    }
  }
});

test("Scenario: Effect reported from a mouse study", () => {
  assert.equal(BASIS_WORDS.animals, "The report gave a study in animals as its basis.");
  assert.equal(BASIS_WORDS.not_said, "The report did not say what this rests on.");
});

test("how sure the check is, as a word and a percentage", () => {
  assert.equal(statementConfidenceLabel(0.93), "Very likely in the report · 93%");
  assert.equal(statementConfidenceLabel(0.6), "Likely in the report · 60%");
  assert.equal(statementConfidenceLabel(0.2), "Unsure it is in the report · 20%");
});

test("the heading and note follow the number of reports", () => {
  assert.equal(statementsHeading(1), "What the report said");
  assert.equal(statementsHeading(3), "What the reports said");
  assert.match(statementsNote(1), /^What the news report said about the treatment/);
  assert.match(statementsNote(2), /^What the news reports said about the treatment/);
  assert.match(statementsNote(1), /A report’s statement is not a record: the records follow\./);
  assert.match(statementsNote(1), /Not medical advice\./);
});

test("Scenario: Kind code without site wording, named with the other codes", () => {
  const kinds = Object.entries(KIND_WORDS).map(([kind]) => statement({ kind }));
  assert.deepEqual(unwordedStatementCodes(kinds), []);
  assert.deepEqual(
    unwordedStatementCodes([
      statement({ kind: "miracle" }),
      statement({ firmness: "certain" }),
      statement({ speaker: "dr_who" }),
      statement({ basis: "hearsay" }),
    ]),
    [
      "statement basis: hearsay",
      "statement firmness: certain",
      "statement kind: miracle",
      "statement speaker: dr_who",
    ],
  );
});

test("wording that would hold a statement against a record is refused", () => {
  for (const text of ["The trial confirmed it.", "Records contradict this.", "This held up.", "It was right."]) {
    assert.throws(() => assertNoComparison([text]), /Comparison wording/);
  }
  assert.doesNotThrow(() => assertNoComparison([statementsNote(2), ...Object.values(KIND_WORDS)]));
});
