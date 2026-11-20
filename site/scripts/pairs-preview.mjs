// Pair pages in a pull request's preview (openspec pairs-site, task 4.5). Previews run in
// their own Cloudflare account, which cannot reach the store's databases, so the preview
// account holds one D1 database of its own for pairs, in the EU jurisdiction. Each preview
// loads its bundle there, is built from that bundle, and its Worker (worker/with-pairs.mjs)
// makes the pages not built ahead from it.
//
// When the preview's token cannot read that database, or it does not exist, or it is not in
// the EU, the preview holds only the pages built ahead, and its log says why.
// Production (wrangler.jsonc) is never read or written here.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { manifestBackfill, statements, withChunkedDrops } from "../../store/ingest/scripts/load-pairs.mjs";

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
/**
 * How a deployment with pairs routes between its files and its Worker (openspec pairs-site task
 * 4.6d), set on every configuration written here: a preview's, staging's and the cutover's.
 * The configuration files themselves are left as they are; production's (wrangler.jsonc) is not
 * changed before the cutover.
 *
 * - An address that is a file is served without the Worker: a static asset request is free and
 *   unlimited, while one that runs the Worker first is billed as an invocation
 *   (https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/).
 * - An address no file has reaches the Worker (`not_found_handling: "none"`): a pair's page
 *   (/<a>--<b>), every listing, record, embed and card address, an old claim's address (301 or
 *   410), a saved alias, and a missing page, whose not-found page the Worker sends
 *   (worker/with-pairs.mjs). With "404-page" the files answer such an address themselves and the
 *   Worker is never asked: seen in `wrangler dev`, tests/worker-first.build-test.mjs.
 * - The Worker runs first (WORKER_FIRST) only where a file of the address exists and the Worker
 *   must answer instead: the frames it fills, never served themselves, and the trial reader's
 *   template; and its registry search and trial pages, so they never reach a file. A built
 *   file under /_astro/ matches none of these, so it is served without the Worker, and a missing
 *   one reaches the Worker for the site's not-found page. `*` matches across "/"
 *   (https://developers.cloudflare.com/workers/static-assets/binding/#run_worker_first).
 */
export const WORKER_FIRST = [
  "/pair-shell", "/pair-shell/*", "/embed-shell", "/embed-shell/*",
  "/trial-reader", "/trial-reader/*", "/trial-reader.html",
  "/api/*", "/trials/*",
];

/**
 * The rate limit on addresses made on request (worker/with-pairs.mjs, ON_REQUEST_LIMIT), by
 * Worker: each its own namespace, so staging never uses up production's counts. 600 a minute
 * from one address in one location, ten a second: a search engine's crawler asks far fewer of one
 * location from one address.
 */
export const ON_REQUEST_LIMITS = { thenwhat: "4131", "thenwhat-staging": "4132", "thenwhat-pr": "4133" };
export const ON_REQUEST_LIMIT = { limit: 600, period: 60 };

/**
 * Why a deployment's configuration may not be published: one that binds the pairs database must
 * also bind ON_REQUEST_LIMIT, in its own Worker's namespace, at the site's limit. The Worker
 * answers without a limit when the binding is missing, so that a limiter fault never takes pages
 * down; this check is what keeps a deployment from going out without it.
 * @param {string} file a Wrangler configuration, as pairsConfig writes it
 * @returns {string[]} what is wrong, or nothing
 */
export function limitProblems(file) {
  const config = readConfig(file);
  if (!(config.d1_databases ?? []).some((binding) => binding.binding === "PAIRS")) return [];
  const binding = (config.ratelimits ?? []).find((one) => one.name === "ON_REQUEST_LIMIT");
  if (!binding) return [`${file} binds the pairs database but not ON_REQUEST_LIMIT, the rate limit on pages made on request.`];
  const problems = [];
  const namespace = ON_REQUEST_LIMITS[config.name];
  if (binding.namespace_id !== namespace) problems.push(`${file} gives ON_REQUEST_LIMIT namespace ${binding.namespace_id}, not ${config.name}'s own (${namespace ?? "none"}).`);
  if (binding.simple?.limit !== ON_REQUEST_LIMIT.limit || binding.simple?.period !== ON_REQUEST_LIMIT.period) {
    problems.push(`${file} limits ON_REQUEST_LIMIT to ${binding.simple?.limit} a ${binding.simple?.period} s, not ${ON_REQUEST_LIMIT.limit} a ${ON_REQUEST_LIMIT.period} s.`);
  }
  return problems;
}

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
  config.assets = {
    ...config.assets,
    directory: path.resolve(from, config.assets.directory),
    not_found_handling: "none",
    run_worker_first: WORKER_FIRST,
  };
  if (!ON_REQUEST_LIMITS[worker]) throw new Error(`no rate limit namespace for the ${worker} Worker`);
  config.ratelimits = [
    ...(config.ratelimits ?? []).filter((binding) => binding.name !== "ON_REQUEST_LIMIT"),
    { name: "ON_REQUEST_LIMIT", namespace_id: ON_REQUEST_LIMITS[worker], simple: ON_REQUEST_LIMIT },
  ];
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
    "SELECT version, current, loaded_at, counts FROM pair_bundle"]);
  if (held.status !== 0) throw new Error(`${database.name} could not be read: ${lastError(`${held.stdout}${held.stderr}`)}`);
  const versions = json(held.stdout)[0]?.results ?? [];
  if (versions.find((row) => row.version === load.version)?.current === 1) {
    // Already current, perhaps from before bundles carried a manifest: keep the manifest with it.
    const kept = wrangler(["d1", "execute", database.name, ...where, "--config", config, "--json", "--command", manifestBackfill(load).sql[0]]);
    if (kept.status !== 0) throw new Error(`the manifest of bundle ${load.version} was not kept in ${database.name}: ${lastError(`${kept.stdout}${kept.stderr}`)}`);
    return { version: load.version, loaded: false };
  }
  const dir = fs.mkdtempSync(path.join(path.dirname(config), "pairs-sql-"));
  try {
    const file = path.join(dir, "pairs.sql");
    // The versions that age out are deleted a chunk at a time, inside D1's time a query has.
    fs.writeFileSync(file, `${withChunkedDrops(load, versions).join(";\n")};\n`);
    const ran = wrangler(["d1", "execute", database.name, ...where, "--config", config, "--yes", "--file", file]);
    if (ran.status !== 0) throw new Error(`bundle ${load.version} did not load into ${database.name}: ${lastError(`${ran.stdout}${ran.stderr}`)}`);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
  return { version: load.version, loaded: true };
}
