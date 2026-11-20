// Deploy the site to Cloudflare. Refuses unless the export is a non-preview one
// and SITE_URL is the public address. Builds locally or takes the checked CI
// build, then hands the files to Wrangler for SITE_URL's domain.
//
//   SITE_URL=https://example.org node scripts/deploy.mjs            deploy
//   SITE_URL=https://example.org node scripts/deploy.mjs --dry-run  check and build only
//   BUILD_REVISION=<sha> node scripts/deploy.mjs --reuse-build     deploy a verified CI build
//
// With pair pages (openspec pairs-site, task 4.4), PAIRS_DATABASE names the D1 database whose
// current bundle version the site is built from; its Worker is worker/with-pairs.mjs with that
// database bound as PAIRS. Until the cutover only a dry run is allowed: publishing with pair
// pages also needs --cutover. PAIRS_LOCAL_STATE reads the database from D1's local engine at
// that folder instead, for a rehearsal on this machine, and is refused without --dry-run.
// PAIRS_VERSION builds from that version instead of the current one: the version before, which
// the store keeps, is how a deployment with pair pages is rolled back without touching D1.
//
//   PAIRS_DATABASE=thenwhat-store node scripts/deploy.mjs --dry-run      rehearse the cutover
//
// Uses the locked project dependency; authenticate with OAuth locally or a CI token.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import os from "node:os";

import { besideProblems } from "./listing-checks.mjs";
import { deployProblems } from "./deploy-checks.mjs";
import { countFiles, FILE_COUNT_LIMIT, FILE_LIMIT, oversizedFiles } from "./dist-size.mjs";
import { prepareSiteRelease, releaseSettings } from "./site-release-deploy.mjs";

const SITE_DIR = path.resolve(import.meta.dirname, "..");
const dist = path.join(SITE_DIR, "dist");
const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const reuse = args.includes("--reuse-build");
const cutover = args.includes("--cutover");
const revision = process.env.BUILD_REVISION;
const pairsDatabase = process.env.PAIRS_DATABASE || null;
const pairsLocal = process.env.PAIRS_LOCAL_STATE || null;
const pairsVersion = process.env.PAIRS_VERSION || null;

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

// Only the pipeline's own export is deployed. The checked-in seed export is a sample
// for a fresh checkout and is never a fallback here.
const exportFile = path.resolve(SITE_DIR, process.env.EXPORT_FILE ?? "data/export.json");
if (!fs.existsSync(exportFile)) {
  stop([`No export at ${exportFile}. Write one first (make public-export).`]);
}
const data = JSON.parse(fs.readFileSync(exportFile, "utf8"));
const siteUrl = process.env.SITE_URL;

// The listing beside the export is held to what staging holds it to: its schema, its
// size, and naming only claims this export publishes.
const problems = [...deployProblems({ data, siteUrl }), ...besideProblems(exportFile, data)];
if (problems.length > 0) stop(problems);

// Pair pages: the bundle is the database's current version, exported to a folder of this
// run. The cutover is one deployment the operator says can go ahead (task 5.2), so until then
// nothing is published with pair pages.
let pairs = null;
if ((pairsLocal || pairsVersion) && !pairsDatabase) stop(["PAIRS_LOCAL_STATE or PAIRS_VERSION was given without PAIRS_DATABASE."]);
if (pairsVersion && !/^[0-9a-f]{16}$/.test(pairsVersion)) stop(["PAIRS_VERSION is not a bundle version (16 hexadecimal characters)."]);
if (pairsDatabase) {
  if (pairsLocal && !dryRun) stop(["A bundle from D1's local engine is for a rehearsal: add --dry-run."]);
  if (!dryRun && !cutover) stop(["Publishing with pair pages is the cutover. Rehearse with --dry-run, or give --cutover once the operator has said it can go ahead."]);
  if (reuse) stop(["A checked CI build is built from no bundle: leave out --reuse-build with PAIRS_DATABASE."]);
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
  console.log(`Pair pages: bundle ${pairs.version}, ${pairs.pairs} pairs, from ${pairs.database.name}${pairs.database.local ? " (local engine)" : ""}.`);
}

const domain = new URL(siteUrl).hostname;
const siteRelease = releaseSettings();
if ((reuse || revision !== undefined) && !/^[a-f0-9]{40}$/.test(revision ?? "")) {
  stop(["BUILD_REVISION must be a full Git commit SHA."]);
}

// The registry search is offered only when its settings are given. The model's key is
// a secret the operator stores once with `wrangler secret put OPENAI_API_KEY`.
const lookup = Boolean(process.env.LLM_MODEL && process.env.CONTACT_EMAIL);
const revisionFile = path.join(dist, "build-revision.txt");
if (!reuse) {
  const env = {
    ...process.env,
    PUBLIC_BUILD: "1",
    SITE_URL: siteUrl,
    EXPORT_FILE: exportFile,
    ASTRO_TELEMETRY_DISABLED: "1",
    LOOKUP_URL: lookup ? "/api/lookup" : "",
    PAIRS_BUNDLE: pairs ? pairs.folder : "",
  };
  delete env.CLOUDFLARE_API_TOKEN;
  env.SITE_RELEASE_BUILD = siteRelease ? "1" : "";
  console.log(`Building ${data.claims.length} claims for ${siteUrl}.`);
  run("pnpm", ["run", "build"], env);
  if (revision) fs.writeFileSync(revisionFile, `${revision}\n`);
} else {
  if (!fs.existsSync(revisionFile) || fs.readFileSync(revisionFile, "utf8").trim() !== revision) {
    stop([`The checked build does not match revision ${revision}.`]);
  }
  console.log(`Publishing the checked build for ${revision}.`);
}

// The built files must agree with the export, including when CI supplies them.
const built = JSON.parse(fs.readFileSync(path.join(dist, "lookup.json"), "utf8"));
if (built.preview) stop(["The built site is a preview build."]);
if (built.generated_at !== data.generated_at) stop(["The built site does not match the public export."]);
if (!fs.existsSync(path.join(dist, "sitemap.xml"))) {
  stop(["The built site has no sitemap, so it was not built as a public build."]);
}

// A build from a bundle recorded its version in the frame the Worker fills, and the Worker
// reads pages of that version only, so it must be the version exported.
if (pairs) {
  const { builtVersion } = await import("./pairs-deploy.mjs");
  const recorded = builtVersion(dist);
  if (recorded !== pairs.version) stop([`The built site records bundle ${recorded ?? "none"}, not ${pairs.version}.`]);
}

const wranglerArgs = ["deploy", "--domain", domain];
if (siteRelease) {
  const config = prepareSiteRelease({ settings: siteRelease, siteDir: SITE_DIR, dist, dryRun, run });
  wranglerArgs.push("--config", pairs ? (await import("./pairs-preview.mjs")).pairsConfig({ base: config, database: pairs.database, scratch: pairs.scratch, worker: "thenwhat" }) : config);
} else if (pairs) {
  wranglerArgs.push("--config", pairs.config);
} else if (reuse && (countFiles(dist) > FILE_COUNT_LIMIT || oversizedFiles(dist, FILE_LIMIT).length)) {
  stop(["The checked build exceeds the static file limits. Configure SITE_FILES_BUCKET for a split release."]);
}
if (lookup) {
  wranglerArgs.push("--var", `LLM_MODEL:${process.env.LLM_MODEL}`, "--var", `CONTACT_EMAIL:${process.env.CONTACT_EMAIL}`);
  for (const name of ["LLM_BASE_URL", "DECISION_BACKEND", "DECISIONS_MODEL"]) {
    if (process.env[name]) wranglerArgs.push("--var", `${name}:${process.env[name]}`);
  }
}
console.log(lookup ? "With the registry search (/api/lookup)." : "Without the registry search: LLM_MODEL and CONTACT_EMAIL are not both set.");
if (dryRun) wranglerArgs.push("--dry-run");
run(process.execPath, [path.join(SITE_DIR, "node_modules/wrangler/bin/wrangler.js"), ...wranglerArgs]);
// CI's staged snapshot already records publication history.
if (!dryRun && !reuse) {
  const record = path.join(SITE_DIR, "data/published-topics.json");
  const before = fs.existsSync(record) ? JSON.parse(fs.readFileSync(record, "utf8")) : [];
  const topics = [...new Set([...before, ...data.verticals.map((vertical) => vertical.slug)])].sort();
  fs.writeFileSync(record, `${JSON.stringify(topics, null, 2)}\n`);
  console.log(`Recorded ${topics.length} published topics in data/published-topics.json; commit it.`);
}
console.log(
  dryRun
    ? `Dry run finished. Nothing was published. Without --dry-run this would go to ${domain}${pairs ? `, with pair pages from bundle ${pairs.version}` : ""}.`
    : `Deployed to ${siteUrl}.`,
);
