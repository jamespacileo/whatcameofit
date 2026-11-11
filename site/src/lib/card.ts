// What the status card says, in one place: the three image shapes and their text
// alternative are all built from this, so they cannot disagree.
import type { ExportedClaim } from "./export";
import { assertNeutral } from "./status.ts";

export interface CardFact {
  label: string;
  value: string;
}

export interface CardContent {
  /** The earliest article's title as the outlet wrote it, or null when the claim has no article. */
  quote: string | null;
  outlet: string | null;
  /** The claim's own headline: shown only when there is no article to quote. */
  headline: string;
  status: string;
  /** The no-signal note in the site's wording, when it applies. */
  note: string | null;
  facts: CardFact[];
}

/** Carried by everything that leaves the site, where the footer notices cannot follow. */
export const CARD_NOTICE = "Not medical advice";

const LABELS = {
  first: "First reported",
  promised: "Promised by",
  status: "Status now",
  checked: "Checked",
};

// The card's own words are held to the same rule as status labels: a build fails
// rather than publish a verdict.
assertNeutral([CARD_NOTICE, ...Object.values(LABELS)]);

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "Nov 2026": the month a date falls in. A card is dated, never counted from. */
export function monthAndYear(isoDate: string): string {
  const [year, month] = isoDate.slice(0, 10).split("-").map(Number);
  return `${MONTHS[month - 1]} ${year}`;
}

export function cardContent(
  claim: ExportedClaim,
  statusLabel: string,
  note: string | null,
  latestPromiseDate: string | null,
  lastCheckedAt: string | null,
): CardContent {
  // The earliest report is the one readers remember the claim by.
  const earliest = [...claim.articles].sort((a, b) =>
    a.published_date < b.published_date ? -1 : a.published_date > b.published_date ? 1 : 0,
  )[0];

  const facts: CardFact[] = [];
  if (claim.first_reported_date) {
    facts.push({ label: LABELS.first, value: claim.first_reported_date.slice(0, 4) });
  }
  // A promise is shown as the year it names, never as a count of days: a count would
  // be wrong the day after the image was made.
  if (latestPromiseDate) {
    facts.push({ label: LABELS.promised, value: latestPromiseDate.slice(0, 4) });
  }
  facts.push({ label: LABELS.status, value: statusLabel });
  if (lastCheckedAt) facts.push({ label: LABELS.checked, value: monthAndYear(lastCheckedAt) });

  return {
    quote: earliest?.title ?? null,
    outlet: earliest?.outlet ?? null,
    headline: claim.headline,
    status: statusLabel,
    note,
    facts,
  };
}

/** The same facts as the image, as one line of text. */
export function cardAlt(card: CardContent): string {
  const lead = card.quote ? `“${card.quote}” (${card.outlet})` : card.headline;
  const facts = card.facts.map((fact) => `${fact.label} ${fact.value}`);
  return [lead, ...facts, ...(card.note ? [card.note] : []), CARD_NOTICE].join(". ") + ".";
}

/** A long title ends at a word, with an ellipsis, so the status below it is never pushed out. */
export function clip(text: string, max: number): string {
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  return `${cut.slice(0, Math.max(cut.lastIndexOf(" "), max - 20)).replace(/[\s,;:.]+$/, "")}…`;
}

/**
 * One sentence a reader can paste anywhere: when the claim was first reported, where it
 * stands, when that was checked, and where to read the records. Dated, so it stays true.
 */
export function shareSentence(
  claim: ExportedClaim,
  statusLabel: string,
  lastCheckedAt: string | null,
  address: string,
): string {
  const headline = claim.headline.replace(/[.\s]+$/, "");
  const reported = claim.first_reported_date
    ? ` First reported ${monthAndYear(claim.first_reported_date)}.`
    : "";
  const checked = lastCheckedAt ? ` when checked in ${monthAndYear(lastCheckedAt)}` : "";
  return `${headline}.${reported} Status${checked}: ${statusLabel}. ${CARD_NOTICE}. ${address}`;
}
