// "At a glance": what the claim's treatment and condition are, from its background
// cards, at the top of the claim page and as one row in the record band. The cards
// keep their own words and scores; this module only sorts them into rows and words
// the row labels. Openspec knowledge-cards, site-publishing: "At a glance".
import { isDrugsTarget, moleculeKindText, scoreLabel, type ExportedCard } from "./background";
import { confidenceLabel } from "./confidence";

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

/** A target's row is named for where the gene comes from: the drug's record says the
 * drug acts on it, or the treatment's name names it. Neither says how a treatment works. */
export function targetRowLabel(card: Pick<ExportedCard, "kind" | "reasons">): string {
  return isDrugsTarget(card) ? "Acts on, as the drug’s record says" : "Gene named in its name";
}

export const ROW_LABELS: Record<Exclude<GlanceRow, "target">, string> = {
  treatment: "Treatment",
  kind: "Kind of treatment",
  drug: "Drug record",
  condition: "Claimed for",
};

/** One fact in the band's row: what it is, its value, and how sure the link is when
 * the value comes from a card. */
export interface BandFact {
  label: string;
  value: string;
  /** "High match · 81%", or what stands for a score on a card made by rule. */
  note: string | null;
  row: GlanceRow;
}

/** The band's row: the treatment and the condition always, the kind and a gene when a
 * card gives them. A drug record's kind of molecule is preferred to a kind card, as it
 * is about the drug itself. */
export function bandFacts(
  claim: { intervention: { name: string }; indication: string },
  cards: GlanceCards,
): BandFact[] {
  const facts: BandFact[] = [
    { label: "Treatment", value: claim.intervention.name, note: null, row: "treatment" },
  ];
  const molecule = cards.drug ? moleculeKindText(cards.drug) : null;
  if (cards.drug && molecule) {
    facts.push({ label: "Kind", value: molecule, note: scoreLabel(cards.drug, confidenceLabel), row: "drug" });
  } else if (cards.kind) {
    facts.push({ label: "Kind", value: cards.kind.label, note: scoreLabel(cards.kind, confidenceLabel), row: "kind" });
  }
  if (cards.target) {
    facts.push({
      label: isDrugsTarget(cards.target) ? "Acts on" : "Gene named",
      value: cards.target.label,
      note: scoreLabel(cards.target, confidenceLabel),
      row: "target",
    });
  }
  facts.push({ label: "Claimed for", value: claim.indication, note: null, row: "condition" });
  return facts;
}
