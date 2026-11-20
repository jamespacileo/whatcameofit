// Deploy the site to Cloudflare. The site is built from one bundle of pairs and nothing else
// (openspec pairs-site). Refuses unless SITE_URL is the public address. Builds, then hands
// the files to Wrangler for SITE_URL's domain.
//
//   PAIRS_DATABASE=thenwhat-store node scripts/deploy.mjs --dry-run    rehearse: check and build only
//   PAIRS_DATABASE=thenwhat-store node scripts/deploy.mjs --cutover    deploy
//   PAIRS_BUNDLE=tests/bundle node scripts/deploy.mjs --dry-run        rehearse from a folder
//
// PAIRS_DATABASE names the D1 database whose current bundle version the site is built from;
// its Worker is worker/with-pairs.mjs with that database bound as PAIRS, so the pages not
// built ahead are made on request from the same version. Until the cutover only a dry run is
// allowed: publishing also needs --cutover, which the operator gives once (task 5.2).
// PAIRS_LOCAL_STATE reads the database from D1's local engine at that folder instead, for a
// rehearsal on this machine, and is refused without --dry-run. PAIRS_VERSION builds from
// that version instead of the current one: the version before, which the store keeps, is how
// a deployment is rolled back without touching D1.
//
// PAIRS_BUNDLE alone names a bundle folder, with no database: a rehearsal of the public
// build that needs no Cloudflare account, which is what CI runs. It is never published,
// because a Worker with no database could make no page on request.
//
// Uses the locked project dependency; authenticate with OAuth locally or a CI token.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { deployProblems } from "./deploy-checks.mjs";
import { listingFileProblems } from "./listing-checks.mjs";

const SITE_DIR = path.resolve(import.meta.dirname, "..");
const dist = path.join(SITE_DIR, "dist");
const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const cutover = args.includes("--cutover");
const revision = process.env.BUILD_REVISION;
const pairsDatabase = process.env.PAIRS_DATABASE || null;
const pairsLocal = process.env.PAIRS_LOCAL_STATE || null;
const pairsVersion = process.env.PAIRS_VERSION || null;
const bundleFolder = process.env.PAIRS_BUNDLE ? path.resolve(SITE_DIR, process.env.PAIRS_BUNDLE) : null;

function stop(lines) {
  console.error(["Not deployed.", ...lines.map((line) => `  - ${line}`)].join("\n"));
  process.exit(1);
}

function run(command, args, env = process.env) {
  const result = spawnSync(command, args, {
    cwd: SITE_DIR,
    stdio: "inherit",
    env,
  });
  if (result.error?.code === "ENOENT") {
    stop([`"${command}" was not found. Install it and try again.`]);
  }
  if (result.status !== 0) {
    stop([`"${command} ${args.join(" ")}" failed. Nothing was published by this step.`]);
  }
}

const siteUrl = process.env.SITE_URL;
const problems = [...deployProblems({ siteUrl }), ...listingFileProblems()];
if (problems.length > 0) stop(problems);
if (revision !== undefined && !/^[a-f0-9]{40}$/.test(revision)) stop(["BUILD_REVISION must be a full Git commit SHA."]);

// The bundle is the database's current version, exported to a folder of this run. The
// cutover is one deployment the operator says can go ahead (task 5.2), so until then
// nothing is published.
let pairs = null;
if ((pairsLocal || pairsVersion) && !pairsDatabase) stop(["PAIRS_LOCAL_STATE or PAIRS_VERSION was given without PAIRS_DATABASE."]);
if (pairsVersion && !/^[0-9a-f]{16}$/.test(pairsVersion)) stop(["PAIRS_VERSION is not a bundle version (16 hexadecimal characters)."]);
if (pairsDatabase) {
  if (pairsLocal && !dryRun) stop(["A bundle from D1's local engine is for a rehearsal: add --dry-run."]);
  if (!dryRun && !cutover) stop(["Publishing is the cutover. Rehearse with --dry-run, or give --cutover once the operator has said it can go ahead."]);
  const { exportForDeploy, findDeployDatabase } = await import("./pairs-deploy.mjs");
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-deploy-"));
  process.once("exit", () => fs.rmSync(scratch, { force: true, recursive: true }));
  try {
    const database = findDeployDatabase(pairsDatabase, { localState: pairsLocal });
    const exported = await exportForDeploy({ base: path.join(SITE_DIR, "wrangler.jsonc"), database, scratch, version: pairsVersion });
    pairs = { database, scratch, ...exported };
  } catch (error) {
    stop([`Pair pages: ${error.message}`]);
  }
  console.log(`Bundle ${pairs.version}, ${pairs.pairs} pairs, from ${pairs.database.name}${pairs.database.local ? " (local engine)" : ""}.`);
} else if (bundleFolder) {
  if (!dryRun) stop(["A bundle folder with no database is for a rehearsal: add --dry-run, or name the database with PAIRS_DATABASE."]);
  if (!fs.existsSync(path.join(bundleFolder, "manifest.json"))) stop([`No bundle at ${bundleFolder}.`]);
  console.log(`Bundle folder ${bundleFolder}, with no database: a rehearsal of the build.`);
} else {
  stop(["No bundle was named. Set PAIRS_DATABASE to the D1 database the site is built from."]);
}

const domain = new URL(siteUrl).hostname;

// The registry search is offered only when its settings are given. The model's key is
// a secret the operator stores once with `wrangler secret put OPENAI_API_KEY`.
const lookup = Boolean(process.env.LLM_MODEL && process.env.CONTACT_EMAIL);
const env = {
  ...process.env,
  PUBLIC_BUILD: "1",
  SITE_URL: siteUrl,
  ASTRO_TELEMETRY_DISABLED: "1",
  LOOKUP_URL: lookup ? "/api/lookup" : "",
  PAIRS_BUNDLE: pairs ? pairs.folder : bundleFolder,
};
delete env.CLOUDFLARE_API_TOKEN;
console.log(`Building for ${siteUrl}.`);
run("pnpm", ["run", "build"], env);
if (revision) fs.writeFileSync(path.join(dist, "build-revision.txt"), `${revision}\n`);

if (!fs.existsSync(path.join(dist, "sitemap.xml"))) {
  stop(["The built site has no sitemap, so it was not built as a public build."]);
}

// The build recorded its bundle's version in the frame the Worker fills, and the Worker
// reads pages of that version only, so it must be the version exported.
if (pairs) {
  const { builtVersion } = await import("./pairs-deploy.mjs");
  const recorded = builtVersion(dist);
  if (recorded !== pairs.version) stop([`The built site records bundle ${recorded ?? "none"}, not ${pairs.version}.`]);
}

const wranglerArgs = ["deploy", "--domain", domain];
if (pairs) wranglerArgs.push("--config", pairs.config);
if (lookup) {
  wranglerArgs.push("--var", `LLM_MODEL:${process.env.LLM_MODEL}`, "--var", `CONTACT_EMAIL:${process.env.CONTACT_EMAIL}`);
  for (const name of ["LLM_BASE_URL", "DECISION_BACKEND", "DECISIONS_MODEL"]) {
    if (process.env[name]) wranglerArgs.push("--var", `${name}:${process.env[name]}`);
  }
}
console.log(lookup ? "With the registry search (/api/lookup)." : "Without the registry search: LLM_MODEL and CONTACT_EMAIL are not both set.");
if (dryRun) wranglerArgs.push("--dry-run");
run(process.execPath, [path.join(SITE_DIR, "node_modules/wrangler/bin/wrangler.js"), ...wranglerArgs]);
console.log(
  dryRun
    ? pairs
      ? `Dry run finished. Nothing was published. Without --dry-run this would go to ${domain}, from bundle ${pairs.version}.`
      : "Dry run finished. Nothing was published, and a bundle folder never is."
    : `Deployed to ${siteUrl}.`,
);
