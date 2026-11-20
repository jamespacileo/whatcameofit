// Pair pages in a pull request's preview (openspec pairs-site, task 4.5). Previews run in
// their own Cloudflare account, which cannot reach the store's databases, so the preview
// account holds one D1 database of its own for pairs, in the EU jurisdiction. Each preview
// loads its bundle there, is built from that bundle, and its Worker (worker/with-pairs.mjs)
// makes the pages not built ahead from it.
//
// When the preview's token cannot read that database, or it does not exist, or it is not in
// the EU, the pairs part is left out and said why: the preview is the claims site as before.
// Production (wrangler.jsonc) is never read or written here.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { manifestBackfill, statements } from "../../store/ingest/scripts/load-pairs.mjs";

const SITE_DIR = path.resolve(import.meta.dirname, "..");
const WRANGLER = path.join(SITE_DIR, "node_modules/wrangler/bin/wrangler.js");
const MIGRATIONS = path.resolve(SITE_DIR, "../store/ingest/migrations");
/** The preview account's database for pairs. A name ending in `-preview` is never production. */
export const PREVIEW_PAIRS_DATABASE = "thenwhat-pairs-pr-preview";
/** The bundle a preview loads unless PREVIEW_PAIRS_BUNDLE names another folder. */
export const PREVIEW_PAIRS_BUNDLE = path.join(SITE_DIR, "tests/bundle");
/** How many bundle versions the previews' database keeps, newest loads first. A preview makes
 * its pair pages not built ahead from D1 at the version its build recorded in /pair-shell, for
 * as long as it is up (and, once pair records are served on request, those records too). The
 * store's own rule (the current version and the one before) dropped an older open pull
 * request's version after two newer loads, and those pages then answered 404 (review of PR
 * 383). A preview's version changes only when a pull request changes its bundle, so ten
 * distinct bundles while one pull request is open is far more than happens. A version is known
 * only to the Worker built from it, so keeping exactly the live previews' versions would mean
 * asking every open preview at each load; a count is the smaller rule.
 *
 * Size: the committed small bundle is about 0.1 MB a version. A bundle of the rehearsal's size
 * is about 100 MB a version, and the incoming version is written before old ones are dropped,
 * so ten of those need about 1.1 GB: within the 10 GB a D1 database holds on Workers Paid, but
 * not the 500 MB of the Free plan (docs/sources.md). The preview account's plan is the
 * operator's; PREVIEW_PAIRS_KEEP sets a smaller count (at least 2) for a smaller database.
 * Production keeps the store's rule. */
export const PREVIEW_KEPT_VERSIONS = previewKept(process.env.PREVIEW_PAIRS_KEEP);

function previewKept(value) {
  if (value === undefined || value === "") return 10;
  const count = Number(value);
  if (!Number.isInteger(count) || count < 2) throw new Error(`PREVIEW_PAIRS_KEEP must be a whole number of at least 2, not ${value}`);
  return count;
}
const HOW = 'see docs/deploy.md, "Pair pages in a preview"';

export function wrangler(args) {
  return spawnSync(process.execPath, [WRANGLER, ...args], {
    cwd: SITE_DIR,
    encoding: "utf8",
    env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" },
    maxBuffer: 64 * 1024 * 1024,
  });
}

export const lastError = (text) =>
  text
    .replace(/\x1b\[[0-9;]*m/g, "")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => /error|code: \d+/i.test(line))
    .at(-1) ?? "no reason given";

export const json = (text) => JSON.parse(text.slice(text.search(/[[{]/)));

/**
 * The preview account's pairs database, or why the pairs part is left out.
 * @returns {{ name: string, id: string } | { skip: string }}
 */
export function findPairsDatabase(name = PREVIEW_PAIRS_DATABASE) {
  if (!name.endsWith("-preview")) return { skip: `${name} is not a preview database's name` };
  const answer = wrangler(["d1", "info", name, "--json"]);
  const said = `${answer.stdout ?? ""}${answer.stderr ?? ""}`;
  if (answer.status !== 0) {
    if (/Couldn't find a D1 DB/i.test(said)) return { skip: `the preview account has no database ${name} yet (${HOW})` };
    return { skip: `the preview's token could not read ${name}: ${lastError(said)} (${HOW})` };
  }
  const info = json(answer.stdout);
  // Read back before any record is written, as for the store's databases (docs/deploy.md).
  if (info.jurisdiction !== "eu") return { skip: `${name} is not in the EU jurisdiction, so nothing is written to it (${HOW})` };
  if (typeof info.uuid !== "string") return { skip: `Wrangler gave no id for ${name}` };
  return { name, id: info.uuid };
}

// The checked-in configurations use whole-line comments.
const readConfig = (file) => JSON.parse(fs.readFileSync(file, "utf8").replace(/^[ \t]*\/\/.*$/gm, ""));

/**
 * A Wrangler configuration with pair pages: the given configuration, its Worker the one with
 * pairs, and the pairs database bound as PAIRS. Written into `scratch`. Refuses a
 * configuration whose Worker is not `worker` (by default a pull request preview's), so a
 * preview never writes production's and `make deploy` never writes a preview's.
 */
export function pairsConfig({ base, database, scratch, worker = "thenwhat-pr" }) {
  // A name alone is the site's own file, as Wrangler reads it from the site's folder.
  base = path.resolve(SITE_DIR, base);
  const config = readConfig(base);
  if (config.name !== worker) {
    const what = worker === "thenwhat-pr" ? "a pull request preview's" : `the ${worker} Worker's`;
    throw new Error(`${base} is not ${what} configuration (its name is ${config.name})`);
  }
  const from = path.dirname(path.resolve(base));
  config.main = path.resolve(SITE_DIR, "worker/with-pairs.mjs");
  config.assets = { ...config.assets, directory: path.resolve(from, config.assets.directory) };
  config.d1_databases = [
    ...(config.d1_databases ?? []).filter((binding) => binding.binding !== "PAIRS"),
    { binding: "PAIRS", database_name: database.name, database_id: database.id, migrations_dir: MIGRATIONS },
  ];
  fs.mkdirSync(scratch, { recursive: true });
  const file = path.join(scratch, "wrangler.pairs.json");
  fs.writeFileSync(file, JSON.stringify(config));
  return file;
}

/**
 * Bring the pairs database to the store's migrations and load a bundle into it, unless that
 * bundle's version is already the current one there.
 * @param {{ config: string, database: { name: string }, bundle: string, local?: boolean, persistTo?: string }} options
 * @returns {{ version: string, loaded: boolean }}
 */
export function loadPairsBundle({ config, database, bundle, local = false, persistTo }) {
  const where = local ? ["--local", ...(persistTo ? ["--persist-to", persistTo] : [])] : ["--remote"];
  const migrated = wrangler(["d1", "migrations", "apply", database.name, ...where, "--config", config]);
  if (migrated.status !== 0) throw new Error(`the migrations did not apply to ${database.name}: ${lastError(`${migrated.stdout}${migrated.stderr}`)}`);
  const load = statements(bundle, { keep: PREVIEW_KEPT_VERSIONS });
  const held = wrangler(["d1", "execute", database.name, ...where, "--config", config, "--json", "--command",
    `SELECT current FROM pair_bundle WHERE version = '${load.version}'`]);
  if (held.status !== 0) throw new Error(`${database.name} could not be read: ${lastError(`${held.stdout}${held.stderr}`)}`);
  if (json(held.stdout)[0]?.results?.[0]?.current === 1) {
    // Already current, perhaps from before bundles carried a manifest: keep the manifest with it.
    const kept = wrangler(["d1", "execute", database.name, ...where, "--config", config, "--json", "--command", manifestBackfill(load).sql[0]]);
    if (kept.status !== 0) throw new Error(`the manifest of bundle ${load.version} was not kept in ${database.name}: ${lastError(`${kept.stdout}${kept.stderr}`)}`);
    return { version: load.version, loaded: false };
  }
  const dir = fs.mkdtempSync(path.join(path.dirname(config), "pairs-sql-"));
  try {
    const file = path.join(dir, "pairs.sql");
    fs.writeFileSync(file, `${load.sql.join(";\n")};\n`);
    const ran = wrangler(["d1", "execute", database.name, ...where, "--config", config, "--yes", "--file", file]);
    if (ran.status !== 0) throw new Error(`bundle ${load.version} did not load into ${database.name}: ${lastError(`${ran.stdout}${ran.stderr}`)}`);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
  return { version: load.version, loaded: true };
}
