// The example words the lookup box offers (openspec search-answer-in-step): chosen by
// rule from the claims, in the order the site prefers its examples. Pure functions
// over synthetic claims: no page, no network.
import assert from "node:assert/strict";
import { test } from "node:test";
import { EXAMPLE_LENGTH, matchWeight, ranked, searchExample, searchWords } from "../src/lib/search-order.ts";

const claim = (slug, name, headline, more = {}) => ({
  slug,
  headline,
  intervention: { name, synonyms: [] },
  indication: "Example condition",
  articles: [{ title: "Synthetic report" }],
  ...more,
});

test("the example is the first claim whose treatment's name is in its headline and in no other claim", () => {
  const claims = [
    // Shared: another claim is for the same treatment.
    claim("shared-one", "Sharedmab", "Sharedmab was reported to help one condition"),
    // Not in its own headline.
    claim("unnamed", "Hiddenol", "A new pill was reported to help"),
    claim("found", "Clearzumab", "Clearzumab was reported to slow an example condition"),
    claim("later", "Laterol", "Laterol was reported to help"),
    claim("shared-two", "Sharedmab", "Sharedmab was reported to help another condition"),
  ];
  assert.deepEqual(searchExample(claims), { words: "clearzumab", slug: "found" });
});

test("a name held by another claim's report, condition or other name is passed over", () => {
  const taken = claim("taken", "Takenib", "Takenib was reported to help");
  for (const other of [
    claim("other", "Otherol", "Otherol was reported to help", { articles: [{ title: "Synthetic report on takenib" }] }),
    claim("other", "Otherol", "Otherol was reported to help", { indication: "Takenib resistance" }),
    claim("other", "Otherol", "Otherol was reported to help", { intervention: { name: "Otherol", synonyms: ["takenib II"] } }),
  ]) {
    assert.equal(searchExample([taken, other])?.slug, "other");
  }
});

test("a name of more than three words, with marks in it, too short to search or too long for the field is passed over", () => {
  const long = "x".repeat(EXAMPLE_LENGTH + 1);
  for (const name of ["one two three four", "anti-thing", "ab", `${long}`]) {
    assert.equal(searchExample([claim("only", name, `${name} was reported to help`)]), null, name);
  }
  // Two plain words that stand side by side in the headline are taken, as written.
  assert.deepEqual(searchExample([claim("pair", "ABC gel", "ABC gel was reported to help")]), { words: "ABC gel", slug: "pair" });
  // The same two words apart in the headline are not: the answer would not show why it leads.
  assert.equal(searchExample([claim("apart", "ABC gel", "A gel called ABC was reported to help")]), null);
});

test("no claim, or none that passes, gives no example", () => {
  assert.equal(searchExample([]), null);
});

test("the example's claim outweighs every other claim for its words", () => {
  const claims = [
    claim("found", "Clearzumab", "Clearzumab was reported to slow an example condition"),
    claim("near", "Otherol", "Otherol was reported to clear an example condition"),
  ];
  const example = searchExample(claims);
  const words = searchWords(example.words);
  const asMatch = (item) => ({ headline: item.headline, page: `/${item.slug}`, names: [item.intervention.name], indication: item.indication });
  const detail = { claims: Object.fromEntries(claims.map((item) => [item.slug, { reports: item.articles }])) };
  // Whatever order the search index gives them in, the rule puts the example's claim first.
  const order = ranked([asMatch(claims[1]), asMatch(claims[0])], words, detail);
  assert.equal(order[0].page, "/found");
  assert.equal(matchWeight(asMatch(claims[1]), words, detail), 0);
});
