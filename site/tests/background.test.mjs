// The site's wording for background cards, checked against openspec site-publishing:
// codes are worded here, a definition is never the site's, and a code with no wording
// is named.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  BACKGROUND_NOTE,
  cardKindText,
  creditText,
  reasonTexts,
  unwordedCardCodes,
} from "../src/lib/background.ts";

const card = (extra = {}) => ({
  kind: "condition",
  fit: "exact",
  source: "mesh",
  version: "2026",
  reasons: [{ code: "filed_by_registry", trials: 5, of: 6, name: null }],
  ...extra,
});

test("a card says what its term is to the claim, and when it is broader", () => {
  assert.equal(cardKindText(card()), "The condition");
  assert.equal(cardKindText(card({ kind: "intervention" })), "The treatment");
  assert.equal(cardKindText(card({ fit: "broader" })), "A broader term than this claim’s condition");
  assert.equal(
    cardKindText(card({ kind: "intervention", fit: "broader" })),
    "A broader term than this claim’s treatment",
  );
});

test("reasons are worded with their counts and names", () => {
  assert.deepEqual(reasonTexts(card()), [
    "The trial registry files 5 of this claim’s 6 trials under this term.",
  ]);
  assert.deepEqual(
    reasonTexts(card({ reasons: [{ code: "label_equals_name", name: "Obesity" }] })),
    ["The term’s label is the same as “Obesity”, a name this claim uses."],
  );
});

test("the credit states the vocabulary's edition when the record gives it", () => {
  const source = { credit: "A Vocabulary, Its Publisher" };
  assert.equal(creditText(card(), source), "A Vocabulary, Its Publisher, 2026 edition");
  assert.equal(creditText(card({ version: null }), source), "A Vocabulary, Its Publisher");
});

test("codes with no wording are named, and worded ones are not", () => {
  const sources = [{ name: "mesh" }];
  assert.deepEqual(unwordedCardCodes([card(), card({ fit: "broader" })], sources), []);
  assert.deepEqual(
    unwordedCardCodes(
      [
        card({ kind: "target" }),
        card({ fit: "close" }),
        card({ source: "elsewhere" }),
        card({ reasons: [{ code: "sounds_right" }] }),
      ],
      sources,
    ),
    ["card fit: close", "card kind: target", "card reason: sounds_right", "card source: elsewhere"],
  );
});

test("the section's note says what a card is not", () => {
  assert.match(BACKGROUND_NOTE, /not about this claim’s evidence/);
  assert.match(BACKGROUND_NOTE, /not medical advice/);
});
