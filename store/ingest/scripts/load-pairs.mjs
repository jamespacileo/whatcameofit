// Loads one bundle of the lab's page files into the store's pair tables (migration 0011).
//
//   node scripts/load-pairs.mjs <folder>                       this machine's local engine
//   node scripts/load-pairs.mjs <folder> --remote              the preview database
//   node scripts/load-pairs.mjs <folder> --remote --config <file> --production <database name>
//   node scripts/load-pairs.mjs <folder> --print               the statements, nothing run
//
// <folder> is what `lab pipeline pages` writes: `p12_<page>/<key>.json` and `schemas/`.
// The bundle's version is the checksum of its files. Its rows are written under that
// version and the last statements mark it current and drop every version but it and the
// one before, so a load that stops early leaves the site reading what it read. Loading
// the current version again is refused: nothing would change.
import { createHash } from "node:crypto";
import { mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const PREFIX = "p12_";
// Under D1's 100,000 bytes a statement: a character is at most four bytes, a quote doubles.
const PART_CHARS = 10_000;
const KEPT_VERSIONS = 2;
const TABLES = ["pair_page", "pair_intervention", "pair_intervention_name", "pair_condition", "pair", "pair_trial", "pair_trial_facts", "pair_status_change"];

const model = (folder) => folder.slice(PREFIX.length).split("_").map((word) => word[0].toUpperCase() + word.slice(1)).join("");
const quote = (value) => (value === null || value === undefined ? "NULL"
  : typeof value === "number" ? String(value)
  : typeof value === "boolean" ? (value ? "1" : "0")
  : `'${String(value).replaceAll("'", "''")}'`);
const insert = (table, row) => `INSERT INTO ${table} (${Object.keys(row).join(", ")}) VALUES (${Object.values(row).map(quote).join(", ")})`;

// The bundle's page files, in a fixed order: [model, key, text].
export function files(folder) {
  const out = [];
  for (const name of readdirSync(folder).filter((entry) => entry.startsWith(PREFIX) && statSync(join(folder, entry)).isDirectory()).sort()) {
    for (const file of readdirSync(join(folder, name)).filter((entry) => entry.endsWith(".json")).sort()) {
      out.push([model(name), file.slice(0, -".json".length), readFileSync(join(folder, name, file), "utf8")]);
    }
  }
  if (!out.length) throw new Error(`${folder} holds no page file under a ${PREFIX}* folder: give the folder \`lab pipeline pages\` wrote`);
  return out;
}

// A bundle's version: the checksum of its page files. The site's build records the same
// version, the only one its Worker reads pages of (openspec pairs-site).
export function bundleVersion(folder, pages = files(folder)) {
  const hash = createHash("sha256");
  for (const [name, key, text] of pages) hash.update(`${name}/${key}\n${text}\n`);
  return hash.digest("hex").slice(0, 16);
}

// The statements that load a bundle, its version and its counts. Each statement is one line.
export function statements(folder, { loadedAt = new Date().toISOString() } = {}) {
  const pages = files(folder);
  const version = bundleVersion(folder, pages);
  const rows = Object.fromEntries(TABLES.map((table) => [table, new Map()]));
  const put = (table, key, row) => rows[table].set(key, { version, ...row });

  for (const [name, key, text] of pages) {
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
  const kept = `(SELECT version FROM pair_bundle ORDER BY current DESC, loaded_at DESC LIMIT ${KEPT_VERSIONS})`;
  const sql = [
    // A version left by a load that stopped is cleared before it is loaded again.
    ...TABLES.map((table) => `DELETE FROM ${table} WHERE version = ${quote(version)} AND NOT EXISTS (SELECT 1 FROM pair_bundle WHERE version = ${quote(version)} AND current = 1)`),
    `INSERT INTO pair_bundle (version, loaded_at, counts) VALUES (${quote(version)}, ${quote(loadedAt)}, ${quote(JSON.stringify(counts))}) ON CONFLICT (version) DO UPDATE SET loaded_at = excluded.loaded_at, counts = excluded.counts WHERE current = 0`,
    ...TABLES.flatMap((table) => [...rows[table].values()].map((row) => insert(table, row))),
    `UPDATE pair_bundle SET current = 0 WHERE current = 1 AND version <> ${quote(version)}`,
    `UPDATE pair_bundle SET current = 1 WHERE version = ${quote(version)}`,
    ...TABLES.map((table) => `DELETE FROM ${table} WHERE version NOT IN ${kept}`),
    `DELETE FROM pair_bundle WHERE version NOT IN (SELECT version FROM (${kept.slice(1, -1)}))`,
  ];
  return { version, counts, sql };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [folder, ...argv] = process.argv.slice(2);
  if (!folder || folder.startsWith("--")) {
    console.error("usage: node scripts/load-pairs.mjs <folder of page files> [--print | --remote [--config <file>] [--production <database name>]]");
    process.exit(1);
  }
  try {
    const load = statements(folder);
    if (argv.includes("--print")) {
      console.log(load.sql.join(";\n") + ";");
    } else {
      const { execute, target } = await import("./d1.mjs");
      const to = target(argv);
      const [held] = (await execute(to, "--command", `SELECT version FROM pair_bundle WHERE current = 1`))[0]?.results ?? [];
      if (held?.version === load.version) throw new Error(`bundle ${load.version} is already the current one: nothing to load`);
      const dir = mkdtempSync(join(tmpdir(), "thenwhat-pairs-"));
      try {
        writeFileSync(join(dir, "pairs.sql"), load.sql.join(";\n") + ";\n");
        await execute(to, "--file", join(dir, "pairs.sql"));
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
