// The lab's bundle of page files (openspec pairs-site): one JSON file a page under
// `p12_<page>/`, one JSON Schema a page model under `schemas/`. The files carry codes;
// every word a reader sees for a code is in `pair-wording.ts`. A file
// that does not fit its schema, and a code with no wording, stop the build.
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { PAIR_EVENT_LABELS, PAIR_TRIAL_STATES, unwordedPairCodes } from "./pair-wording.ts";
import { SCHEMA_MODEL, checkManifest } from "../../../store/ingest/scripts/bundle-manifest.mjs";

const PREFIX = "p12_";
const SCHEMAS = "schemas";

/** The page model a folder of the bundle holds: `p12_pair_page` holds `PairPage`. */
export function modelOf(folder: string): string {
  return folder
    .slice(PREFIX.length)
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join("");
}

/** The folder of a page model: `PairPage` is held in `p12_pair_page`. */
const folderOf = (model: string) => PREFIX + model.replace(/[A-Z]/g, (letter, at) => `${at ? "_" : ""}${letter.toLowerCase()}`);

export { PAIR_EVENT_LABELS, PAIR_TRIAL_STATES, unwordedPairCodes };

export interface Bundle {
  /** The bundle's version: the first 16 hex digits of the checksum its manifest states. */
  version: string;
  /** The manifest as the lab wrote it (`store/ingest/scripts/bundle-manifest.mjs`). */
  manifest: Record<string, any>;
  /** Page model name to its pages, by key (a pair page's key is its address). */
  pages: Record<string, Record<string, any>>;
  /** Page models the bundle holds that have no schema in it: nothing of theirs is read. */
  withoutSchema: string[];
}

/** Read a bundle folder. Throws, naming the page model and both counts when the manifest's
 * counts differ from the files, when the files' checksum is not the manifest's, naming the
 * file when one does not fit its schema, and naming the codes when a pair page carries one
 * the site has no words for. Every page is built from what this returns, so a build stops
 * on any of these before it writes a page. */
export function readBundle(folder: string): Bundle {
  if (!fs.existsSync(path.join(folder, SCHEMAS))) {
    throw new Error(`${folder} holds no ${SCHEMAS}/ folder: it is not a bundle of page files.`);
  }
  // The manifest first (openspec pairs-site, task 2.3): a folder cut short in a copy, or
  // changed after the lab wrote it, is refused whole rather than published in part.
  // Every page and schema below is read from what the check read, not from the folder again,
  // so the pages built are the ones the recorded version names even if the folder changes.
  const { version, manifest, pages: checked } = checkManifest(folder);
  const held = new Map<string, [string, string][]>();
  for (const [model, key, text] of checked as [string, string, string][]) {
    if (!held.has(model)) held.set(model, []);
    held.get(model)!.push([key, text]);
  }
  const schemas = new Map(held.get(SCHEMA_MODEL) ?? []);
  const ajv = new Ajv2020({ allErrors: false, strict: false });
  addFormats(ajv);
  // The lab writes some times with no offset (`PairOrigin.created_at`), which the schema
  // calls a date-time and RFC 3339 does not. Both spellings are read as a time until the
  // lab writes an offset (openspec pairs-site, task 2.5).
  // Remove when tests/bundle-strict.test.mjs finds no failing file: the lab's fixed bundle.
  ajv.addFormat("date-time", (text) => !Number.isNaN(Date.parse(text)));
  const pages: Bundle["pages"] = {};
  const withoutSchema: string[] = [];
  for (const [model, files] of [...held].filter(([model]) => model !== SCHEMA_MODEL)) {
    const schema = schemas.get(model);
    if (!schema) {
      withoutSchema.push(model);
      continue;
    }
    const validate = ajv.compile(JSON.parse(schema));
    const name = folderOf(model);
    pages[model] = {};
    for (const [key, text] of files) {
      const page = JSON.parse(text);
      if (!validate(page)) {
        const [error] = validate.errors ?? [];
        throw new Error(
          `${name}/${key}.json does not fit ${model}: ${error?.instancePath || "/"} ${error?.message ?? "is invalid"}.`,
        );
      }
      pages[model][key] = page;
    }
  }
  const unworded = unwordedPairCodes(
    Object.values(pages.PairPage ?? {}),
    Object.values(pages.PairInterventionPage ?? {}),
  );
  if (unworded.length) {
    throw new Error(`The bundle carries codes the site has no words for: ${unworded.join(", ")}.`);
  }
  return { version, manifest, pages, withoutSchema };
}

/** The published claims' slugs whose addresses reach this pair. A row the lab wrote after its
 * pull request 125 lists them (`claim_slugs`): its own claim's, and those whose trials moved to it,
 * so that when a person merged two claims both old slugs lead to the one pair. A row of a
 * bundle cut before that has no such list, and reaches its origin's claim only. Remove the
 * second branch once tests/bundle is recut. */
export function claimSlugsOf(row: any): string[] {
  if (Array.isArray(row.claim_slugs)) return row.claim_slugs;
  return row.origin?.claim_slug ? [row.origin.claim_slug] : [];
}

/** Where an old claim address goes now: the address of the one pair it reaches. A claim
 * whose slug is its pair's address moves nowhere and is left out. A Map, not an object: a
 * slug is any text, and "constructor" is one an object already has. */
export function movedAddresses(pairPages: any[]): Map<string, string> {
  const moved = new Map<string, string>();
  for (const page of pairPages) {
    const address = page.row.pair.address;
    for (const slug of new Set(claimSlugsOf(page.row))) {
      if (!slug || slug === address) continue;
      // A claim that reaches several pairs goes to none of them: a 301 names one successor.
      moved.set(slug, moved.has(slug) ? "" : address);
    }
  }
  return new Map([...moved].filter(([, address]) => address));
}
