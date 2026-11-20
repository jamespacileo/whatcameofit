// The lab's bundle of page files (openspec pairs-site): one JSON file a page under
// `p12_<page>/`, one JSON Schema a page model under `schemas/`. The files carry codes;
// every word a reader sees for a code is here or in the modules this one reads. A file
// that does not fit its schema, and a code with no wording, stop the build.
import fs from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { APPROACH_LABELS } from "./approach.ts";
import { PAIR_EVENT_LABELS, PAIR_TRIAL_STATES } from "./pair-view.ts";
import { STATUS_LABELS } from "./status.ts";
import { PHASE_WORDS } from "./trial-facts.ts";

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

export { PAIR_EVENT_LABELS, PAIR_TRIAL_STATES };

export interface Bundle {
  /** Page model name to its pages, by key (a pair page's key is its address). */
  pages: Record<string, Record<string, any>>;
  /** Page models the bundle holds that have no schema in it: nothing of theirs is read. */
  withoutSchema: string[];
}

/** Read a bundle folder. Throws, naming the file, when one does not fit its schema, and
 * naming the codes when a pair page carries one the site has no words for. */
export function readBundle(folder: string): Bundle {
  if (!fs.existsSync(path.join(folder, SCHEMAS))) {
    throw new Error(`${folder} holds no ${SCHEMAS}/ folder: it is not a bundle of page files.`);
  }
  const ajv = new Ajv2020({ allErrors: false, strict: false });
  addFormats(ajv);
  // The lab writes some times with no offset (`PairOrigin.created_at`), which the schema
  // calls a date-time and RFC 3339 does not. Both spellings are read as a time until the
  // lab writes an offset (openspec pairs-site, task 2.5).
  ajv.addFormat("date-time", (text) => !Number.isNaN(Date.parse(text)));
  const pages: Bundle["pages"] = {};
  const withoutSchema: string[] = [];
  const folders = fs
    .readdirSync(folder)
    .filter((name) => name.startsWith(PREFIX) && fs.statSync(path.join(folder, name)).isDirectory())
    .sort();
  for (const name of folders) {
    const model = modelOf(name);
    const schemaFile = path.join(folder, SCHEMAS, `${model}.json`);
    if (!fs.existsSync(schemaFile)) {
      withoutSchema.push(model);
      continue;
    }
    const validate = ajv.compile(JSON.parse(fs.readFileSync(schemaFile, "utf8")));
    pages[model] = {};
    for (const file of fs.readdirSync(path.join(folder, name)).filter((entry) => entry.endsWith(".json")).sort()) {
      const page = JSON.parse(fs.readFileSync(path.join(folder, name, file), "utf8"));
      if (!validate(page)) {
        const [error] = validate.errors ?? [];
        throw new Error(
          `${name}/${file} does not fit ${model}: ${error?.instancePath || "/"} ${error?.message ?? "is invalid"}.`,
        );
      }
      pages[model][file.slice(0, -".json".length)] = page;
    }
  }
  const unworded = unwordedPairCodes(Object.values(pages.PairPage ?? {}));
  if (unworded.length) {
    throw new Error(`The bundle carries codes the site has no words for: ${unworded.join(", ")}.`);
  }
  return { pages, withoutSchema };
}

/** Codes on pair pages that the site has no words for, as "kind: code", each once. */
export function unwordedPairCodes(pairPages: any[]): string[] {
  const found = new Set<string>();
  const need = (kind: string, code: string | null | undefined, words: Record<string, unknown>) => {
    if (code !== null && code !== undefined && !(code in words)) found.add(`${kind}: ${code}`);
  };
  for (const page of pairPages) {
    need("status", page.row.status.code, STATUS_LABELS);
    need("approach", page.approach?.approach, APPROACH_LABELS);
    for (const change of page.history) {
      need("status", change.before, STATUS_LABELS);
      need("status", change.after, STATUS_LABELS);
    }
    for (const trial of page.trials) {
      need("trial state", trial.facts.overall_status, PAIR_TRIAL_STATES);
      for (const phase of trial.facts.phases ?? []) need("phase", phase, PHASE_WORDS);
      for (const event of trial.events) need("event", event.kind, PAIR_EVENT_LABELS);
    }
  }
  return [...found].sort();
}

/** Where a claim's address goes now: the address of the pair that came from it. A claim
 * whose slug is its pair's address moves nowhere and is left out. */
export function movedAddresses(pairPages: any[]): Record<string, string> {
  const moved: Record<string, string> = {};
  for (const page of pairPages) {
    const slug = page.row.origin?.claim_slug;
    const address = page.row.pair.address;
    if (!slug || slug === address) continue;
    // One claim can stand behind several pairs; its address goes to none of them by rule.
    moved[slug] = slug in moved ? "" : address;
  }
  return Object.fromEntries(Object.entries(moved).filter(([, address]) => address));
}
