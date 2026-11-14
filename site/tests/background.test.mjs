// The site's wording for background cards, checked against openspec site-publishing:
// codes are worded here, a definition is never the site's, and a code with no wording
// is named.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  BACKGROUND_NOTE,
  DRUG_NOTE,
  TARGET_NOTE,
  cardKindText,
  creditText,
  definitionCreditText,
  factsCreditText,
  isDrugsTarget,
  mechanismTexts,
  moleculeKindText,
  scoreLabel,
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

test("Scenario: Target the report names. The card says where the gene comes from and no more", () => {
  const target = card({
    kind: "target",
    source: "opentargets",
    definition_source: "uniprot",
    version: null,
    reasons: [{ code: "word_equals_symbol", word: "CXCR3" }],
  });
  assert.equal(cardKindText(target), "A gene named in the treatment’s name");
  assert.deepEqual(reasonTexts(target), [
    "“CXCR3”, a word in the treatment’s name, is this gene’s symbol.",
  ]);
  assert.deepEqual(
    reasonTexts(card({ reasons: [{ code: "word_equals_synonym", word: "TMS", sources: ["HGNC", "NCBI_entrez"] }] })),
    [
      "“TMS”, a word in the treatment’s name, is another name for this gene, listed by the HUGO Gene Nomenclature Committee and NCBI Gene. It is not the gene’s symbol.",
    ],
  );
  assert.equal(
    definitionCreditText({ credit: "UniProt Consortium", licence: "CC BY 4.0" }),
    "Description by UniProt Consortium, CC BY 4.0",
  );
  assert.match(TARGET_NOTE, /does not say the treatment is known to work through that gene/);
  // No word of the site's about a target says how the treatment works.
  for (const words of [cardKindText(target), ...reasonTexts(target), TARGET_NOTE]) {
    assert.doesNotMatch(words, /acts on|targets|works by|mechanism|inhibit|block/i);
  }
  const sources = [{ name: "opentargets" }, { name: "uniprot" }];
  assert.deepEqual(unwordedCardCodes([target], sources), []);
  assert.deepEqual(
    unwordedCardCodes(
      [
        target,
        card({ kind: "target", fit: "broader", source: "opentargets" }),
        card({ source: "opentargets", reasons: [{ code: "word_equals_synonym", word: "X1", sources: ["a_blog"] }] }),
        card({ source: "opentargets", reasons: [{ code: "word_equals_synonym", word: "X1" }] }),
      ],
      [{ name: "opentargets" }],
    ),
    [
      "card fit: broader for target",
      "card source: uniprot",
      "card synonym source: a_blog",
      "card synonym source: none given",
    ],
  );
});

test("a drug card says what the record says, in the site's words, with no percentage", () => {
  const drug = card({
    kind: "drug",
    source: "opentargets",
    version: null,
    score: null,
    molecule_kind: "protein",
    mechanisms: [
      { action: "agonist", target: "Glucagon-like peptide 1 receptor" },
      { action: "binding_agent", target: "Receptor tyrosine-protein kinase erbB-2" },
    ],
    facts_source: "chembl",
    reasons: [{ code: "drug_name_equals_name", name: "Tirzepatide" }],
  });
  assert.equal(cardKindText(drug), "The drug, as a drug database records it");
  assert.equal(moleculeKindText(drug), "Protein or peptide");
  assert.equal(moleculeKindText(card()), null);
  assert.deepEqual(mechanismTexts(drug), [
    "Agonist of Glucagon-like peptide 1 receptor",
    "Binds to Receptor tyrosine-protein kinase erbB-2",
  ]);
  assert.equal(scoreLabel(drug, () => "never asked"), "Matched by exact name");
  assert.equal(scoreLabel(card({ score: 0.9 }), (score) => `scored ${score}`), "scored 0.9");
  assert.deepEqual(reasonTexts(drug), [
    "The drug database’s own name for this drug is the same as “Tirzepatide”, a name this claim uses. Matched by that rule, so there is no percentage.",
  ]);
  assert.equal(
    factsCreditText(drug, { credit: "ChEMBL, EMBL-EBI", licence: "CC BY-SA 3.0 Unported" }),
    "Kind of molecule and what it acts on: ChEMBL, EMBL-EBI, CC BY-SA 3.0 Unported",
  );
  // The target a drug's record names is worded as the record's, not as a named gene.
  const itsTarget = card({
    kind: "target",
    source: "opentargets",
    score: null,
    facts_source: "chembl",
    reasons: [{ code: "drug_record_names_target", name: "SEMAGLUTIDE" }],
  });
  assert.equal(isDrugsTarget(itsTarget), true);
  assert.equal(cardKindText(itsTarget), "What the drug acts on, as its record says");
  assert.equal(scoreLabel(itsTarget, () => ""), "From the drug’s record");
  assert.match(DRUG_NOTE, /nothing here is a reason to start or stop a medicine/);
  // Nothing the site says of a drug recommends it or says what it is used for.
  for (const words of [cardKindText(drug), ...mechanismTexts(drug), ...reasonTexts(drug), DRUG_NOTE]) {
    assert.doesNotMatch(words, /recommend|should|used (for|to)|treats|approved|effective|safe/i);
  }

  const sources = [{ name: "opentargets" }, { name: "chembl" }];
  assert.deepEqual(unwordedCardCodes([drug, itsTarget], sources), []);
  assert.deepEqual(
    unwordedCardCodes(
      [
        { ...drug, molecule_kind: "nanobot" },
        { ...drug, mechanisms: [{ action: "persuader", target: "A receptor" }] },
        card({ score: null }),
      ],
      [{ name: "opentargets" }, { name: "mesh" }],
    ),
    [
      "card action: persuader",
      "card molecule kind: nanobot",
      "card source: chembl",
      "card without a score: condition",
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
        card({ kind: "organ" }),
        card({ fit: "close" }),
        card({ source: "elsewhere" }),
        card({ reasons: [{ code: "sounds_right" }] }),
      ],
      sources,
    ),
    ["card fit: close", "card kind: organ", "card reason: sounds_right", "card source: elsewhere"],
  );
});

test("the section's note says what a card is not", () => {
  assert.match(BACKGROUND_NOTE, /not about this claim’s evidence/);
  assert.match(BACKGROUND_NOTE, /not medical advice/);
});
