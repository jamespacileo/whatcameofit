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
  scoreLabel,
  type ExportedCard,
  type ExportedCardSource,
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

/** A row's score, said as being about the term: "Term match: high, 81%". */
export function termMatchText(card: Pick<ExportedCard, "kind" | "score">): string {
  return scoreLabel(card, matchWords);
}

/** The scores a row's grey line shows, one per card in the row, each naming what was
 * matched. A drug row's value is what the drug's record says, so its first score is the
 * record's ("Drug record: by exact name"), never the kind of molecule's; a kind card
 * inside the same row keeps its own score in sight ("Kind term: high, 94%"). */
export function rowMatchTexts(cards: Pick<ExportedCard, "kind" | "score">[]): string[] {
  const [first, ...rest] = cards;
  if (!first) return [];
  if (first.kind !== "drug") return [termMatchText(first)];
  const words = (card: Pick<ExportedCard, "kind" | "score">) =>
    termMatchText(card).replace(/^Term match: /, "");
  return [`Drug record: ${words(first)}`, ...rest.map((card) => `Kind term: ${words(card)}`)];
}

/** A source's short name for a row's grey line: the abbreviation its title gives in
 * brackets ("MeSH"), or its title up to any "through …" ("ChEMBL"). The full credit is
 * inside the row's disclosure. */
export function sourceName(source: Pick<ExportedCardSource, "title">): string {
  const bracketed = source.title.match(/\(([^)]+)\)\s*$/);
  return bracketed ? bracketed[1] : source.title.split(",")[0];
}

/** A definition this long or shorter is shown whole in its row and not again in the
 * card; a longer one is shown in its row cut to three lines, and whole in the card. */
export const SHORT_DEFINITION = 240;

/** The source's term for a row matched from the claim's own words (the treatment, the
 * drug, the condition), when it differs from those words other than in case: the claim
 * says "Lung cancer", the vocabulary files it as "Lung Neoplasms". Otherwise null. */
export function filedAs(row: GlanceRow, card: Pick<ExportedCard, "label">, claimWords: string): string | null {
  if (row !== "treatment" && row !== "drug" && row !== "condition") return null;
  return card.label.toLowerCase() === claimWords.toLowerCase() ? null : card.label;
}

/** The start of a row's grey line: whose words the definition above it is, or, with no
 * definition in the row, which source the term is from. A gene's definition says what
 * its product does, as its card does. */
export function wordsLine(card: Pick<ExportedCard, "kind">, source: Pick<ExportedCardSource, "title">, withWords: boolean): string {
  const name = sourceName(source);
  if (!withWords) return `From ${name}`;
  const whose = name.endsWith("s") ? `${name}’` : `${name}’s`;
  return card.kind === "target" ? `What this gene’s product does, in ${whose} words` : `In ${whose} words`;
}
