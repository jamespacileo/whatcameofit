// The site's wording for background cards. Openspec knowledge-cards and site-publishing:
// the export carries codes and the vocabulary's own definition; the site words the
// codes, never rewords a definition and adds no explanation of a condition or a
// treatment of its own.
import { assertNeutral } from "./status.ts";
import { assertNoOutcomeVerdict } from "./trial-facts.ts";

export interface CardReason {
  /** "filed_by_registry" or "label_equals_name". */
  code: string;
  trials?: number | null;
  of?: number | null;
  name?: string | null;
}

export interface ExportedCard {
  /** What the term is to the claim: "condition" or "intervention". */
  kind: string;
  /** "exact" or "broader". */
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

const FIT_CODES = ["exact", "broader"];

const REASON_WORDS: Record<string, (reason: CardReason) => string> = {
  filed_by_registry: ({ trials, of }) =>
    of === 1
      ? "The trial registry files this claim’s one trial under this term."
      : `The trial registry files ${trials} of this claim’s ${of} trials under this term.`,
  label_equals_name: ({ name }) =>
    `The term’s label is the same as “${name}”, a name this claim uses.`,
};

/** What the section says of itself, once, above the cards. */
export const BACKGROUND_NOTE =
  "What an open vocabulary says about the terms this claim uses. Each definition is its source’s own wording, written for indexing research, and is not this site’s. These notes describe terms. They are not about this claim’s evidence and they are not medical advice. A score is about how well a term fits the claim, not about the treatment. Naming a source does not mean it endorses this site.";

export const DEFINITION_LABEL = "Definition, in the source’s words";
export const NO_DEFINITION = "The source gives this term no definition.";
export const NO_REASON = "No reason was found by rule.";

/** "The condition", or that the term is broader than the claim's. */
export function cardKindText(card: Pick<ExportedCard, "kind" | "fit">): string {
  return (card.fit === "broader" ? BROADER_WORDS : CARD_KIND_WORDS)[card.kind];
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
    if (!FIT_CODES.includes(card.fit)) missing.add(`card fit: ${card.fit}`);
    if (!known.has(card.source)) missing.add(`card source: ${card.source}`);
    for (const reason of card.reasons) {
      if (!(reason.code in REASON_WORDS)) missing.add(`card reason: ${reason.code}`);
    }
  }
  return [...missing].sort();
}

// The site's own words about a card never say what became of a treatment or that it
// helps. A definition is the source's and is not checked here.
const SITE_WORDS = [
  ...Object.values(CARD_KIND_WORDS),
  ...Object.values(BROADER_WORDS),
  ...Object.values(REASON_WORDS).map((word) => word({ code: "", trials: 2, of: 3, name: "a name" })),
  BACKGROUND_NOTE,
  DEFINITION_LABEL,
  NO_DEFINITION,
  NO_REASON,
];
assertNeutral(SITE_WORDS);
assertNoOutcomeVerdict(SITE_WORDS);
