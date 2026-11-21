// `make deploy` with pair pages (openspec pairs-site, task 4.4), rehearsed on this machine:
// the bundle loaded into the production database's name on D1's local engine by the store's
// own loader, then deploy.mjs in dry-run mode reads its current version back, exports it,
// builds the site from it and has Wrangler check the production Worker with pairs. Nothing is
// sent to Cloudflare. The refusals that keep the cutover a step the operator takes come first.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { writeManifest } from "../../store/ingest/scripts/bundle-manifest.mjs";
import { statements } from "../../store/ingest/scripts/load-pairs.mjs";
import { builtVersion, findDeployDatabase } from "../scripts/pairs-deploy.mjs";
import { loadPairsBundle, pairsConfig } from "../scripts/pairs-preview.mjs";

const BUNDLE = path.resolve("tests/bundle");
const DATABASE = "thenwhat-store";
const scratch = () => fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-deploy-test-"));

function deploy(args, env = {}) {
  return spawnSync(process.execPath, ["scripts/deploy.mjs", ...args], {
    encoding: "utf8",
    maxBuffer: 256 * 1024 * 1024,
    env: {
      ...process.env,
      SITE_URL: "https://whatcameofit.com",
      PAIRS_BUNDLE: "",
      ASTRO_TELEMETRY_DISABLED: "1",
      CI: "1",
      WRANGLER_SEND_METRICS: "false",
      ...env,
    },
  });
}

/** D1's local engine at a new folder, holding the small bundle as the current version. */
function localStore() {
  const dir = scratch();
  const database = findDeployDatabase(DATABASE, { localState: path.join(dir, "state") });
  const config = pairsConfig({ base: "wrangler.jsonc", database, scratch: dir, worker: "thenwhat" });
  loadPairsBundle({ config, database, bundle: BUNDLE, local: true, persistTo: database.persistTo });
  return database.persistTo;
}

test("publishing is refused before anything is built, unless it is the cutover", () => {
  const remote = deploy([], { PAIRS_DATABASE: DATABASE });
  assert.equal(remote.status, 1);
  assert.match(remote.stderr, /Publishing is the cutover/);
  const local = deploy(["--cutover"], { PAIRS_DATABASE: DATABASE, PAIRS_LOCAL_STATE: scratch() });
  assert.equal(local.status, 1);
  assert.match(local.stderr, /local engine is for a rehearsal: add --dry-run/);
  assert.match(deploy(["--dry-run"], { PAIRS_LOCAL_STATE: scratch() }).stderr, /PAIRS_LOCAL_STATE or PAIRS_VERSION was given without PAIRS_DATABASE/);
  for (const run of [remote, local]) assert.doesNotMatch(run.stdout, /Building/);
});

test("a database holding no current bundle stops the deployment, named", () => {
  const dir = scratch();
  const database = findDeployDatabase(DATABASE, { localState: path.join(dir, "state") });
  // The store's tables, and no bundle in them.
  const config = pairsConfig({ base: "wrangler.jsonc", database, scratch: dir, worker: "thenwhat" });
  const migrated = spawnSync(process.execPath, ["node_modules/wrangler/bin/wrangler.js", "d1", "migrations", "apply", DATABASE,
    "--local", "--persist-to", database.persistTo, "--config", config], { encoding: "utf8", env: { ...process.env, CI: "1" } });
  assert.equal(migrated.status, 0, migrated.stdout + migrated.stderr);
  const run = deploy(["--dry-run"], { PAIRS_DATABASE: DATABASE, PAIRS_LOCAL_STATE: database.persistTo });
  assert.equal(run.status, 1);
  assert.match(run.stderr, /Pair pages: the store holds no current bundle/);
  // A version asked for by name that the store does not keep is refused the same way.
  const named = deploy(["--dry-run"], { PAIRS_DATABASE: DATABASE, PAIRS_LOCAL_STATE: database.persistTo, PAIRS_VERSION: "0123456789abcdef" });
  assert.match(named.stderr, /Pair pages: the store holds no bundle 0123456789abcdef/);
});

test("a dry run reads the current version, builds the site from it and checks the Worker with pairs", () => {
  const { version } = statements(BUNDLE);
  const run = deploy(["--dry-run"], { PAIRS_DATABASE: DATABASE, PAIRS_LOCAL_STATE: localStore() });
  assert.equal(run.status, 0, run.stdout.slice(-4000) + run.stderr.slice(-4000));
  const pairs = fs.readdirSync(path.join(BUNDLE, "p12_pair_page")).length;
  assert.match(run.stdout, new RegExp(`Bundle ${version}, ${pairs} pairs, from ${DATABASE} \\(local engine\\)`));
  // The build read that version and recorded it for the pages made on request.
  assert.equal(builtVersion("dist"), version);
  // No file is built per pair; the frames the Worker fills are.
  assert.ok(!fs.existsSync(path.join("dist", "apitegromab--muscular-atrophy-spinal")));
  assert.ok(fs.existsSync(path.join("dist", "pair-shell", "index.html")) && fs.existsSync(path.join("dist", "embed-shell", "index.html")));
  // Wrangler was given the production Worker with the database bound as PAIRS.
  assert.match(run.stdout, /env\.PAIRS \(thenwhat-store\)/);
  assert.match(run.stdout, new RegExp(`Dry run finished\\. Nothing was published\\..*whatcameofit\\.com, from bundle ${version}`));
});

test("a bundle folder with no database is rehearsed, and never published", () => {
  const refused = deploy([], { PAIRS_BUNDLE: "tests/bundle" });
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /A bundle folder with no database is for a rehearsal/);
  assert.match(deploy(["--dry-run"]).stderr, /No bundle was named/);
  const run = deploy(["--dry-run"], { PAIRS_BUNDLE: "tests/bundle" });
  assert.equal(run.status, 0, run.stdout.slice(-4000) + run.stderr.slice(-4000));
  assert.equal(builtVersion("dist"), statements(BUNDLE).version);
  assert.match(run.stdout, /Nothing was published, and a bundle folder never is\./);
});

test("a sampled trial listing cannot pass a cutover rehearsal", (t) => {
  const dir = scratch();
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  fs.cpSync(BUNDLE, dir, { recursive: true });
  const listing = path.join(dir, "p12_pair_trial_listing");
  fs.mkdirSync(listing);
  fs.copyFileSync("tests/fixture-trials-listing.json", path.join(listing, "listed.json"));
  fs.copyFileSync("trials-listing.schema.json", path.join(dir, "schemas/PairTrialListing.json"));
  const count = JSON.parse(fs.readFileSync(path.join(listing, "listed.json"), "utf8")).trials.length;
  writeManifest(dir, { snapshot: { trial_listing: { run_id: "164310e2a14b", complete: false, registry_total: count + 1, trials_read: count, trials_listed: count } } });
  const run = deploy(["--dry-run", "--cutover"], { PAIRS_BUNDLE: dir });
  assert.equal(run.status, 1);
  assert.match(run.stderr, /no verified full registry run/);
  assert.doesNotMatch(run.stdout, /Building/);
  // Built as if there were no listing, the run's coverage is not asked for.
  const off = deploy(["--dry-run", "--cutover"], { PAIRS_BUNDLE: dir, LISTED_TRIAL_PAGES: "0" });
  assert.doesNotMatch(off.stderr, /no verified full registry run/);
  assert.match(off.stdout, /Building/);
});

test("a trial listing from a local file is never published, to staging or the cutover", () => {
  for (const args of [["--cutover"], ["--staging"]]) {
    const run = deploy(args, { PAIRS_DATABASE: DATABASE, TRIALS_LISTING_FILE: "tests/fixture-trials-listing.json", BUILD_REVISION: "0".repeat(40) });
    assert.equal(run.status, 1, args.join(" "));
    assert.match(run.stderr, /TRIALS_LISTING_FILE is for a rehearsal/);
    assert.doesNotMatch(run.stdout, /Building|Bundle /);
  }
});
