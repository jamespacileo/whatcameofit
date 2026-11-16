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
export const NOT_READ_YET = "Its registry record has not been read into fields yet.";

/** "Phase 2", "Under way": the record's phase and state in the site's words. */
export function standingOf(record: ExportedMatchRecord): string[] {
  return [phaseText(record.phases) ?? NO_PHASE_GIVEN, TRIAL_STATE_WORDS[record.state]];
}
