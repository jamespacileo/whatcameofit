// The site's only input: the pipeline's export, validated before anything is built.
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

export type StatusCode =
  | "preclinical_only"
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

export interface ExportedClaim {
  slug: string;
  headline: string;
  summary: string;
  vertical: string;
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
