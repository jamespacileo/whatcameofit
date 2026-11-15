// How sure the pipeline is that a registry record is evidence for a claim, in the
// site's own words. The export carries the score; the site words it. Openspec
// auto-publish: "Confidence is shown with every match". Never a verdict on the
// treatment: a score says how well a record matches the reported treatment and
// condition, nothing about whether the treatment works.

/** Score bands, lowest first: a score at or above `from` takes the word. */
const CONFIDENCE_BANDS = [
  { from: 0, word: "Low match" },
  { from: 0.5, word: "Medium match" },
  { from: 0.8, word: "High match" },
] as const;

type Band =(typeof CONFIDENCE_BANDS)[number]["word"];

export function bandOf(score: number): Band {
  let word: Band = CONFIDENCE_BANDS[0].word;
  for (const band of CONFIDENCE_BANDS) if (score >= band.from) word = band.word;
  return word;
}

/** "High match · 92%". */
export function confidenceLabel(score: number): string {
  return `${bandOf(score)} · ${Math.round(score * 100)}%`;
}

/** "high, 92%": the band and the score, for a note that already says it is a match. */
export function matchWords(score: number): string {
  return `${bandOf(score).replace(" match", "").toLowerCase()}, ${Math.round(score * 100)}%`;
}

/** "Match to this claim: high, 92%": a score read as a note about the match, never as a
 * mark beside a title (openspec: "A match score reads as a note about the match"). */
export function matchNote(score: number): string {
  return `Match to this claim: ${matchWords(score)}`;
}

/** Why the record scored as it did, from how it was read. */
const READINGS:Record<string, string> = {
  match: "Read as a study of this treatment for this condition.",
  other_indication: "Read as the same treatment studied for a different condition, patient group or treatment setting.",
  not_a_match: "Read as a study of something else.",
};

const UNREAD ="Scored before the condition was part of the question.";

export function readingOf(reading: string | null): string {
  return (reading && READINGS[reading]) ?? UNREAD;
}
