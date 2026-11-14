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
}

export interface ExportedCard {
  /** What the term is to the claim: "condition" or "intervention". */
  kind: string;
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
  score: number;
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
};

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
      ? "The trial registry files this claim’s one trial under this term."
      : `The trial registry files ${trials} of this claim’s ${of} trials under this term.`,
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
};

/** What the section says of itself, once, above the cards. */
export const BACKGROUND_NOTE =
  "What an open vocabulary says about the terms this claim uses. Each definition is its source’s own wording, written for indexing research, and is not this site’s. Where the vocabulary has no term for the treatment itself, the note is for the kind of treatment it is, and says so. These notes describe terms. They are not about this claim’s evidence and they are not medical advice. A score is about how well a term fits the claim, not about the treatment. Naming a source does not mean it endorses this site.";

export const DEFINITION_LABEL = "Definition, in the source’s words";
export const NO_DEFINITION = "The source gives this term no definition.";
export const NO_REASON = "No reason was found by rule.";

/** "The condition", or that the term is broader than the claim's, or that it is the
 * kind of treatment and not the treatment. */
export function cardKindText(card: Pick<ExportedCard, "kind" | "fit">): string {
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
  cards: Pick<ExportedCard, "kind" | "fit" | "reasons" | "source">[],
  sources: Pick<ExportedCardSource, "name">[],
): string[] {
  const missing = new Set<string>();
  const known = new Set(sources.map((source) => source.name));
  for (const card of cards) {
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
    word({ code: "", trials: 2, of: 3, name: "a name", entry_term: "a wording", type: "DRUG" }),
  ),
  BACKGROUND_NOTE,
  DEFINITION_LABEL,
  NO_DEFINITION,
  NO_REASON,
];
assertNeutral(SITE_WORDS);
assertNoOutcomeVerdict(SITE_WORDS);
