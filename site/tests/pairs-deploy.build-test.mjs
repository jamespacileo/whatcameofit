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
import { statements } from "../../store/ingest/scripts/load-pairs.mjs";
import { builtVersion, findDeployDatabase } from "../scripts/pairs-deploy.mjs";
import { loadPairsBundle, pairsConfig } from "../scripts/pairs-preview.mjs";

const BUNDLE = path.resolve("tests/bundle");
const DATABASE = "thenwhat-store";
const scratch = () => fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-deploy-test-"));
// The fixture export's topics are not production's, so the record of topics published is a
// file of this test's own, holding none.
const PUBLISHED_TOPICS = path.join(scratch(), "published-topics.json");
fs.writeFileSync(PUBLISHED_TOPICS, "[]\n");

function deploy(args, env = {}) {
  return spawnSync(process.execPath, ["scripts/deploy.mjs", ...args], {
    encoding: "utf8",
    maxBuffer: 256 * 1024 * 1024,
    env: {
      ...process.env,
      SITE_URL: "https://whatcameofit.com",
      EXPORT_FILE: "tests/fixture-export.json",
      ASTRO_TELEMETRY_DISABLED: "1",
      CI: "1",
      WRANGLER_SEND_METRICS: "false",
      PUBLISHED_TOPICS_FILE: PUBLISHED_TOPICS,
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

test("publishing with pair pages is refused before anything is built, unless it is the cutover", () => {
  const remote = deploy([], { PAIRS_DATABASE: DATABASE });
  assert.equal(remote.status, 1);
  assert.match(remote.stderr, /Publishing with pair pages is the cutover/);
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
  assert.match(run.stdout, new RegExp(`Pair pages: bundle ${version}, ${pairs} pairs, from ${DATABASE} \\(local engine\\)`));
  // The build read that version and recorded it for the pages made on request.
  assert.equal(builtVersion("dist"), version);
  assert.ok(fs.existsSync(path.join("dist", "apitegromab--muscular-atrophy-spinal", "index.html")));
  // Wrangler was given the production Worker with the database bound as PAIRS.
  assert.match(run.stdout, /env\.PAIRS \(thenwhat-store\)/);
  assert.match(run.stdout, new RegExp(`Dry run finished\\. Nothing was published\\..*whatcameofit\\.com, with pair pages from bundle ${version}`));
});
