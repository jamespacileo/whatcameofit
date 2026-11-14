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

test("Scenario: Kind card. It says it is the kind of treatment, not the treatment", () => {
  assert.equal(
    cardKindText(card({ kind: "intervention", fit: "kind" })),
    "The kind of treatment this is, not the treatment itself",
  );
});

test("Scenario: Registry type as a reason, with the entry-term and kind reasons", () => {
  const reasons = [
    { code: "kind_chosen", kind: "electrical_stimulation" },
    { code: "registry_lists_type", type: "DEVICE", trials: 3 },
    { code: "registry_lists_type", type: "PROCEDURE", trials: 1 },
    { code: "entry_term_equals_name", entry_term: "Ketogenic Diet", name: "Ketogenic diet" },
  ];
  assert.deepEqual(reasonTexts(card({ reasons })), [
    "No term was found for the treatment itself. Its kind was chosen from this site’s fixed list of kinds.",
    "The trial registry lists it as a device in 3 of this claim’s trials.",
    "The trial registry lists it as a procedure in one of this claim’s trials.",
    "The vocabulary files “Ketogenic Diet” under this term, and that is the same as “Ketogenic diet”, a name this claim uses.",
  ]);
});

test("an unknown fit, a kind fit on a condition and an unknown registry type are named", () => {
  const sources = [{ name: "mesh" }];
  const kind = card({
    kind: "intervention",
    fit: "kind",
    reasons: [{ code: "kind_chosen", kind: "device" }, { code: "registry_lists_type", type: "DEVICE", trials: 2 }],
  });
  assert.deepEqual(unwordedCardCodes([kind], sources), []);
  assert.deepEqual(
    unwordedCardCodes(
      [
        card({ fit: "kind" }),
        card({ fit: "narrower" }),
        card({ reasons: [{ code: "registry_lists_type", type: "HOLOGRAM", trials: 2 }] }),
        card({ reasons: [{ code: "registry_lists_type", trials: 2 }] }),
      ],
      sources,
    ),
    [
      "card fit: kind for condition",
      "card fit: narrower",
      "card registry type: HOLOGRAM",
      "card registry type: undefined",
    ],
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
