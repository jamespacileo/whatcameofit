// The site's words for a record reading (openspec record-readings): what a model read
// from a trial's stored registry record into a fixed code, checked by rule before it was
// stored. One place words a measure, so "The record in brief" and a trial's entry cannot
// say it differently. The model writes nothing a reader sees (docs/adr/0003).

import type { ExportedReading, ExportedTrial } from "./export";
import { assertNeutral } from "./status.ts";

/** The site's phrase for each kind of measure a reading can name: as stated, and as a
 * change when the registry's title names a change. "other" has no phrase. */
export const MEASURE_PHRASES: Record<string, { plain: string; change: string }> = {
  symptom_score: { plain: "A symptom score", change: "The change in a symptom score" },
  frequency: { plain: "How often an event happened", change: "The change in how often an event happened" },
  body_measure: {
    plain: "A body measurement or lab value",
    change: "The change in a body measurement or lab value",
  },
  scan_finding: { plain: "What a scan or image showed", change: "The change in what a scan or image showed" },
  survival: {
    plain: "How long until an event, such as the illness getting worse or death",
    change: "How long until an event, such as the illness getting worse or death",
  },
  side_effects: { plain: "Side effects", change: "The change in side effects" },
  use_of_treatment: { plain: "How much the treatment was used", change: "How much the treatment was used" },
  quality_of_life: { plain: "A quality-of-life score", change: "The change in a quality-of-life score" },
  physical_test: {
    plain: "A test of what the body can do, such as walking",
    change: "The change in a test of what the body can do, such as walking",
  },
};

/** A reading less sure than this is not used; the page gives the registry's own words. */
export const READING_SHOWN_FROM = 0.5;

const READING_BANDS = [
  { from: 0.5, word: "likely" },
  { from: 0.8, word: "very likely" },
] as const;

/** A reading is a model's, and its confidence is the model's own figure: it is never
 * shown as certain, whatever the model says. */
const MOST_SURE = 99;

/** "very likely · 92%": how sure a reading is. Never how sure a result is. */
export function readingConfidenceLabel(confidence: number): string {
  let word: string = READING_BANDS[0].word;
  for (const band of READING_BANDS) if (confidence >= band.from) word = band.word;
  return `${word} · ${Math.min(MOST_SURE, Math.round(confidence * 100))}%`;
}

const usable = (reading: ExportedReading | undefined): reading is ExportedReading =>
  Boolean(reading && reading.confidence >= READING_SHOWN_FROM);

export interface MeasureWords {
  /** "The change in a symptom score". */
  phrase: string;
  /** " over 4 weeks" (", followed for 4 years" for a time until an event), or nothing when no
   * follow-up was read. The number and its unit do not part. */
  over: string;
  /** The registry's own title for the measure, and its time frame when the follow-up was read from it. */
  measure: string;
  timeFrame: string | null;
  /** How sure the reading is: the less sure of the two when both are used. */
  confidence: number;
}

/** What one of a trial's main measures is, in the site's words, from its readings. Null
 * with no usable reading of its kind, or a kind the site has no phrase for. */
export function measureWords(trial: ExportedTrial, outcomeIndex: number): MeasureWords | null {
  const outcome = trial.facts?.primary_outcomes[outcomeIndex];
  if (!outcome) return null;
  const about = (trial.readings ?? []).filter((reading) => reading.outcome === outcomeIndex);
  const measure = about.find((reading) => reading.kind === "measure");
  const followUp = about.find((reading) => reading.kind === "follow_up");
  const phrase = usable(measure) && measure.code ? MEASURE_PHRASES[measure.code] : undefined;
  if (!phrase || !usable(measure)) return null;
  // Whether the measure is a change is read by rule from the registry's title.
  const isChange = /\bchange\b/i.test(outcome.measure);
  const timed = usable(followUp) && followUp.number !== null && followUp.unit !== null;
  const unit = timed ? (followUp.number === 1 ? followUp.unit!.slice(0, -1) : followUp.unit) : "";
  return {
    phrase: isChange ? phrase.change : phrase.plain,
    // A time until an event is not measured "over" a period: people are followed for one.
    over: timed
      ? `${measure.code === "survival" ? ", followed for" : " over"} ${followUp.number!.toLocaleString("en-GB")} ${unit}`
      : "",
    measure: outcome.measure,
    timeFrame: timed ? outcome.time_frame : null,
    confidence: timed ? Math.min(measure.confidence, followUp.confidence) : measure.confidence,
  };
}

// A build fails rather than publish a verdict in the words for a measure.
assertNeutral(Object.values(MEASURE_PHRASES).flatMap((phrase) => [phrase.plain, phrase.change]));
