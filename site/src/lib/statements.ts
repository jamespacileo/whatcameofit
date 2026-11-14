// The site's wording for reported statements. Openspec reported-statements and
// site-publishing: the export carries a statement's text, in the pipeline's own words,
// and codes for its kind, firmness, speaker and basis. The site words every code and
// frames every statement as what its report said, so the framing cannot be dropped by a
// statement's own text. Nothing here compares a statement with a record or says
// whether it held.
import { assertNeutral } from "./status.ts";
import { assertNoOutcomeVerdict } from "./trial-facts.ts";

export interface ExportedStatement {
  /** In the pipeline's own words, never a quotation of the report. */
  text: string;
  kind: string;
  firmness: string;
  /** A role, never a name. */
  speaker: string;
  /** What the report said the statement rests on. */
  basis: string;
  /** The automatic check's probability that the report says this. */
  confidence: number;
  article_url: string;
  /** When the report was read for it. */
  read_on: string;
}

/** What a statement is about, as the grey line above it. */
export const KIND_WORDS: Record<string, string> = {
  effect: "Effect",
  safety: "Safety",
  how_it_works: "How it acts",
  who_it_could_help: "Who it could help",
  comparison: "Compared with existing treatment",
  what_it_could_lead_to: "What it could lead to",
};

/** Who the report had saying it, by role. */
const SPEAKER_WORDS: Record<string, string> = {
  article: "The report",
  researcher: "a researcher",
  company: "the company",
  patient: "a patient",
  other_expert: "another expert",
};

/** How firmly the report put it, completing the attribution's opening words. */
const FIRMNESS_WORDS: Record<string, { own: string; theirs: string }> = {
  fact: { own: "said", theirs: "saying" },
  possibility: { own: "said this could be so", theirs: "saying this could be so" },
};

/** What the report gave as the statement's basis, always as the report's. */
export const BASIS_WORDS: Record<string, string> = {
  people: "The report gave a study in people as its basis.",
  animals: "The report gave a study in animals as its basis.",
  laboratory: "The report gave laboratory work as its basis.",
  not_said: "The report did not say what this rests on.",
};

/** Bands of how sure the check is, lowest first: a confidence at or above `from` takes the word. */
const CONFIDENCE_BANDS = [
  { from: 0, word: "Unsure it is in the report" },
  { from: 0.5, word: "Likely in the report" },
  { from: 0.8, word: "Very likely in the report" },
] as const;

/** The section's heading. */
export function statementsHeading(reports: number): string {
  return reports > 1 ? "What the reports said" : "What the report said";
}

/** What the section says of itself, once, under its heading. */
export function statementsNote(reports: number): string {
  const said = reports > 1 ? "What the news reports said" : "What the news report said";
  return `${said} about the treatment, in this site’s words and never quoted. A report’s statement is not a record: the records follow. Each statement was read from its report by an AI model and checked against the report automatically, and shows how sure that check is. Not medical advice.`;
}

/** What the confidence means, in the panel it opens. */
export function confidenceMeaning(readOn: string): string {
  return `How sure an automatic check is that the report says this, as firmly as it is put here, from reading the report on ${readOn}. It is about the reading of the report, not about the treatment.`;
}

/** The opening words that attribute a statement to its report: "The report said:",
 * or "The report had a researcher saying this could be so:". */
export function attributionText(statement: Pick<ExportedStatement, "speaker" | "firmness">): string {
  const firmness = FIRMNESS_WORDS[statement.firmness];
  if (statement.speaker === "article") return `The report ${firmness.own}:`;
  return `The report had ${SPEAKER_WORDS[statement.speaker]} ${firmness.theirs}:`;
}

/** "Very likely in the report · 92%". */
export function statementConfidenceLabel(confidence: number): string {
  let word: string = CONFIDENCE_BANDS[0].word;
  for (const band of CONFIDENCE_BANDS) if (confidence >= band.from) word = band.word;
  return `${word} · ${Math.round(confidence * 100)}%`;
}

/** Statement codes in the export that the site has no words for, as "field: code". */
export function unwordedStatementCodes(
  statements: Pick<ExportedStatement, "kind" | "firmness" | "speaker" | "basis">[],
): string[] {
  const missing = new Set<string>();
  for (const statement of statements) {
    if (!(statement.kind in KIND_WORDS)) missing.add(`statement kind: ${statement.kind}`);
    if (!(statement.firmness in FIRMNESS_WORDS)) missing.add(`statement firmness: ${statement.firmness}`);
    if (!(statement.speaker in SPEAKER_WORDS)) missing.add(`statement speaker: ${statement.speaker}`);
    if (!(statement.basis in BASIS_WORDS)) missing.add(`statement basis: ${statement.basis}`);
  }
  return [...missing].sort();
}

/** Words that would compare a report's statement with a record, or say whether it held. */
const COMPARISON_WORDS =
  /\b(confirm\w*|contradict\w*|consistent|inconsistent|held up|borne out|refut\w*|disprove\w*|verif\w*|accurate|inaccurate|true|false|correct|wrong|right|support(s|ed)?)\b/i;

export function assertNoComparison(texts: string[]): void {
  for (const text of texts) {
    const found = text.match(COMPARISON_WORDS);
    if (found) {
      throw new Error(
        `Comparison wording "${found[0]}" in statement wording: "${text}". A report's statement is shown as what the report said, never held against a record.`,
      );
    }
  }
}

// The site's own words about statements: no verdict, no outcome, no comparison.
const SITE_WORDS = [
  ...Object.values(KIND_WORDS),
  ...Object.values(BASIS_WORDS),
  ...CONFIDENCE_BANDS.map((band) => band.word),
  ...Object.keys(SPEAKER_WORDS).flatMap((speaker) =>
    Object.keys(FIRMNESS_WORDS).map((firmness) => attributionText({ speaker, firmness })),
  ),
  statementsHeading(1),
  statementsHeading(2),
  statementsNote(1),
  statementsNote(2),
  confidenceMeaning("14 November 2026"),
];
assertNeutral(SITE_WORDS);
assertNoOutcomeVerdict(SITE_WORDS);
assertNoComparison(SITE_WORDS);
