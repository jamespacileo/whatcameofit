// What the status card says, in one place: the three image shapes and their text
// alternative are all built from this, so they cannot disagree.
import { assertNeutral } from "./status.ts";
import { MONTHS } from "./timetable.ts";

export interface CardFact {
  label: string;
  value: string;
}

export interface CardContent {
  /** A report's title as its outlet wrote it. The first version holds no reports, so null. */
  quote: string | null;
  outlet: string | null;
  /** The pair's name: shown when there is no report to quote. */
  headline: string;
  status: string;
  /** The no-signal note in the site's wording, when it applies. */
  note: string | null;
  facts: CardFact[];
  /** The status's place on the path, counted from 1, or null when it is off the path. */
  place?: number | null;
}

/** Carried by everything that leaves the site, where the footer notices cannot follow. */
export const CARD_NOTICE = "Not medical advice";

const LABELS = {
  first: "First reported",
  promised: "Promised by",
  status: "Status now",
  checked: "Checked",
};

/** The card draws this one fact on pale amber, so it is found by its label. */
export const PROMISED_LABEL = LABELS.promised;

// The card's own words are held to the same rule as status labels: a build fails
// rather than publish a verdict.
assertNeutral([CARD_NOTICE, ...Object.values(LABELS)]);

/** "Nov 2026": the month a date falls in. A card is dated, never counted from. */
export function monthAndYear(isoDate: string): string {
  const [year, month] = isoDate.slice(0, 10).split("-").map(Number);
  return `${MONTHS[month - 1]} ${year}`;
}

/** The same facts as the image, as one line of text. */
export function cardAlt(card: CardContent): string {
  const lead = card.quote ? `“${card.quote}” (${card.outlet})` : card.headline;
  const facts = card.facts.map((fact) => `${fact.label} ${fact.value}`);
  return [lead, ...facts, ...(card.note ? [card.note] : []), CARD_NOTICE].join(". ") + ".";
}

/** What a pair's card says (openspec pairs-site): the pair's name in place of a report's
 * title, its status, how many trials it rests on, and the day the status was worked out.
 * The first version holds no reports, so the card quotes none. */
export function pairCardContent(
  headline: string,
  statusLabel: string,
  note: string | null,
  trials: number,
  asOf: string,
): CardContent {
  return {
    quote: null,
    outlet: null,
    headline,
    status: statusLabel,
    note,
    facts: [
      { label: LABELS.status, value: statusLabel },
      { label: "Trials", value: String(trials) },
      { label: LABELS.checked, value: monthAndYear(asOf) },
    ],
  };
}

/** A long title ends at a word, with an ellipsis, so the status below it is never pushed out. */
export function clip(text: string, max: number): string {
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  return `${cut.slice(0, Math.max(cut.lastIndexOf(" "), max - 20)).replace(/[\s,;:.]+$/, "")}…`;
}

/**
 * One sentence a reader can paste anywhere: what is followed, where it stands, when that
 * was worked out, and where to read the records. Dated, so it stays true.
 */
export function shareSentence(title: string, statusLabel: string, asOf: string, address: string): string {
  return `${title.replace(/[.\s]+$/, "")}. Status when checked in ${monthAndYear(asOf)}: ${statusLabel}. ${CARD_NOTICE}. ${address}`;
}
