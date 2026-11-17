// The trial listing: the pipeline's file of one named set of stored trials, validated
// before anything is built from it. It stands beside the export it was written with:
// data/published-export.json has data/published-trials-listing.json. A build with no
// listing beside its export has no listed trials, and no page opens for an uncited one.
// Behaviour: openspec trial-pages, "A trial listing built into the site".
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { LISTED_TRIAL_PAGES } from "../../site.config.mjs";

export type ListedRow = [
  id: string,
  title: string,
  acronym: string | null,
  phases: string[],
  state: string,
  updated: string | null,
  conditions: string[],
  interventions: string[],
  claim: string | null,
];

export interface TrialsListing {
  schema_version: 1;
  set: string;
  registry: string;
  records_read: string | null;
  columns: string[];
  trials: ListedRow[];
}

const EMPTY: TrialsListing = {
  schema_version: 1,
  set: "",
  registry: "clinicaltrials.gov",
  records_read: null,
  columns: ["id", "title", "acronym", "phases", "state", "updated", "conditions", "interventions", "claim"],
  trials: [],
};

/** Where the listing is: named outright, or beside the export under the export's name
 * with "export" replaced by "trials-listing". */
export function listingPath(): string | null {
  const configured = process.env.TRIALS_LISTING_FILE;
  if (configured) return path.resolve(configured);
  const live = path.resolve("data/export.json");
  const exported = process.env.EXPORT_FILE
    ? path.resolve(process.env.EXPORT_FILE)
    : fs.existsSync(live)
      ? live
      : path.resolve("data/seed-export.json");
  const name = path.basename(exported);
  const beside = name.replace(/export(?=\.json$)/, "trials-listing");
  // An export under another name has no listing beside it: never the export itself.
  return beside === name ? null : path.join(path.dirname(exported), beside);
}

function load(): TrialsListing {
  // The operator's switch: off, the site is built as if there were no listing.
  if (!LISTED_TRIAL_PAGES) return EMPTY;
  const file = listingPath();
  if (!file || !fs.existsSync(file)) {
    if (process.env.TRIALS_LISTING_FILE) throw new Error(`No trial listing at ${file}.`);
    return EMPTY;
  }
  const content = JSON.parse(fs.readFileSync(file, "utf8"));
  const schema = JSON.parse(fs.readFileSync(path.resolve("trials-listing.schema.json"), "utf8"));
  const ajv = new Ajv2020({ allErrors: false });
  addFormats(ajv);
  const validate = ajv.compile(schema);
  if (!validate(content)) {
    const problems = (validate.errors ?? []).map((error) => `  ${error.instancePath || "/"} ${error.message}`).join("\n");
    throw new Error(`The trial listing at ${file} does not match trials-listing.schema.json:\n${problems}`);
  }
  return content as TrialsListing;
}

export const listing: TrialsListing = load();
