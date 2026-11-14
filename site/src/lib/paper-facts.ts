// What a paper's index record says of the paper, in the site's own words. The export
// carries codes; the site words them here. Openspec paper-facts and site-publishing:
// an entry says what kind of publication a paper is and how it came to be listed,
// never what it found, and nothing here ranks one paper above another. A paper is not
// a trial record and does not set the status.
import type { ExportedClaim, ExportedPaper, ExportedPaperRole } from "./export";

/** The index the facts are read from, named wherever a fact is shown. */
export const PAPER_INDEX = "Europe PMC";

/** The first kind a record gives is the one shown. */
export const PAPER_KIND_WORDS: Record<string, string> = {
  randomised_trial: "Report of a randomised trial",
  clinical_trial: "Report of a clinical trial",
  meta_analysis: "Meta-analysis",
  systematic_review: "Systematic review",
  review: "Review",
  observational_study: "Observational study",
  case_report: "Case report",
  preprint: "Preprint",
  comment: "Editorial, letter or comment",
  correction: "Correction notice",
  retraction_notice: "Retraction notice",
  article: "Journal article",
};

/** The groups of the papers section, in the order they are shown, each with its heading. */
export const PAPER_ROLE_WORDS: Record<string, string> = {
  origin: "The paper first reported",
  trial_result: "Papers named by a trial's registry record",
  follow_up: "Follow-up papers",
  related: "Related research",
};
const ROLE_ORDER = Object.keys(PAPER_ROLE_WORDS);

/** What a group says of itself, under its heading. */
export const PAPER_ROLE_NOTES: Record<string, string> = {
  origin: "The publication the first news reports were about.",
  trial_result:
    "A trial's sponsor can list a paper as reporting the trial's results. The registry also fills in papers from PubMed, and says those may or may not be about the study.",
  follow_up: "Papers that cite the paper first reported and share an author with it or name the treatment.",
  related:
    "Papers a literature search found for this treatment and condition, with how sure each match is. A score is about the match, not about the treatment.",
};

/** How a trial's registry record came to name a paper. The trial's identifier follows. */
export const LISTED_WORDS: Record<string, string> = {
  listed_by_sponsor: "Listed by the sponsor as reporting results of",
  linked_by_registry: "Linked by the registry from PubMed to",
};

/** A second role a paper plays, said on its entry in the group of its first. */
export const ALSO_WORDS: Record<string, string> = {
  follow_up: "Also a follow-up paper",
  related: "Also found by the literature search",
};

/** What the index's subject headings say the study was in. Attributed to the index. */
export const STUDIED_IN_WORDS: Record<string, string> = {
  people: `${PAPER_INDEX} files it as a study in people`,
  animals: `${PAPER_INDEX} files it as a study in animals`,
  "people+animals": `${PAPER_INDEX} files it as a study in people and in animals`,
};

/** Why the literature search listed a related paper, found by rule. */
export const PAPER_REASON_WORDS: Record<string, string> = {
  named_in_title: "Names the treatment in its title",
  indication_named: "Names the condition",
  named_institution: "From an institution the report names",
  published_before_report: "Published on or before the day of the first report",
};

export const RETRACTED_WORDS = "This paper has been retracted";
export const OPEN_ACCESS_WORDS = "Open access";

/** What the section says of itself, once, above the papers. */
export const PAPERS_NOTE = `Each paper on record for this claim, once. What is said of a paper is read from its ${PAPER_INDEX} record: where it appeared and what kind of publication it is, never what it concluded. A paper is not a trial record and does not set the status.`;

// A build fails rather than say what a paper means for the claim, or that one paper is
// better than another.
const PAPER_VERDICT_WORDS =
  /\b(supports?|supported|confirm\w*|proves?|proved|proven|refut\w*|disprov\w*|work(s|ed)|effective\w*|ineffective\w*|success\w*|fail\w*|promising|breakthrough|cure[sd]?|best|strongest|weakest|high[- ]quality|low[- ]quality|reliable|unreliable|gold standard)\b/i;

export function assertNoPaperVerdict(texts: string[]): void {
  for (const text of texts) {
    const found = text.match(PAPER_VERDICT_WORDS);
    if (found) {
      throw new Error(
        `Verdict wording "${found[0]}" in paper wording: "${text}". Paper facts state what an index record says, never what a paper shows about the claim or how good it is.`,
      );
    }
  }
}

assertNoPaperVerdict([
  ...[
    PAPER_KIND_WORDS,
    PAPER_ROLE_WORDS,
    PAPER_ROLE_NOTES,
    LISTED_WORDS,
    ALSO_WORDS,
    STUDIED_IN_WORDS,
    PAPER_REASON_WORDS,
  ].flatMap((words) => Object.values(words)),
  RETRACTED_WORDS,
  OPEN_ACCESS_WORDS,
  PAPERS_NOTE,
]);

/** Paper codes in the export that the site has no words for, as "kind: code". */
export function unlabelledPaperCodes(papers: ExportedPaper[]): string[] {
  const missing = new Set<string>();
  const check = (kind: string, words: Record<string, string>, code: string | null | undefined) => {
    if (code !== null && code !== undefined && !(code in words)) missing.add(`${kind}: ${code}`);
  };
  for (const paper of papers) {
    for (const role of paper.roles) {
      check("paper role", PAPER_ROLE_WORDS, role.role);
      check("how listed", LISTED_WORDS, role.listed);
      for (const reason of role.reasons ?? []) check("paper reason", PAPER_REASON_WORDS, reason);
    }
    for (const kind of paper.facts?.kinds ?? []) check("paper kind", PAPER_KIND_WORDS, kind);
    for (const subject of paper.facts?.studied_in ?? []) check("studied in", STUDIED_IN_WORDS, subject);
  }
  return [...missing].sort();
}

/** The address of a paper's entry on its claim page. */
export function paperAnchor(identifier: string): string {
  return `paper-${identifier.replace(/[^A-Za-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;
}

/** What to call a paper whose index record is not held: its DOI, or its PubMed number. */
export function paperName(paper: ExportedPaper): string {
  if (paper.facts?.title) return paper.facts.title;
  if (paper.identifier.startsWith("pmid:")) return `PubMed ${paper.identifier.slice(5)}`;
  if (paper.identifier.startsWith("openalex:")) return `OpenAlex ${paper.identifier.slice(9)}`;
  return paper.identifier;
}

/** "Report of a randomised trial · The Example Journal · 2022". Null when the record
 * states none of it or is not held. */
export function paperStanding(paper: ExportedPaper): string | null {
  const facts = paper.facts;
  if (!facts) return null;
  const kind = facts.kinds.length > 0 ? PAPER_KIND_WORDS[facts.kinds[0]] : null;
  const parts = [kind, facts.journal, facts.year === null ? null : String(facts.year)].filter(
    (part): part is string => Boolean(part),
  );
  return parts.length > 0 ? parts.join(" · ") : null;
}

/** What the index says the study was in, or null when it says neither. */
export function studiedInText(paper: ExportedPaper): string | null {
  const subjects = paper.facts?.studied_in ?? [];
  if (subjects.length === 0) return null;
  return STUDIED_IN_WORDS[subjects.join("+")] ?? null;
}

export interface PaperGroup {
  role: string;
  heading: string;
  note: string;
  papers: ExportedPaper[];
}

/** The claim's papers by the first role each plays, so that each is listed once. The
 * order within a group is the export's. */
export function groupPapers(papers: ExportedPaper[]): PaperGroup[] {
  return ROLE_ORDER.map((role) => ({
    role,
    heading: PAPER_ROLE_WORDS[role],
    note: PAPER_ROLE_NOTES[role],
    papers: papers.filter((paper) => paper.roles[0]?.role === role),
  })).filter((group) => group.papers.length > 0);
}

/** The roles of a paper that name a trial, for the line that links back to it. */
export function trialRoles(paper: ExportedPaper): ExportedPaperRole[] {
  return paper.roles.filter((role) => role.role === "trial_result" && role.trial_id);
}

export interface SubjectCount {
  /** The claim's trials, and its papers the index files as studies in people. */
  people: number;
  /** The claim's papers the index files as studies in animals. */
  animals: number;
}

/** Counts of records, never of people or of studies: a trial and the paper that reports
 * it are two records. */
export function countSubjects(claim: Pick<ExportedClaim, "trials" | "papers">): SubjectCount {
  const papers = claim.papers ?? [];
  const filed = (subject: string) =>
    papers.filter((paper) => paper.facts?.studied_in.includes(subject)).length;
  return { people: (claim.trials ?? []).length + filed("people"), animals: filed("animals") };
}

/** "3 in people · 1 in animals". Null when the claim has no such record. */
export function subjectCountText(tally: SubjectCount): string | null {
  const parts = [
    tally.people > 0 ? `${tally.people.toLocaleString("en-GB")} in people` : null,
    tally.animals > 0 ? `${tally.animals.toLocaleString("en-GB")} in animals` : null,
  ].filter((part): part is string => part !== null);
  return parts.length > 0 ? parts.join(" · ") : null;
}

/** How many papers of a group the page shows before the rest go behind one press. */
export const PAPERS_SHOWN = 5;
