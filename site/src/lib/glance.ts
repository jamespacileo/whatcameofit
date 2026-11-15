// "At a glance": what the claim's treatment and condition are, from its background
// cards, one line per row near the top of the claim page, and the kind and gene as a
// row in the record band. The cards keep their own words and scores, one press away
// in each row; this module sorts them into rows and words the row labels and values.
// Openspec knowledge-cards, site-publishing: "Background cards on the claim page" and
// "The band names what the treatment is".
import {
  isDrugsTarget,
  mechanismTexts,
  moleculeKindText,
  type ExportedCard,
} from "./background";
import { matchWords } from "./confidence";

export const GLANCE_TITLE = "At a glance";

/** The section's anchor, and each row's, so the band can point at a row. */
export const GLANCE_ID = "glance";
export const rowId = (row: GlanceRow) => `glance-${row}`;

export type GlanceRow = "treatment" | "kind" | "drug" | "target" | "condition";

/** A claim's cards, one per row; a row with no card has none. */
export type GlanceCards = Partial<Record<GlanceRow, ExportedCard>>;

export function glanceCards(cards: ExportedCard[]): GlanceCards {
  return {
    treatment: cards.find((card) => card.kind === "intervention" && card.fit !== "kind"),
    kind: cards.find((card) => card.kind === "intervention" && card.fit === "kind"),
    drug: cards.find((card) => card.kind === "drug"),
    target: cards.find((card) => card.kind === "target"),
    condition: cards.find((card) => card.kind === "condition"),
  };
}

/** Each row's label, said the same in the band and in "At a glance". A target's row is
 * named for where the gene comes from: the drug's record says the drug acts on it, or
 * the treatment's name names it. Neither says how a treatment works. */
export function rowLabel(row: GlanceRow, card?: Pick<ExportedCard, "kind" | "reasons">): string {
  if (row === "target") return card && isDrugsTarget(card) ? "Acts on" : "Gene named";
  return ROW_LABELS[row];
}

const ROW_LABELS: Record<Exclude<GlanceRow, "target">, string> = {
  treatment: "Treatment",
  kind: "Kind of treatment",
  drug: "Kind of molecule",
  condition: "Claimed for",
};

/** A vocabulary's title-cased label in sentence case for the row's one line, so a term
 * reads as the claim's own words do. Only a capitalised ordinary word is lowered: an
 * acronym ("DNA") or a symbol keeps its case. The source's label is shown as written
 * in the row's disclosure. */
export function sentenceCase(label: string): string {
  return label
    .split(" ")
    .map((word, index) => (index > 0 && /^[A-Z][a-z]+$/.test(word) ? word.toLowerCase() : word))
    .join(" ");
}

/** A drug record's name as the claim writes it: the rule that matched the card names the
 * claim's own wording of it. Otherwise, as its source writes it. */
export function drugName(card: Pick<ExportedCard, "label" | "reasons">): string {
  const matched = card.reasons.find((reason) => reason.code === "drug_name_equals_name")?.name;
  return matched && matched.toLowerCase() === card.label.toLowerCase() ? matched : card.label;
}

/** A drug card's one line: its kind of molecule, then what its record says it acts on. */
export function drugLine(card: ExportedCard): { value: string; detail: string | null } {
  const kind = moleculeKindText(card);
  const mechanisms = mechanismTexts(card);
  if (kind) return { value: kind, detail: mechanisms.length > 0 ? mechanisms.join("; ") : null };
  return { value: mechanisms.join("; ") || card.label, detail: null };
}

/** One fact in the band's row: what it is and its value. */
export interface BandFact {
  label: string;
  value: string;
  row: GlanceRow;
}

/** The band's row: only what the headline does not already say, the kind of thing the
 * treatment is and a gene, when a card gives them. A drug record's kind of molecule is
 * preferred to a kind card, as it is about the drug itself. No score is shown here,
 * beside the status: each fact's row in "At a glance" carries it. */
export function bandFacts(cards: GlanceCards): BandFact[] {
  const facts: BandFact[] = [];
  const molecule = cards.drug ? moleculeKindText(cards.drug) : null;
  if (cards.drug && molecule) {
    facts.push({ label: rowLabel("drug"), value: molecule, row: "drug" });
  } else if (cards.kind) {
    facts.push({ label: rowLabel("kind"), value: sentenceCase(cards.kind.label), row: "kind" });
  }
  if (cards.target) {
    facts.push({ label: rowLabel("target", cards.target), value: cards.target.label, row: "target" });
  }
  return facts;
}

/** What stands for a score on a card made by rule, after "Term match:". */
const RULE_MATCH_WORDS: Record<string, string> = {
  drug: "by exact name",
  target: "from the drug’s record",
};

/** A row's score, said as being about the term so it is never read as about the
 * treatment: "Term match: high, 81%", or the rule that stands for it. */
export function termMatchText(card: Pick<ExportedCard, "kind" | "score">): string {
  return `Term match: ${card.score === null ? RULE_MATCH_WORDS[card.kind] : matchWords(card.score)}`;
}
