// What must be true of a trial listing before it is deployed: it matches its schema and is
// small enough to be built and searched. Used by deploy.mjs and pr-preview.mjs.
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

// The site's build cuts the listing into parts of about a mebibyte, so no file a reader
// fetches holds all of it (src/lib/trial-listing-parts.mjs). This bounds the whole: the
// build reads it into memory, and a reader who searches it by words fetches every part.
// 29 MiB held 102,877 trials on 2026-11-17.
export const LISTING_LIMIT_BYTES = 64 * 1024 * 1024;

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
