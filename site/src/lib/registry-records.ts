// Registry records listed on a claim page outside its trials: grouped by how each was
// read, each laid out field by field. Pure. Openspec registry-record-rows.

import { READING_HEADINGS, READING_ORDER, UNREAD_HEADING } from "./confidence.ts";
import type { ExportedMatch, ExportedMatchRecord } from "./export";
import { TRIAL_STATE_WORDS, phaseText, sizeText } from "./trial-facts.ts";

export interface ReadingGroup {
  /** The reading code, or null for records scored before readings were asked. */
  reading: string | null;
  heading: string;
  matches: ExportedMatch[];
}

/** The records in one group per reading, closest to the claim first, each group in the
 * order it was given (the export's: highest score first). An empty group is left out. */
export function groupByReading(matches: ExportedMatch[]): ReadingGroup[] {
  const known = new Set(READING_ORDER);
  const groups: ReadingGroup[] = READING_ORDER.map((reading) => ({
    reading,
    heading: READING_HEADINGS[reading],
    matches: matches.filter((match) => match.reading === reading),
  }));
  groups.push({
    reading: null,
    heading: UNREAD_HEADING,
    matches: matches.filter((match) => !match.reading || !known.has(match.reading)),
  });
  return groups.filter((group) => group.matches.length > 0);
}

export const NO_PHASE_GIVEN = "Phase not given";
export const NOT_READ_YET = "Details not read from the registry yet";
/** Said once above the possible records: none counts, and the rule that would count one,
 * with the score the pipeline's rule needs, so no row reads as a counted trial (openspec
 * registry-record-rows; openspec auto-publish, "Confident candidates are approved by
 * rule"). With the rule off, only a person counts a record. */
export function notCounted(acceptAbove: number | null): string {
  const rule =
    acceptAbove === null
      ? "A record counts only once a person confirms it."
      : `A record counts only when it is read as this treatment for this condition and its match is ${Math.round(acceptAbove * 100)}% or more.`;
  return `None of these is counted in the status, and no person has checked them. ${rule}`;
}
export const NOT_COUNTED_LINK = { href: "/guide/match-and-confidence", text: "How a match is scored" };
/** Records shown in a group before the rest fold away. */
export const RECORDS_SHOWN = 3;

/** What the record lists among its interventions: the treatment, comparators and
 * procedures alike, so it is never worded as what the trial tests. */
export const NAMED_LABEL = "Named in the record";
export const FOR_LABEL = "For";

/** "Phase 2": the record's phase in the site's words. */
export function phaseOf(record: ExportedMatchRecord): string {
  return phaseText(record.phases) ?? NO_PHASE_GIVEN;
}

/** "Under way": the record's state in the trial entries' words. */
export function stateOf(record: ExportedMatchRecord): string {
  return TRIAL_STATE_WORDS[record.state];
}

/** "780 people planned": the record's size in the trials table's words, or null. */
export function sizeOf(record: ExportedMatchRecord): string | null {
  return sizeText(record.participants ?? null);
}
