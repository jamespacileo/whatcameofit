// The site's only input: the pipeline's export, validated before anything is built.
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { unlabelledApproaches } from "./approach";
import { unlabelledTrialCodes } from "./trial-facts";

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
}

/** One trial behind a claim's approved events. Openspec trial-facts. */
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
}

export interface ExportedClaim {
  slug: string;
  headline: string;
  summary: string;
  vertical: string;
  /** The kind of intervention, as a code the site words; null when none is recorded. */
  approach: string | null;
  intervention: { name: string; synonyms: string[] };
  indication: string;
  first_reported_date: string | null;
  evidence_stage: string | null;
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
  }[];
  promises: { description: string; parsed_date: string | null; article_url: string }[];
  events: ExportedEvent[];
  /** Registry records matched to the claim, approved first, each with its score. Absent
   * from an export made before openspec auto-publish. */
  matches?: ExportedMatch[];
  /** The claim's trials, one per registry identifier. Absent from an export made before
   * openspec trial-facts. */
  trials?: ExportedTrial[];
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
  // True when the export holds claims an AI assistant decided. Never for the public site.
  preview: boolean;
  sources: { name: string; url: string }[];
  verticals: ExportedVertical[];
  /** Icons of the outlets whose articles are exported, each as a data URI. */
  outlets: { domain: string; icon: string; fetched_at: string }[];
  claims: ExportedClaim[];
  /** Claims the operator took down. Each address answers 410; the reason is never exported. */
  archived?: { slug: string; on: string }[];
}

const SUPPORTED_SCHEMA_VERSION = 1;

function exportPath(): string {
  const configured = process.env.EXPORT_FILE;
  if (configured) return path.resolve(configured);
  const live = path.resolve("data/export.json");
  // The checked-in seed export keeps a fresh checkout buildable before any pipeline run.
  return fs.existsSync(live) ? live : path.resolve("data/seed-export.json");
}

function load(): Export {
  const file = exportPath();
  const content = JSON.parse(fs.readFileSync(file, "utf8"));
  const schema = JSON.parse(fs.readFileSync(path.resolve("export.schema.json"), "utf8"));
  const ajv = new Ajv2020({ allErrors: true });
  addFormats(ajv);
  const validate = ajv.compile(schema);
  if (!validate(content)) {
    const problems = (validate.errors ?? [])
      .slice(0, 10)
      .map((error) => `  ${error.instancePath || "/"} ${error.message}`)
      .join("\n");
    throw new Error(`The export at ${file} does not match export.schema.json:\n${problems}`);
  }
  if (content.schema_version !== SUPPORTED_SCHEMA_VERSION) {
    throw new Error(
      `The export at ${file} has schema version ${content.schema_version}; this site reads version ${SUPPORTED_SCHEMA_VERSION}.`,
    );
  }
  const unlabelled = unlabelledApproaches(
    (content as Export).claims.map((claim) => claim.approach),
  );
  if (unlabelled.length > 0) {
    throw new Error(
      `The export at ${file} has approaches the site has no words for: ${unlabelled.join(", ")}. Add them to src/lib/approach.ts.`,
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
  return content as Export;
}

export const data: Export = load();

/** Topics that have at least one published claim. Only these are linked from menus and lists. */
export const listedTopics = data.verticals.filter((vertical) =>
  data.claims.some((claim) => claim.vertical === vertical.slug),
);

export function verticalTitle(slug: string): string {
  return data.verticals.find((vertical) => vertical.slug === slug)?.title ?? slug;
}
