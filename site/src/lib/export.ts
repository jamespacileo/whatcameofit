// The site's only input: the pipeline's export, validated before anything is built.
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { unlabelledApproaches } from "./approach";

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
  return content as Export;
}

export const data: Export = load();

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
