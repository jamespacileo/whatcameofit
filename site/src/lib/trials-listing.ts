// The trial listing: the pipeline's file of one named set of stored trials, validated
// before anything is built from it. The bundle's version covers the listing,
// so a rollback restores both the pairs and the listed trials in one build.
// Behaviour: openspec trial-pages, "A trial listing built into the site".
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { LISTED_TRIAL_PAGES } from "../../site.config.mjs";
import { pairBundle } from "./pairs.ts";
import { LISTING_LIMIT_BYTES, PART_BYTES, splitListing } from "./trial-listing-parts.mjs";

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

function load(): TrialsListing {
  // The operator's switch: off, the site is built as if there were no listing.
  if (!LISTED_TRIAL_PAGES) return EMPTY;
  const bundle = pairBundle();
  const bundled = bundle.pages.PairTrialListing;
  const bundledFile = "p12_pair_trial_listing/listed.json";
  if (bundle.withoutSchema.includes("PairTrialListing") ||
      (bundled && (Object.keys(bundled).length !== 1 || !Object.hasOwn(bundled, "listed")))) {
    throw new Error(`A bundled trial listing needs ${bundledFile} and schemas/PairTrialListing.json.`);
  }
  const configured = process.env.TRIALS_LISTING_FILE;
  if (bundled && configured) throw new Error("Remove TRIALS_LISTING_FILE to use the bundle's trial listing.");
  if (!bundled && !configured) return EMPTY;
  const file = configured ? path.resolve(configured) : bundledFile;
  if (configured && !fs.existsSync(file)) throw new Error(`No trial listing at ${file}.`);
  const content = bundled ? bundled.listed : JSON.parse(fs.readFileSync(file, "utf8"));
  const schema = JSON.parse(fs.readFileSync(path.resolve("trials-listing.schema.json"), "utf8"));
  const ajv = new Ajv2020({ allErrors: false });
  addFormats(ajv);
  const validate = ajv.compile(schema);
  if (!validate(content)) {
    const problems = (validate.errors ?? []).map((error) => `  ${error.instancePath || "/"} ${error.message}`).join("\n");
    throw new Error(`The trial listing at ${file} does not match trials-listing.schema.json:\n${problems}`);
  }
  const listing = content as TrialsListing;
  if (Buffer.byteLength(JSON.stringify(listing)) + 1 > LISTING_LIMIT_BYTES) {
    throw new Error(`The trial listing at ${file} exceeds ${LISTING_LIMIT_BYTES / (1024 * 1024)} MiB.`);
  }
  if (new Set(listing.trials.map(([id]) => id)).size !== listing.trials.length) {
    throw new Error(`The trial listing at ${file} repeats a registry number.`);
  }
  const measured = bundle.manifest.snapshot?.trial_listing?.trials_listed;
  if (bundled && measured !== undefined && measured !== listing.trials.length) {
    throw new Error(`The manifest reports ${measured} listed trials; the bundle has ${listing.trials.length}.`);
  }
  return listing;
}

export const listing: TrialsListing = load();

export interface ListingPart {
  /** The part's name in its address: /trials-listing/<name>.json. */
  name: string;
  /** The first and last registry numbers it holds; parts are in registry-number order. */
  first: string;
  last: string;
  trials: ListedRow[];
}

// No single file a reader fetches holds the whole listing: it is cut, in registry-number
// order, into parts of about a mebibyte. A registry number is found in one part.
export const parts = (splitListing(listing.trials, PART_BYTES) as ListingPart[]).map((part) => {
  // Hash exactly what the part serves, including its columns and registry snapshot.
  const hash = createHash("sha256").update(JSON.stringify({ ...listing, trials: part.trials })).digest("hex");
  return { ...part, name: `${part.name}-${hash}` };
});

/** What a reader's search fetches first: which part holds which registry numbers. */
export const manifest = {
  schema_version: listing.schema_version,
  set: listing.set,
  registry: listing.registry,
  records_read: listing.records_read,
  columns: listing.columns,
  total: listing.trials.length,
  parts: parts.map((part) => ({
    file: `/trials-listing/${part.name}.json`,
    first: part.first,
    last: part.last,
    trials: part.trials.length,
  })),
};
