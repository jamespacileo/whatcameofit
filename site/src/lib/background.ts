// The site's wording for background cards. Openspec knowledge-cards and site-publishing:
// the export carries codes and the vocabulary's own definition; the site words the
// codes, never rewords a definition and adds no explanation of a condition or a
// treatment of its own.
import { assertNeutral } from "./status.ts";
import { assertNoOutcomeVerdict } from "./trial-facts.ts";

export interface CardReason {
  /** "filed_by_registry", "label_equals_name", "entry_term_equals_name", "kind_chosen"
   * or "registry_lists_type". */
  code: string;
  trials?: number | null;
  of?: number | null;
  name?: string | null;
  /** For "entry_term_equals_name": the vocabulary's other wording the name equals. */
  entry_term?: string | null;
  /** For "kind_chosen": the code of the kind, from the pipeline's fixed list. */
  kind?: string | null;
  /** For "registry_lists_type": the trial registry's own code, such as "DEVICE". */
  type?: string | null;
  /** For "word_equals_symbol" and "word_equals_synonym": the word of the treatment's
   * name that equals the gene's symbol or a listed synonym of it. */
  word?: string | null;
  /** For "word_equals_synonym": the target source's codes for who lists the synonym. */
  sources?: string[] | null;
}

export interface ExportedCard {
  /** What the term is to the claim: "condition", "intervention", "drug" for a drug
   * database's record of the treatment, or "target": the one protein a drug's record
   * names, or else a gene named in the treatment's name. */
  kind: string;
  /** For a drug: the kind of molecule, as a code. */
  molecule_kind?: string | null;
  /** For a drug: what its record says it does, each an action code and a target's name. */
  mechanisms?: { action: string; target: string }[];
  /** The name in `card_sources` of the source the card's facts are drawn from, when
   * they are under another licence than the card's own source. */
  facts_source?: string | null;
  /** For a target: the gene's approved name. Absent or null otherwise. */
  name?: string | null;
  /** The name in `card_sources` of the source the definition's words come from, when
   * that is not the card's own source. */
  definition_source?: string | null;
  /** How the term fits the claim: "exact", "broader", or "kind" for the term of the
   * kind of treatment this is. */
  fit: string;
  label: string;
  /** The vocabulary publisher's own words. Null when it gives none. */
  definition: string | null;
  url: string;
  /** The source's name in the export's `card_sources`. */
  source: string;
  external_id: string;
  /** The version of the vocabulary the record was read from. */
  version: string | null;
  /** Null for a card made by a rule a reader can check, such as an exact name. */
  score: number | null;
  reasons: CardReason[];
  decided_by: string;
  read_at: string;
}

export interface ExportedCardSource {
  name: string;
  title: string;
  /** How the source asks to be credited. */
  credit: string;
  licence: string;
  url: string;
  terms_url: string;
  /** Whether its cards may be offered in the open data file. */
  in_data_file: boolean;
}

/** What a card is about, when its term is the claim's own. */
export const CARD_KIND_WORDS: Record<string, string> = {
  condition: "The condition",
  intervention: "The treatment",
  // Says where the gene comes from and nothing about how the treatment works.
  target: "A gene named in the treatment’s name",
  drug: "The drug, as a drug database records it",
};

/** What a target card is about when it comes from a drug's record, not from a name. */
export const DRUG_TARGET_WORDS = "What the drug acts on, as its record says";

/** A drug's kind of molecule, by the drug source's code for it. */
export const MOLECULE_KIND_WORDS: Record<string, string> = {
  small_molecule: "Small molecule",
  antibody: "Antibody",
  antibody_drug_conjugate: "Antibody-drug conjugate",
  protein: "Protein or peptide",
  oligonucleotide: "Oligonucleotide",
  oligosaccharide: "Oligosaccharide",
  enzyme: "Enzyme",
  cell: "Cell-based product",
  gene: "Gene-based product",
  unknown: "Kind of molecule not recorded",
};

/** What a drug's record says it does to a target, by the drug source's action code. */
export const ACTION_WORDS: Record<string, (target: string) => string> = {
  agonist: (target) => `Agonist of ${target}`,
  partial_agonist: (target) => `Partial agonist of ${target}`,
  inverse_agonist: (target) => `Inverse agonist of ${target}`,
  antagonist: (target) => `Antagonist of ${target}`,
  allosteric_antagonist: (target) => `Allosteric antagonist of ${target}`,
  inhibitor: (target) => `Inhibitor of ${target}`,
  blocker: (target) => `Blocker of ${target}`,
  opener: (target) => `Opener of ${target}`,
  activator: (target) => `Activator of ${target}`,
  modulator: (target) => `Modulator of ${target}`,
  positive_modulator: (target) => `Positive modulator of ${target}`,
  negative_modulator: (target) => `Negative modulator of ${target}`,
  positive_allosteric_modulator: (target) => `Positive allosteric modulator of ${target}`,
  negative_allosteric_modulator: (target) => `Negative allosteric modulator of ${target}`,
  binding_agent: (target) => `Binds to ${target}`,
  releasing_agent: (target) => `Releasing agent for ${target}`,
  substrate: (target) => `Substrate of ${target}`,
  stabiliser: (target) => `Stabiliser of ${target}`,
  degrader: (target) => `Degrader of ${target}`,
  disrupting_agent: (target) => `Disrupting agent for ${target}`,
  cross_linking_agent: (target) => `Cross-linking agent for ${target}`,
  chelating_agent: (target) => `Chelating agent for ${target}`,
  sequestering_agent: (target) => `Sequestering agent for ${target}`,
  antisense_inhibitor: (target) => `Antisense inhibitor of ${target}`,
  rnai_inhibitor: (target) => `RNA-interference inhibitor of ${target}`,
  hydrolytic_enzyme: (target) => `Hydrolytic enzyme acting on ${target}`,
  proteolytic_enzyme: (target) => `Proteolytic enzyme acting on ${target}`,
  oxidative_enzyme: (target) => `Oxidative enzyme acting on ${target}`,
  reducing_agent: (target) => `Reducing agent for ${target}`,
  methylating_agent: (target) => `Methylating agent for ${target}`,
  vaccine_antigen: (target) => `Vaccine antigen: ${target}`,
  exogenous_protein: (target) => `Supplies the protein ${target}`,
  exogenous_gene: (target) => `Supplies the gene for ${target}`,
  other: (target) => `Acts on ${target}, in a way the record does not class`,
};

/** Who lists a synonym of a gene's symbol, by the target source's code for them. */
export const SYNONYM_SOURCE_WORDS: Record<string, string> = {
  uniprot: "UniProt",
  HGNC: "the HUGO Gene Nomenclature Committee",
  NCBI_entrez: "NCBI Gene",
};
const SYNONYM_SOURCES = Object.entries(SYNONYM_SOURCE_WORDS).map(([code]) => code);

function listed(words: string[]): string {
  if (words.length <= 1) return words.join("");
  return `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}`;
}

/** What a card is about, when its term is wider than the claim's. */
export const BROADER_WORDS: Record<string, string> = {
  condition: "A broader term than this claim’s condition",
  intervention: "A broader term than this claim’s treatment",
};

/** What a card is about, when its term is the kind of thing the claim's treatment is. */
export const KIND_WORDS: Record<string, string> = {
  intervention: "The kind of treatment this is, not the treatment itself",
};

/** How a link fits, each with the words for what its card is about. */
const FIT_WORDS: Record<string, Record<string, string>> = {
  exact: CARD_KIND_WORDS,
  broader: BROADER_WORDS,
  kind: KIND_WORDS,
};

/** The trial registry's types of intervention, as the end of "lists it as …". */
export const REGISTRY_TYPE_WORDS: Record<string, string> = {
  DRUG: "a drug",
  DEVICE: "a device",
  BIOLOGICAL: "a biological product or vaccine",
  PROCEDURE: "a procedure",
  RADIATION: "radiation",
  BEHAVIORAL: "a behavioural intervention",
  GENETIC: "a genetic intervention",
  DIETARY_SUPPLEMENT: "a dietary supplement",
  COMBINATION_PRODUCT: "a combination product",
  DIAGNOSTIC_TEST: "a diagnostic test",
  OTHER: "an intervention of another type",
};
const REGISTRY_TYPES = Object.entries(REGISTRY_TYPE_WORDS).map(([type]) => type);

const REASON_WORDS: Record<string, (reason: CardReason) => string> = {
  filed_by_registry: ({ trials, of }) =>
    of === 1
      ? "When this term was gathered, the trial registry filed the claim’s one trial under it."
      : `When this term was gathered, the trial registry filed ${trials} of the claim’s ${of} trials under it.`,
  label_equals_name: ({ name }) =>
    `The term’s label is the same as “${name}”, a name this claim uses.`,
  entry_term_equals_name: ({ entry_term, name }) =>
    `The vocabulary files “${entry_term}” under this term, and that is the same as “${name}”, a name this claim uses.`,
  kind_chosen: () =>
    "No term was found for the treatment itself. Its kind was chosen from this site’s fixed list of kinds.",
  registry_lists_type: ({ type, trials }) =>
    trials === 1
      ? `The trial registry lists it as ${REGISTRY_TYPE_WORDS[type ?? ""]} in one of this claim’s trials.`
      : `The trial registry lists it as ${REGISTRY_TYPE_WORDS[type ?? ""]} in ${trials} of this claim’s trials.`,
  drug_name_equals_name: ({ name }) =>
    `The drug database’s own name for this drug is the same as “${name}”, a name this claim uses. Matched by that rule, so there is no percentage.`,
  drug_record_names_target: ({ name }) =>
    `The drug database’s record of ${name} names this as the one protein the drug acts on. Taken from that record, so there is no percentage.`,
  word_equals_symbol: ({ word }) =>
    `“${word}”, a word in the treatment’s name, is this gene’s symbol.`,
  word_equals_synonym: ({ word, sources }) =>
    `“${word}”, a word in the treatment’s name, is another name for this gene, listed by ${listed(
      (sources ?? []).map((code) => SYNONYM_SOURCE_WORDS[code]),
    )}. It is not the gene’s symbol.`,
};

/** What the section says, in addition, when one of its cards is for a named gene. */
export const TARGET_NOTE =
  "A gene is shown because the treatment’s name names it. That does not say the treatment is known to work through that gene.";
export const TARGET_DEFINITION_LABEL = "What this gene’s product does, in the source’s words";
export const NO_TARGET_DEFINITION = "The source gives this gene no description.";

/** What the section says, in addition, when one of its cards is for a drug. */
export const DRUG_NOTE =
  "What a drug acts on is its drug database’s record of the drug. It is not about this condition, and nothing here is a reason to start or stop a medicine.";
export const NO_MECHANISM = "The record gives no mechanism for this drug.";
/** What stands where a score would, on a card made by a rule and not scored, after
 * "Term match:". */
export const RULE_LABELS: Record<string, string> = {
  drug: "by exact name",
  target: "from the drug’s record",
};

/** Whether a target card comes from a drug's record and not from the treatment's name. */
export function isDrugsTarget(card: Pick<ExportedCard, "kind" | "reasons">): boolean {
  return (
    card.kind === "target" &&
    card.reasons.some((reason) => reason.code === "drug_record_names_target")
  );
}

/** A drug's kind of molecule in words, or nothing when its record gives none. */
export function moleculeKindText(card: Pick<ExportedCard, "molecule_kind">): string | null {
  return card.molecule_kind ? MOLECULE_KIND_WORDS[card.molecule_kind] : null;
}

/** What a drug's record says it does, one phrase per mechanism. */
export function mechanismTexts(card: Pick<ExportedCard, "mechanisms">): string[] {
  return (card.mechanisms ?? []).map(({ action, target }) => ACTION_WORDS[action](target));
}

/** A card's score, said as being about the term so it is never read as about the
 * treatment: "Term match: high, 81%", or the rule that stands for it. The same words in
 * its row and on the card. */
export function scoreLabel(card: Pick<ExportedCard, "kind" | "score">, scored: (score: number) => string): string {
  return `Term match: ${card.score === null ? RULE_LABELS[card.kind] : scored(card.score)}`;
}

/** Whose facts a card rests on when they are not its own source's, with the licence. */
export function factsCreditText(
  card: Pick<ExportedCard, "kind">,
  source: Pick<ExportedCardSource, "credit" | "licence">,
): string {
  const what =
    card.kind === "drug" ? "Kind of molecule and what it acts on" : "That the drug acts on it";
  return `${what}: ${source.credit}, ${source.licence}`;
}

/** Who wrote a definition that is not the card's own source's, with its licence. */
export function definitionCreditText(source: Pick<ExportedCardSource, "credit" | "licence">): string {
  return `Description by ${source.credit}, ${source.licence}`;
}

/** The card's heading over its reasons: the score itself is in sight on its row. */
export const MATCH_WHY_HEAD = "Why it matched";

/** One line under the section's heading, where a reader first meets a term match. */
export const GLANCE_LEAD =
  "Each term is shown in an outside source’s words. A term match is how well that source’s term fits this claim; it says nothing about the treatment.";

/** What the section says of itself, once, above the cards. */
export const BACKGROUND_NOTE =
  "These notes describe the terms this claim uses, in their sources’ own words and not this site’s; naming a source does not mean it endorses this site. They are not about this claim’s evidence and they are not medical advice, and a score is about how well a term fits the claim, not about the treatment.";

export const DEFINITION_LABEL = "Definition, in the source’s words";
export const NO_DEFINITION = "The source gives this term no definition.";
export const NO_REASON = "No reason was found by rule.";

/** "The condition", or that the term is broader than the claim's, or that it is the
 * kind of treatment and not the treatment. */
export function cardKindText(
  card: Pick<ExportedCard, "kind" | "fit"> & Partial<Pick<ExportedCard, "reasons">>,
): string {
  if (isDrugsTarget({ kind: card.kind, reasons: card.reasons ?? [] })) return DRUG_TARGET_WORDS;
  return FIT_WORDS[card.fit][card.kind];
}

/** Why the term was chosen, one sentence per reason found by rule. */
export function reasonTexts(card: Pick<ExportedCard, "reasons">): string[] {
  return card.reasons.map((reason) => REASON_WORDS[reason.code](reason));
}

/** The credit a source asks for, with the vocabulary's version when the record gives it. */
export function creditText(
  card: Pick<ExportedCard, "version">,
  source: Pick<ExportedCardSource, "credit">,
): string {
  return card.version ? `${source.credit}, ${card.version} edition` : source.credit;
}

/** Card codes in the export that the site has no words for, as "kind: code". */
export function unwordedCardCodes(
  cards: (Pick<ExportedCard, "kind" | "fit" | "reasons" | "source" | "definition_source"> &
    Partial<Pick<ExportedCard, "molecule_kind" | "mechanisms" | "facts_source" | "score">>)[],
  sources: Pick<ExportedCardSource, "name">[],
): string[] {
  const missing = new Set<string>();
  const known = new Set(sources.map((source) => source.name));
  for (const card of cards) {
    if (card.definition_source && !known.has(card.definition_source)) {
      missing.add(`card source: ${card.definition_source}`);
    }
    if (card.facts_source && !known.has(card.facts_source)) {
      missing.add(`card source: ${card.facts_source}`);
    }
    if (card.molecule_kind && !(card.molecule_kind in MOLECULE_KIND_WORDS)) {
      missing.add(`card molecule kind: ${card.molecule_kind}`);
    }
    for (const mechanism of card.mechanisms ?? []) {
      if (!(mechanism.action in ACTION_WORDS)) missing.add(`card action: ${mechanism.action}`);
    }
    // A card with no score needs words for what stands in its place.
    if (card.score === null && !(card.kind in RULE_LABELS)) {
      missing.add(`card without a score: ${card.kind}`);
    }
    if (!(card.kind in CARD_KIND_WORDS)) missing.add(`card kind: ${card.kind}`);
    if (!(card.fit in FIT_WORDS)) missing.add(`card fit: ${card.fit}`);
    // A fit the site words for one kind of card only, such as a kind of treatment.
    else if (card.kind in CARD_KIND_WORDS && !(card.kind in FIT_WORDS[card.fit])) {
      missing.add(`card fit: ${card.fit} for ${card.kind}`);
    }
    if (!known.has(card.source)) missing.add(`card source: ${card.source}`);
    for (const reason of card.reasons) {
      if (!(reason.code in REASON_WORDS)) missing.add(`card reason: ${reason.code}`);
      else if (reason.code === "registry_lists_type" && !REGISTRY_TYPES.includes(reason.type ?? "")) {
        missing.add(`card registry type: ${reason.type}`);
      } else if (reason.code === "word_equals_synonym") {
        // A synonym with no source named cannot be worded either.
        if (!reason.sources?.length) missing.add("card synonym source: none given");
        for (const code of reason.sources ?? []) {
          if (!SYNONYM_SOURCES.includes(code)) missing.add(`card synonym source: ${code}`);
        }
      }
    }
  }
  return [...missing].sort();
}

// The site's own words about a card never say what became of a treatment or that it
// helps. A definition is the source's and is not checked here.
const SITE_WORDS = [
  ...Object.values(CARD_KIND_WORDS),
  ...Object.values(BROADER_WORDS),
  ...Object.values(KIND_WORDS),
  ...REGISTRY_TYPES.flatMap((type) =>
    [1, 3].map((trials) => REASON_WORDS.registry_lists_type({ code: "", type, trials })),
  ),
  ...Object.values(REASON_WORDS).map((word) =>
    word({
      code: "",
      trials: 2,
      of: 3,
      name: "a name",
      entry_term: "a wording",
      type: "DRUG",
      word: "ABC1",
      sources: SYNONYM_SOURCES,
    }),
  ),
  definitionCreditText({ credit: "A Consortium", licence: "A licence" }),
  factsCreditText({ kind: "drug" }, { credit: "A Database", licence: "A licence" }),
  factsCreditText({ kind: "target" }, { credit: "A Database", licence: "A licence" }),
  ...Object.values(MOLECULE_KIND_WORDS),
  ...Object.values(ACTION_WORDS).map((word) => word("a named receptor")),
  ...Object.values(RULE_LABELS),
  DRUG_TARGET_WORDS,
  DRUG_NOTE,
  NO_MECHANISM,
  TARGET_NOTE,
  TARGET_DEFINITION_LABEL,
  NO_TARGET_DEFINITION,
  BACKGROUND_NOTE,
  DEFINITION_LABEL,
  NO_DEFINITION,
  NO_REASON,
];
assertNeutral(SITE_WORDS);
assertNoOutcomeVerdict(SITE_WORDS);
