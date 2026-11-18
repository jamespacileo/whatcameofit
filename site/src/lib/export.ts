// The site's only input: the pipeline's export, validated before anything is built.
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { assertClaimFilesFit, SPLIT_RELEASE } from "../../scripts/dist-size.mjs";
import { unlabelledApproaches, unwordedRegistryTypes } from "./approach";
import { clinicalProblems, type Clinical, type ClinicalCategory } from "./clinical";
import { unlabelledPaperCodes } from "./paper-facts";
import { unwordedCardCodes, type ExportedCard, type ExportedCardSource } from "./background";
import { unwordedStatementCodes, type ExportedStatement } from "./statements";
import { REGISTRY_CLAIM_WORDING } from "./registry-claim-wording";
import { unlabelledTrialCodes } from "./trial-facts";
import { unwordedOrganisationCodes, type ExportedOrganisation } from "./organisations";

export type StatusCode =
  | "preclinical_only"
  | "no_trial_found"
  | "trial_registered"
  | "phase_1"
  | "phase_2"
  | "phase_3"
  | "approved"
  | "failed"
  | "terminated"
  | "retracted";

export interface ExportedEvent {
  id: number;
  type: string;
  event_date: string;
  date_basis: string | null;
  summary: string;
  source_name: string;
  source_url: string;
  trial_id: string | null;
  trial_phases: string[];
  trial_state: string | null;
  regulatory_outcome: string | null;
  /** 0 to 1: how sure the pipeline is of the event. Absent or null in an export made
   * before openspec trial-facts; shown only when below 1. */
  confidence?: number | null;
}

/** One group's posted numbers for an outcome, each as the registry wrote it. */
export interface ExportedResultGroup {
  title: string;
  analysed: string | null;
  value: string | null;
  spread: string | null;
  lower: string | null;
  upper: string | null;
}

export interface ExportedComparison {
  /** Titles of the groups compared. */
  groups: string[];
  p_value: string | null;
  method: string | null;
  test: string | null;
}

export interface ExportedResultOutcome {
  title: string;
  time_frame: string | null;
  unit: string | null;
  measure: string | null;
  /** What the spread is, in the registry's words, such as "Standard Deviation". */
  spread_kind: string | null;
  /** How many rows of values the registry posts. Groups are carried only for one. */
  rows: number;
  groups: ExportedResultGroup[];
  comparisons: ExportedComparison[];
}

/** What a trial's registry record states, as codes and the registry's own text. */
export interface ExportedTrialFacts {
  study_kind: string | null;
  participants: { count: number; basis: "actual" | "planned" } | null;
  allocation: string | null;
  masking: string | null;
  comparators: string[];
  healthy_volunteers: boolean | null;
  age_groups: string[];
  /** The name is absent when the sponsor is a person. */
  sponsor: { name: string | null; kind: string | null } | null;
  primary_outcomes: { measure: string; time_frame: string | null }[];
  primary_outcomes_total: number;
  why_stopped: string | null;
  results: { outcomes: ExportedResultOutcome[]; outcomes_total: number } | null;
  /** The record's arms in its order. Absent from an export made before change
   * trials-by-phase; empty for a registry that lists none. */
  arms?: ExportedArm[];
}

/** One arm of a trial, in the record's words. */
export interface ExportedArm {
  label: string | null;
  kind:
    | "experimental"
    | "active_comparator"
    | "placebo_comparator"
    | "sham_comparator"
    | "no_intervention"
    | "other";
  interventions: string[];
}

/** One trial behind a claim's approved events. Openspec trial-facts. */
/** Something a model read from a trial's stored registry record into a fixed code, with
 * the words it read (openspec record-readings). A rule checked the words are in the
 * record before it was stored. The site words the code; the model writes nothing shown. */
export interface ExportedReading {
  kind: "follow_up" | "measure";
  /** Which of the trial's `facts.primary_outcomes` it is about, counted from 0. */
  outcome: number;
  field: "time_frame" | "measure";
  /** The record's own words, exactly as read. */
  words: string;
  number: number | null;
  unit: "days" | "weeks" | "months" | "years" | null;
  code: string | null;
  /** 0 to 1: how sure the reading is. */
  confidence: number;
  read_on: string;
}

export interface ExportedTrial {
  trial_id: string;
  source_name: string;
  url: string;
  title: string | null;
  phases: string[];
  state: string;
  /** When the registry record the facts were read from was fetched. */
  facts_as_of: string | null;
  /** Null for a trial entered by hand, which has no registry record. */
  facts: ExportedTrialFacts | null;
  /** Identifiers of the papers the trial's registry record names, each an entry in the
   * claim's `papers`. Absent from an export made before openspec paper-facts. */
  papers?: string[];
  /** Absent from an export made before openspec record-readings. */
  readings?: ExportedReading[];
  /** Whether the claim's treatment is in the trial's experimental arm or only in its
   * comparator arms, by an exact name match; null when the record cannot tell. Absent
   * from an export made before change trials-by-phase. */
  claim_arm?: "experimental" | "comparator" | null;
}

/** One role a paper plays for a claim. Openspec paper-facts. */
export interface ExportedPaperRole {
  /** "origin", "trial_result", "follow_up" or "related". */
  role: string;
  /** For a trial's results paper: the trial, and how its record came to name the paper. */
  trial_id?: string | null;
  listed?: string | null;
  /** For a follow-up paper: the evidence event it is behind. */
  event_id?: number | null;
  /** For a related paper: the match score, the reasons as codes, and what the search
   * source says of the paper in one line. */
  score?: number | null;
  reasons?: string[];
  decided_by?: string | null;
  summary?: string | null;
}

/** What a paper's index record states of the paper, as codes and the record's own text. */
export interface ExportedPaperFacts {
  title: string | null;
  journal: string | null;
  year: number | null;
  /** Every kind the record gives, most specific first. */
  kinds: string[];
  open_access: boolean | null;
  retracted: boolean;
  /** "people", "animals", both or neither, from the record's subject headings. */
  studied_in: string[];
}

/** One paper a claim page lists, once, whatever brought it there. */
export interface ExportedPaper {
  /** The DOI, else "pmid:<number>", else the search source's own identifier. */
  identifier: string;
  url: string;
  /** The index record the facts were read from. */
  record_url: string | null;
  roles: ExportedPaperRole[];
  facts_as_of: string | null;
  /** Null when the index does not hold the paper. */
  facts: ExportedPaperFacts | null;
}

export interface ExportedMatch {
  source_name: string;
  external_id: string;
  url: string | null;
  /** 0 to 1: how likely the record is evidence for the claim. */
  score: number;
  /** "approved" counts toward the status; "candidate" does not. */
  state: "approved" | "candidate";
  reading: string | null;
  decided_by: string | null;
  summary: string | null;
  /** A trial's record field by field (openspec registry-record-rows). Null until the
   * record has been read into fields; absent from an export made before then. */
  record?: ExportedMatchRecord | null;
}

/** Names as the registry wrote them; phases and state as codes the site words. */
export interface ExportedMatchRecord {
  title: string | null;
  conditions: string[];
  interventions: string[];
  phases: string[];
  state: string;
  /** How many people the record says took part or are planned; null when it says not. */
  participants?: { count: number; basis: "actual" | "planned" } | null;
}

export interface ExportedClaim {
  slug: string;
  headline: string;
  summary: string;
  drafted_from?: "article" | "registry" | "operator" | null;
  has_report?: boolean | null;
  vertical: string;
  /** The kind of intervention, as a code the site words; null when none is recorded. */
  approach: string | null;
  /** What the registry lists the intervention as, when that is the approach. Codes. */
  approach_basis?: { type: string; trials: number } | null;
  /**
   * The claim's clinical categories, as MeSH descriptors with the records that gave
   * each. Empty when its records give none; null or absent when a MeSH record needed to
   * place them has not been read, and then none is shown.
   */
  clinical_categories?: ClinicalCategory[] | null;
  intervention: { name: string; synonyms: string[] };
  indication: string;
  first_reported_date: string | null;
  evidence_stage: string | null;
  /** How the first report was read while the stage is not confirmed: shown marked low
   * confidence, never used for the status. Absent or null when there is nothing to show. */
  evidence_stage_reading?: {
    stage: string;
    score: number;
    also: { stage: string; score: number }[];
  } | null;
  // False for a claim loaded from a seed file or decided by an AI assistant.
  checked_by_person: boolean;
  status: {
    code: StatusCode;
    overlay_years: number | null;
    updated_at: string | null;
    explained_by: number[];
    // The days the status changed, oldest first. Absent from an export made before
    // the pipeline added it.
    history?: { on: string; code: StatusCode }[];
  };
  articles: {
    url: string;
    outlet: string;
    title: string;
    published_date: string;
    archive_url: string | null;
    /** The registry record address of the claim's identified organisation on whose
     * website the report is. Absent or null for any other report, and in an export made
     * before openspec organisations. */
    published_by?: string | null;
  }[];
  promises: { description: string; parsed_date: string | null; article_url: string }[];
  events: ExportedEvent[];
  /** Registry records matched to the claim, approved first, each with its score. Absent
   * from an export made before openspec auto-publish. */
  matches?: ExportedMatch[];
  /** The claim's trials, one per registry identifier. Absent from an export made before
   * openspec trial-facts. */
  trials?: ExportedTrial[];
  /** Each paper the page lists, once. Absent from an export made before openspec
   * paper-facts, which lists its papers among `matches` instead. */
  papers?: ExportedPaper[];
  /** Background cards: at most one for the condition, then one for the intervention.
   * Each says how its term fits: "exact", "broader", or "kind" when it is the term of
   * the kind of treatment and not of the treatment itself (an intervention card only).
   * Absent from an export made before openspec knowledge-cards. */
  background?: ExportedCard[];
  /** Each organisation the claim names, once. Absent from an export made before
   * openspec organisations. */
  organisations?: ExportedOrganisation[];
  /** Approved reported statements, report by report. Absent from an export made before
   * openspec reported-statements. */
  reported_statements?: ExportedStatement[];
  failure_flags: { trial_id: string; source_url: string }[];
}

export interface ExportedVertical {
  slug: string;
  title: string;
  /** The broader area the topic is filed under. Absent or null when it has none. */
  group?: { slug: string; title: string } | null;
}

export interface Export {
  schema_version: number;
  generated_at: string;
  last_checked_at: string | null;
  // Always false since the auto-publish decision. Kept so that an older export, which
  // could be a preview, is still read and refused for the public site.
  preview: boolean;
  sources: { name: string; url: string }[];
  verticals: ExportedVertical[];
  /** Icons of the outlets whose articles are exported, each as a data URI. */
  outlets: { domain: string; icon: string; fetched_at: string }[];
  claims: ExportedClaim[];
  /** The part of the MeSH tree the claims' clinical categories sit in. */
  clinical?: Clinical | null;
  /** Claims the operator took down. Each address answers 410; the reason is never exported. */
  archived?: { slug: string; on: string }[];
  /** Addresses that were a claim's page and now lead to another's: merged into it, or renamed. */
  moved?: { slug: string; to: string }[];
  /** The sources of the claims' background cards, each once. */
  card_sources?: ExportedCardSource[];
  /** The score at or above which a registry match is approved by rule; null when only a
   * person approves one. Absent from an export made before openspec registry-record-rows. */
  match_accept_above?: number | null;
}

// Version 2 introduced the audit hold. Version 3 also carries registry-drafted claims.
const SUPPORTED_SCHEMA_VERSIONS = [2, 3];

type SourceClaim = Omit<ExportedClaim, "headline" | "summary"> & {
  headline: string | null;
  summary: string | null;
};

function wordClaim(claim: SourceClaim): ExportedClaim {
  const hasReport = claim.has_report ?? claim.articles.length > 0;
  const { intervention, indication } = claim;
  return {
    ...claim,
    headline: claim.headline ?? REGISTRY_CLAIM_WORDING.headline(intervention.name, indication),
    summary: claim.summary ?? (hasReport ? "" : REGISTRY_CLAIM_WORDING.summary(intervention.name, indication)),
    has_report: hasReport,
  };
}

function exportPath(): string {
  const configured = process.env.EXPORT_FILE;
  if (configured) return path.resolve(configured);
  const live = path.resolve("data/export.json");
  // The checked-in seed export keeps a fresh checkout buildable before any pipeline run.
  return fs.existsSync(live) ? live : path.resolve("data/seed-export.json");
}

/** The value at a JSON pointer such as "/claims/1/kind". */
function valueAt(content: unknown, pointer: string): unknown {
  return pointer
    .split("/")
    .slice(1)
    .map((part) => part.replace(/~1/g, "/").replace(/~0/g, "~"))
    .reduce<unknown>((value, part) => (value as Record<string, unknown> | undefined)?.[part], content);
}

function load(): { data: Export; exportVersion: string } {
  const file = exportPath();
  const raw = fs.readFileSync(file, "utf8");
  const content = JSON.parse(raw);
  const schema = JSON.parse(fs.readFileSync(path.resolve("export.schema.json"), "utf8"));
  const ajv = new Ajv2020({ allErrors: true });
  addFormats(ajv);
  const validate = ajv.compile(schema);
  if (!validate(content)) {
    const problems = (validate.errors ?? [])
      .slice(0, 10)
      .map((error) => {
        // A code outside a fixed list is named, so the build says which code it was.
        const given =
          error.keyword === "enum" ? ` (it is ${JSON.stringify(valueAt(content, error.instancePath))})` : "";
        return `  ${error.instancePath || "/"} ${error.message}${given}`;
      })
      .join("\n");
    throw new Error(`The export at ${file} does not match export.schema.json:\n${problems}`);
  }
  if (!SUPPORTED_SCHEMA_VERSIONS.includes(content.schema_version)) {
    throw new Error(
      `The export at ${file} has schema version ${content.schema_version}; this site reads versions 2 and 3.`,
    );
  }
  if (!SPLIT_RELEASE) assertClaimFilesFit(content.claims.length);
  const unlabelled = unlabelledApproaches(
    (content as Export).claims.map((claim) => claim.approach),
  );
  if (unlabelled.length > 0) {
    throw new Error(
      `The export at ${file} has approaches the site has no words for: ${unlabelled.join(", ")}. Add them to src/lib/approach.ts.`,
    );
  }
  const clinical = clinicalProblems((content as Export).clinical, (content as Export).claims);
  if (clinical.length > 0) {
    throw new Error(`The export at ${file} cannot be shown by clinical category: ${clinical.join("; ")}.`);
  }
  const unwordedTypes = unwordedRegistryTypes(
    (content as Export).claims.map((claim) => claim.approach_basis?.type),
  );
  if (unwordedTypes.length > 0) {
    throw new Error(
      `The export at ${file} has registry intervention types the site has no words for: ${unwordedTypes.join(", ")}. Add them to src/lib/approach.ts.`,
    );
  }
  const unworded = unlabelledTrialCodes(
    (content as Export).claims.flatMap((claim) => claim.trials ?? []),
  );
  if (unworded.length > 0) {
    throw new Error(
      `The export at ${file} has trial fact codes the site has no words for: ${unworded.join(", ")}. Add them to src/lib/trial-facts.ts.`,
    );
  }
  const unwordedPapers = unlabelledPaperCodes(
    (content as Export).claims.flatMap((claim) => claim.papers ?? []),
  );
  if (unwordedPapers.length > 0) {
    throw new Error(
      `The export at ${file} has paper codes the site has no words for: ${unwordedPapers.join(", ")}. Add them to src/lib/paper-facts.ts.`,
    );
  }
  const unwordedCards = unwordedCardCodes(
    (content as Export).claims.flatMap((claim) => claim.background ?? []),
    (content as Export).card_sources ?? [],
  );
  if (unwordedCards.length > 0) {
    throw new Error(
      `The export at ${file} has background card codes the site has no words for: ${unwordedCards.join(", ")}. Add them to src/lib/background.ts.`,
    );
  }
  const unwordedOrganisations = unwordedOrganisationCodes(
    (content as Export).claims.flatMap((claim) => claim.organisations ?? []),
  );
  if (unwordedOrganisations.length > 0) {
    throw new Error(
      `The export at ${file} has organisation codes the site has no words for: ${unwordedOrganisations.join(", ")}. Add them to src/lib/organisations.ts.`,
    );
  }
  const unwordedStatements = unwordedStatementCodes(
    (content as Export).claims.flatMap((claim) => claim.reported_statements ?? []),
  );
  if (unwordedStatements.length > 0) {
    throw new Error(
      `The export at ${file} has reported statement codes the site has no words for: ${unwordedStatements.join(", ")}. Add them to src/lib/statements.ts.`,
    );
  }
  return {
    data: { ...content, claims: (content.claims as SourceClaim[]).map(wordClaim) } as Export,
    exportVersion: createHash("sha256").update(raw).digest("hex").slice(0, 24),
  };
}

export const { data, exportVersion } = load();

/** Topics that have at least one published claim. Only these are linked from menus and lists. */
export const listedTopics = data.verticals.filter((vertical) =>
  data.claims.some((claim) => claim.vertical === vertical.slug),
);

/** One address per published claim, each given its claim: getStaticPaths for every claim route. */
export function claimPaths() {
  return data.claims.map((claim) => ({ params: { slug: claim.slug }, props: { claim } }));
}

export function verticalTitle(slug: string): string {
  return data.verticals.find((vertical) => vertical.slug === slug)?.title ?? slug;
}
