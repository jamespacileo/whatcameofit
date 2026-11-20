// A bundle's manifest (openspec pairs-site, task 2.3, `specs/site-bundle`): `manifest.json`
// beside the `p12_<page>/` folders and `schemas/`, stating the files' checksum, how many files
// each page model has, when it was made and, from the lab, the commit and step versions that
// made it, the registry snapshot read and how many trials were fetched. The loader checks
// it before anything is written to D1 and the build before any page is written, so a folder
// cut short in a copy, or changed after the lab wrote it, is refused rather than published.
//
//   node scripts/bundle-manifest.mjs <folder> [--made-at <time>] [--lab-commit <sha>] [--steps <file of {"step": "version"}>]
//
// writes the manifest of a folder that has none. The lab's `lab pipeline pages` is to write the
// same file itself (with its step versions); this command is for a folder cut before it does.
//
// The checksum leaves the manifest out (it holds the checksum), so a bundle's version is the
// one it had before bundles carried a manifest: `230ee727aab2d32c` for site/tests/bundle.
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const PREFIX = "p12_";
const SCHEMAS = "schemas";
export const MANIFEST = "manifest.json";
export const MANIFEST_FORMAT = "pairs-bundle";
// Raised when the manifest's shape changes, so an older reader refuses a newer bundle.
export const MANIFEST_FORMAT_VERSION = 1;
/** The reserved model a schema is kept under in D1 (load-pairs.mjs). No page model has it. */
export const SCHEMA_MODEL = "$schema";

const model = (folder) => folder.slice(PREFIX.length).split("_").map((word) => word[0].toUpperCase() + word.slice(1)).join("");

// The bundle's files, in a fixed order: [model, key, text]. Page files first, by folder and
// name; then each schema, as the model `$schema` keyed by its page model's name.
export function files(folder) {
  const out = [];
  for (const name of readdirSync(folder).filter((entry) => entry.startsWith(PREFIX) && statSync(join(folder, entry)).isDirectory()).sort()) {
    for (const file of readdirSync(join(folder, name)).filter((entry) => entry.endsWith(".json")).sort()) {
      out.push([model(name), file.slice(0, -".json".length), readFileSync(join(folder, name, file), "utf8")]);
    }
  }
  if (!out.length) throw new Error(`${folder} holds no page file under a ${PREFIX}* folder: give the folder \`lab pipeline pages\` wrote`);
  const schemas = join(folder, SCHEMAS);
  const held = existsSync(schemas) ? readdirSync(schemas).filter((entry) => entry.endsWith(".json")).sort() : [];
  if (!held.length) throw new Error(`${folder} holds no ${SCHEMAS}/ folder of JSON Schemas: the site reads none of a bundle without them`);
  for (const file of held) out.push([SCHEMA_MODEL, file.slice(0, -".json".length), readFileSync(join(schemas, file), "utf8")]);
  return out;
}

/** The SHA-256 of a bundle's files, in hex. Each file is hashed as compact JSON after its
 * path, so a folder written back from D1 has the checksum it was loaded with whatever
 * spacing the lab used. */
export function bundleChecksum(folder, pages = files(folder)) {
  const hash = createHash("sha256");
  for (const [name, key, text] of pages) hash.update(`${name}/${key}\n${JSON.stringify(JSON.parse(text))}\n`);
  return hash.digest("hex");
}

// A bundle's version: the first 16 hex digits of its checksum. The site's build records the
// same version, the only one its Worker reads pages of (openspec pairs-site).
export function bundleVersion(folder, pages = files(folder)) {
  return bundleChecksum(folder, pages).slice(0, 16);
}

/** How many files of each page model a bundle holds. Schemas are not counted (they are not
 * page models); the checksum covers them. */
export function countsOf(pages) {
  const counts = {};
  for (const [name] of pages) if (name !== SCHEMA_MODEL) counts[name] = (counts[name] ?? 0) + 1;
  return counts;
}

/**
 * The manifest of a folder as it is now. The shape is the one agreed with the lab, which is
 * to write it from `lab pipeline pages` (coordinator, 2026-11-20): the site checks the
 * checksum and counts; `lab_commit`, `steps`, `snapshot` and `coverage` are the lab's, read
 * here only for their shape (the release check's coverage half is the lab's).
 */
export function manifestOf(folder, { madeAt = new Date().toISOString(), labCommit, steps, snapshot, trialsFetched } = {}) {
  const pages = files(folder);
  return {
    format: MANIFEST_FORMAT,
    format_version: MANIFEST_FORMAT_VERSION,
    made_at: madeAt,
    ...(labCommit === undefined ? {} : { lab_commit: labCommit }),
    ...(steps === undefined ? {} : { steps }),
    ...(snapshot === undefined ? {} : { snapshot }),
    checksum: `sha256:${bundleChecksum(folder, pages)}`,
    counts: countsOf(pages),
    ...(trialsFetched === undefined ? {} : { coverage: { trials_fetched: trialsFetched } }),
  };
}

export function writeManifest(folder, options) {
  const manifest = manifestOf(folder, options);
  writeFileSync(join(folder, MANIFEST), `${JSON.stringify(manifest, null, 1)}\n`);
  return manifest;
}

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
// RFC 3339 with its offset: a time the lab writes without one is refused here, unlike the
// page files' allowance (task 2.5), since the manifest is new and has no older spelling.
const OFFSET_TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;

/**
 * Check a folder against its manifest: the counts first, since a missing file is the likely
 * fault and a count names it, then the checksum. Throws naming what differs.
 * @returns {{ version: string, manifest: object, pages: Array<[string, string, string]> }}
 */
export function checkManifest(folder) {
  const pages = files(folder);
  const file = join(folder, MANIFEST);
  if (!existsSync(file)) throw new Error(`${folder} holds no ${MANIFEST}: a bundle is read only with the manifest that states its checksum and counts`);
  const manifest = JSON.parse(readFileSync(file, "utf8"));
  if (manifest.format !== MANIFEST_FORMAT || manifest.format_version !== MANIFEST_FORMAT_VERSION) {
    throw new Error(`${file} is ${manifest.format} version ${manifest.format_version}; this site reads ${MANIFEST_FORMAT} version ${MANIFEST_FORMAT_VERSION}`);
  }
  for (const [field, ok] of [
    ["made_at", typeof manifest.made_at === "string" && OFFSET_TIME.test(manifest.made_at) && !Number.isNaN(Date.parse(manifest.made_at))],
    ["checksum", typeof manifest.checksum === "string" && /^sha256:[0-9a-f]{64}$/.test(manifest.checksum)],
    ["counts", isObject(manifest.counts) && Object.values(manifest.counts).every((n) => Number.isInteger(n) && n >= 0)],
    ["lab_commit", manifest.lab_commit === undefined || typeof manifest.lab_commit === "string"],
    ["steps", manifest.steps === undefined || (isObject(manifest.steps) && Object.values(manifest.steps).every((v) => typeof v === "string"))],
    ["snapshot", manifest.snapshot === undefined || isObject(manifest.snapshot)],
    ["coverage", manifest.coverage === undefined || (isObject(manifest.coverage) && Number.isInteger(manifest.coverage.trials_fetched) && manifest.coverage.trials_fetched >= 0)],
  ]) {
    if (!ok) throw new Error(`${file} has no valid ${field}`);
  }
  const present = countsOf(pages);
  for (const name of [...new Set([...Object.keys(manifest.counts), ...Object.keys(present)])].sort()) {
    const stated = manifest.counts[name] ?? 0;
    const found = present[name] ?? 0;
    if (stated !== found) throw new Error(`the manifest counts ${stated} ${name} files and ${found} are present in ${folder}`);
  }
  const checksum = `sha256:${bundleChecksum(folder, pages)}`;
  if (checksum !== manifest.checksum) throw new Error(`the files' checksum ${checksum} differs from the manifest's ${manifest.checksum} in ${folder}`);
  return { version: checksum.slice("sha256:".length, "sha256:".length + 16), manifest, pages };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [folder, ...argv] = process.argv.slice(2);
  const option = (name) => (argv.includes(name) ? argv[argv.indexOf(name) + 1] : undefined);
  if (!folder || folder.startsWith("--")) {
    console.error("usage: node scripts/bundle-manifest.mjs <folder> [--made-at <time>] [--lab-commit <sha>] [--steps <file>]");
    process.exit(1);
  }
  try {
    if (existsSync(join(folder, MANIFEST))) throw new Error(`${folder} already holds a ${MANIFEST}; check it, or remove it to write a new one`);
    const steps = option("--steps") ? JSON.parse(readFileSync(option("--steps"), "utf8")) : undefined;
    const written = writeManifest(folder, { madeAt: option("--made-at") ?? new Date().toISOString(), labCommit: option("--lab-commit"), steps });
    console.log(`${join(folder, MANIFEST)}: ${written.checksum}, ${Object.entries(written.counts).map(([name, n]) => `${n} ${name}`).join(", ")}`);
  } catch (error) {
    console.error(String(error.message || error));
    process.exit(1);
  }
}
