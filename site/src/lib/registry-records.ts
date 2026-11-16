// Registry records listed on a claim page outside its trials: grouped by how each was
// read, each laid out field by field. Pure. Openspec registry-record-rows.

import { READING_HEADINGS, READING_ORDER, UNREAD_HEADING } from "./confidence.ts";
import type { ExportedMatch, ExportedMatchRecord } from "./export";
import { TRIAL_STATE_WORDS, phaseText } from "./trial-facts.ts";

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
/** Said once above the possible records, with the rule that would have counted them,
 * so no row reads as a counted trial (openspec auto-publish, "Confident candidates are
 * approved by rule"). */
export const NOT_COUNTED =
  "None of these is counted in the status. A rule counts a record only when it is read as this treatment for this condition with a high enough score, and no person has confirmed these.";
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
