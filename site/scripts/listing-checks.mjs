// What must be true of a trial listing before it is deployed: it matches its schema and is
// small enough to be built and searched. Used by deploy.mjs and pr-preview.mjs.
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

import { LISTING_LIMIT_BYTES } from "../src/lib/trial-listing-parts.mjs";

export { LISTING_LIMIT_BYTES };

const SCHEMA_FILE = path.resolve(import.meta.dirname, "../trials-listing.schema.json");

/**
 * Why this listing must not be published: one sentence each. An empty list means it may be.
 * @param {{ text: string }} given
 * @returns {{ problems: string[], listing?: object, size?: number }}
 */
export function listingProblems({ text }) {
  let listing;
  try {
    listing = JSON.parse(text);
  } catch {
    return { problems: ["The trial listing is not JSON."] };
  }
  const ajv = new Ajv2020({ allErrors: false });
  addFormats(ajv);
  const validate = ajv.compile(JSON.parse(fs.readFileSync(SCHEMA_FILE, "utf8")));
  if (!validate(listing)) {
    const [problem] = validate.errors ?? [];
    return { problems: [`The trial listing does not match trials-listing.schema.json: ${problem?.instancePath || "/"} ${problem?.message}`] };
  }
  const problems = [];
  const compact = `${JSON.stringify(listing)}\n`;
  const size = Buffer.byteLength(compact);
  if (size > LISTING_LIMIT_BYTES) {
    problems.push(`The trial listing is ${size.toLocaleString("en")} bytes, over the ${LISTING_LIMIT_BYTES.toLocaleString("en")} a listing may be. List a smaller set.`);
  }
  return { problems, listing, size };
}

/** The problems of the listing TRIALS_LISTING_FILE names, for a deployment: none when there
 * is no listing, since a site built without one opens no page for a trial no pair holds. */
export function listingFileProblems() {
  if (!process.env.TRIALS_LISTING_FILE) return [];
  const file = path.resolve(process.env.TRIALS_LISTING_FILE);
  if (!fs.existsSync(file)) return [`No trial listing at ${file}.`];
  return listingProblems({ text: fs.readFileSync(file, "utf8") }).problems;
}

/** A cutover can use a versioned listing only after its source run accounted for the full set. */
export function listingCoverageProblems(folder) {
  const manifest = JSON.parse(fs.readFileSync(path.join(folder, "manifest.json"), "utf8"));
  if (!manifest.counts.PairTrialListing) return [];
  const report = manifest.snapshot?.trial_listing;
  if (report?.complete !== true ||
      !Number.isInteger(report.registry_total) || report.trials_read !== report.registry_total ||
      !Number.isInteger(report.trials_listed) || report.trials_listed < 1 || report.trials_listed > report.trials_read) {
    return ["The bundle's trial listing has no verified full registry run. Run the lab listing without a page cap, then export and load the bundle."];
  }
  return [];
}
