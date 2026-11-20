// Loads one bundle of the lab's page files into the store's pair tables (migration 0011).
//
//   node scripts/load-pairs.mjs <folder>                       this machine's local engine
//   node scripts/load-pairs.mjs <folder> --remote              the preview database
//   node scripts/load-pairs.mjs <folder> --remote --config <file> --production <database name>
//   node scripts/load-pairs.mjs <folder> --print               the statements, nothing run
//
// <folder> is what `lab pipeline pages` writes: `p12_<page>/<key>.json` and `schemas/`.
// Each schema is kept as a `pair_page` row of the model `$schema`, keyed by its page model's
// name, so a version read back from D1 (scripts/export-pairs.mjs) is the whole folder.
// The folder is checked against its `manifest.json` (scripts/bundle-manifest.mjs) before any
// statement is made: a file missing or changed since the lab wrote it, and nothing is loaded.
// The manifest itself is kept as the `pair_page` row `$manifest`/`manifest`.
// The bundle's version is the checksum of its files, read as JSON, schemas included. Its rows are written under that
// version and the last statements mark it current and drop every version but it and the
// one before, so a load that stops early leaves the site reading what it read. Loading
// the current version again is refused: nothing would change.
import { createWriteStream, mkdtempSync, realpathSync, rmSync, statSync } from "node:fs";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { MANIFEST, SCHEMA_MODEL, bundleVersion, checkManifest, files } from "./bundle-manifest.mjs";

export { SCHEMA_MODEL, bundleVersion, files };

/** The reserved model the manifest is kept under in `pair_page`, keyed `manifest`, so a version
 * read back from D1 has the manifest the lab wrote. It is not one of the files it checksums. */
export const MANIFEST_MODEL = "$manifest";
const MANIFEST_KEY = MANIFEST.slice(0, -".json".length);
// Under D1's 100,000 bytes a statement: a character is at most four bytes, a quote doubles.
const PART_CHARS = 10_000;
// The store keeps the current version and the one before: a deployment is rolled back by
// building from the one before (docs/deploy.md). Previews keep more (site/scripts/pairs-preview.mjs).
export const KEPT_VERSIONS = 2;
const TABLES = ["pair_page", "pair_intervention", "pair_intervention_name", "pair_condition", "pair", "pair_trial", "pair_trial_facts", "pair_status_change"];

const quote = (value) => (value === null || value === undefined ? "NULL"
  : typeof value === "number" ? String(value)
  : typeof value === "boolean" ? (value ? "1" : "0")
  : `'${String(value).replaceAll("'", "''")}'`);
const insert = (table, row) => `INSERT INTO ${table} (${Object.keys(row).join(", ")}) VALUES (${Object.values(row).map(quote).join(", ")})`;

// The statements that store a checked folder's manifest under its version when that version is
// held without one: a bundle loaded before bundles carried a manifest keeps its version (the
// manifest is outside the checksum), so it is never loaded again, and without this it could
// never be exported for a build. A manifest already held is left as it is.
// It takes the version and manifest a check already returned (`statements(...)` gives both), so
// the manifest stored is the one checked, even if the folder is replaced in the meantime.
export function manifestBackfill({ version, manifest }) {
  const body = JSON.stringify(manifest);
  // One part, so the guard below sees the whole manifest or none of it.
  if (body.length > PART_CHARS) throw new Error(`the manifest of bundle ${version} is longer than one part of ${PART_CHARS} characters`);
  const sql = `INSERT INTO pair_page (version, model, key, part, body) SELECT ${quote(version)}, ${quote(MANIFEST_MODEL)}, ${quote(MANIFEST_KEY)}, 0, ${quote(body)}`
    + ` WHERE EXISTS (SELECT 1 FROM pair_bundle WHERE version = ${quote(version)})`
    + ` AND NOT EXISTS (SELECT 1 FROM pair_page WHERE version = ${quote(version)} AND model = ${quote(MANIFEST_MODEL)})`;
  return { version, sql: [sql] };
}

// The statements that load a bundle, its version and its counts. Each statement is one line.
export function statements(folder, { loadedAt = new Date().toISOString(), keep = KEPT_VERSIONS } = {}) {
  if (!Number.isInteger(keep) || keep < 2) throw new Error(`keep must be a whole number of at least 2 (the current version and the one before), not ${keep}`);
  // Nothing is written unless the folder is whole and unchanged since its manifest was made.
  const { version, manifest, pages } = checkManifest(folder);
  const rows = Object.fromEntries(TABLES.map((table) => [table, new Map()]));
  const put = (table, key, row) => rows[table].set(key, { version, ...row });

  for (const [name, key, text] of [...pages, [MANIFEST_MODEL, MANIFEST_KEY, JSON.stringify(manifest)]]) {
    const body = JSON.stringify(JSON.parse(text));
    for (let part = 0; part * PART_CHARS < body.length; part += 1) {
      put("pair_page", `${name}|${key}|${part}`, { model: name, key, part, body: body.slice(part * PART_CHARS, (part + 1) * PART_CHARS) });
    }
    if (name !== "PairPage") continue;
    const page = JSON.parse(text);
    const { pair, intervention, condition, descriptor, status, filing, origin } = page.row;
    put("pair_intervention", intervention.id, { id: intervention.id, slug: intervention.slug, preferred_name: intervention.preferred_name,
      key_kind: intervention.key_kind, approach: page.approach?.approach ?? null, registry_type: page.approach?.registry_type ?? null });
    for (const held of page.names) {
      put("pair_intervention_name", `${held.intervention_id}|${held.name}`, { intervention_id: held.intervention_id, name: held.name, role: held.role, searchable: held.searchable });
    }
    put("pair_condition", condition.descriptor_id, { descriptor_id: condition.descriptor_id, slug: condition.slug, label: descriptor.label });
    put("pair", pair.key, { key: pair.key, address: pair.address, intervention_id: pair.intervention_id, condition_id: pair.condition_id,
      status_code: status.code, status_as_of: status.as_of, vertical: filing?.vertical ?? null, checked_by_person: page.checked_by_person,
      trials: page.trials.length, claim_slug: origin?.claim_slug ?? null });
    for (const trial of page.trials) {
      put("pair_trial", `${pair.key}|${trial.nct_id}`, { pair_key: pair.key, nct_id: trial.nct_id, arms: JSON.stringify(trial.arms), claim_arm: trial.claim_arm });
      const facts = trial.facts;
      put("pair_trial_facts", trial.nct_id, { nct_id: trial.nct_id, title: facts.title, phases: JSON.stringify(facts.phases ?? []),
        overall_status: facts.overall_status, start_day: facts.start?.day ?? null, completion_day: facts.completion?.day ?? null, as_of: facts.as_of });
    }
    for (const change of page.history) {
      put("pair_status_change", `${pair.key}|${change.on}|${change.after}`, { pair_key: pair.key, on_day: change.on, before: change.before, after: change.after });
    }
  }

  const counts = Object.fromEntries(TABLES.map((table) => [table, rows[table].size]));
  const kept = `(SELECT version FROM pair_bundle ORDER BY current DESC, loaded_at DESC LIMIT ${keep})`;
  const sql = [
    // A version left by a load that stopped is cleared before it is loaded again.
    ...TABLES.map((table) => `DELETE FROM ${table} WHERE version = ${quote(version)} AND NOT EXISTS (SELECT 1 FROM pair_bundle WHERE version = ${quote(version)} AND current = 1)`),
    `INSERT INTO pair_bundle (version, loaded_at, counts) VALUES (${quote(version)}, ${quote(loadedAt)}, ${quote(JSON.stringify(counts))}) ON CONFLICT (version) DO UPDATE SET loaded_at = excluded.loaded_at, counts = excluded.counts WHERE current = 0`,
    ...TABLES.flatMap((table) => [...rows[table].values()].map((row) => insert(table, row))),
    `UPDATE pair_bundle SET current = 0 WHERE current = 1 AND version <> ${quote(version)}`,
    `UPDATE pair_bundle SET current = 1 WHERE version = ${quote(version)}`,
    // Only the versions that fall out are deleted, each table by its key's first column, so a
    // load reads the rows it removes and not the history it keeps.
    ...TABLES.map((table) => `DELETE FROM ${table} WHERE version IN (SELECT version FROM pair_bundle WHERE version NOT IN ${kept})`),
    `DELETE FROM pair_bundle WHERE version NOT IN (SELECT version FROM (${kept.slice(1, -1)}))`,
  ];
  return { version, manifest, counts, sql };
}

/**
 * Writes the statements to a stream one at a time, waiting whenever it asks to. Joined into one
 * string, a full bundle's statements pass V8's longest string (about 536 million characters;
 * the rehearsal's 3,825 pairs are 73 million) and the load stops with "Invalid string length"
 * before anything is sent.
 * @param {import("node:stream").Writable} stream
 * @param {string[]} sql
 */
export async function writeStatements(stream, sql) {
  // pipeline waits on the stream's asks to slow down and turns any failure, the last flush's
  // included, into this promise's rejection.
  await pipeline(Readable.from(sql.map((statement) => `${statement};\n`), { objectMode: false }), stream);
}

/** The most a file for D1's local engine holds: Wrangler reads such a file whole, as one string. */
export const LOCAL_FILE_BYTES = 64 * 2 ** 20;

/**
 * The statements in files of at most `maxBytes` each, in order, named 1.sql, 2.sql and on. The
 * statements from the first that marks a version current to the end are kept in the last file
 * together, so no file boundary falls between the store losing its current version and
 * gaining the new one.
 * @returns {Promise<string[]>} the files, in the order they are to run
 */
export async function writeStatementFiles(dir, sql, maxBytes = Infinity) {
  const switchAt = sql.findIndex((statement) => statement.startsWith("UPDATE pair_bundle SET current"));
  const groups = [];
  let group = [];
  let bytes = 0;
  for (const statement of switchAt < 0 ? sql : sql.slice(0, switchAt)) {
    const size = Buffer.byteLength(statement) + 2;
    if (group.length > 0 && bytes + size > maxBytes) {
      groups.push(group);
      group = [];
      bytes = 0;
    }
    group.push(statement);
    bytes += size;
  }
  if (switchAt >= 0) group.push(...sql.slice(switchAt));
  if (group.length > 0) groups.push(group);
  const files = [];
  for (const [index, statements_] of groups.entries()) {
    const file = join(dir, `${index + 1}.sql`);
    await writeStatements(createWriteStream(file), statements_);
    files.push(file);
  }
  return files;
}

/**
 * A folder for the load's SQL on the drive that holds the bundle: beside the bundle's own folder,
 * found through its real path, so a link on this machine's disk to a bundle elsewhere still
 * writes there. A bundle folder that is a mount point has no parent on its own drive, so it is
 * refused rather than written beside on another.
 */
export function scratchBeside(folder) {
  const real = realpathSync(folder);
  const parent = dirname(real);
  if (statSync(parent).dev !== statSync(real).dev) throw new Error(`${real} is a mount point: copy the bundle into a folder on that drive, so its SQL can be written beside it`);
  return mkdtempSync(join(parent, ".thenwhat-pairs-"));
}

// Run as a command, not imported (an importer may have no script path of its own).
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [folder, ...argv] = process.argv.slice(2);
  if (!folder || folder.startsWith("--")) {
    console.error("usage: node scripts/load-pairs.mjs <folder of page files> [--print | --remote [--config <file>] [--production <database name>]]");
    process.exit(1);
  }
  try {
    const load = statements(folder);
    if (argv.includes("--print")) {
      // Ended here, so the statements are all out before the process exits.
      await writeStatements(process.stdout, load.sql);
    } else {
      const { execute, target } = await import("./d1.mjs");
      const to = target(argv);
      const [held] = (await execute(to, "--command", `SELECT version FROM pair_bundle WHERE current = 1`))[0]?.results ?? [];
      if (held?.version === load.version) {
        await execute(to, "--command", manifestBackfill(load).sql[0]);
        console.log(`bundle ${load.version} is already the current one: nothing loaded; its manifest is held`);
        process.exit(0);
      }
      // Beside the bundle's folder, on the drive that holds it: the statements carry the lab's
      // pages, which stay off this machine's own disk.
      const dir = scratchBeside(folder);
      try {
        // D1 itself takes one file of up to 5 GB; the local engine reads each file whole, so it
        // is given them in parts, in order.
        for (const file of await writeStatementFiles(dir, load.sql, to.remote ? Infinity : LOCAL_FILE_BYTES)) await execute(to, "--file", file);
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
      console.log(`bundle ${load.version} loaded and current: ${Object.entries(load.counts).map(([table, n]) => `${n} ${table}`).join(", ")}`);
    }
  } catch (error) {
    console.error(String(error.message || error));
    process.exit(1);
  }
}
