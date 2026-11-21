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
// --staging deploys the same build to staging instead (docs/deploy.md, "Staging"): the
// thenwhat-staging Worker (wrangler.staging.jsonc), at SITE_URL's address, from the preview
// database pinned by STAGING_PAIRS_DATABASE_ID (its name must end in -preview), with every file
// marked noindex and the Worker marking every response it gives the same (ROBOTS_NOINDEX). It
// never takes --cutover. It publishes with `wrangler versions upload` and `wrangler versions
// deploy`, which change no trigger: the Worker's custom domain, workers.dev address and routes
// stay as the operator set them in the dashboard. One token (CLOUDFLARE_API_TOKEN) holds the
// Editor role on thenwhat-staging and the account's D1 Read: it reads the bundle by D1's query
// endpoint and uploads and deploys the version.
//
//   SITE_URL=https://staging.whatcameofit.com PAIRS_DATABASE=thenwhat-store-preview node scripts/deploy.mjs --staging
//
// Uses the locked project dependency; authenticate with OAuth locally or a CI token.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { STAGING_WORKER, deployProblems, stagingProblems, withNoindex } from "./deploy-checks.mjs";
import { listingFileProblems } from "./listing-checks.mjs";

const SITE_DIR = path.resolve(import.meta.dirname, "..");
const dist = path.join(SITE_DIR, "dist");
const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const cutover = args.includes("--cutover");
const staging = args.includes("--staging");
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
const problems = [
  ...deployProblems({ siteUrl }),
  ...(staging ? stagingProblems({ siteUrl, database: pairsDatabase, cutover }) : []),
  // Staging is published only with the commit it is: the smoke checks hold the host to it.
  ...(staging && !dryRun && !/^[a-f0-9]{40}$/.test(revision ?? "") ? ["Staging is published with the commit it is: set BUILD_REVISION to its full SHA."] : []),
  ...listingFileProblems(),
];
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
  if (!dryRun && !cutover && !staging) stop(["Publishing is the cutover. Rehearse with --dry-run, or give --cutover once the operator has said it can go ahead."]);
  const { exportForDeploy, findDeployDatabase, findStagingDatabase } = await import("./pairs-deploy.mjs");
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-deploy-"));
  process.once("exit", () => fs.rmSync(scratch, { force: true, recursive: true }));
  try {
    const database =
      staging && !pairsLocal
        ? await findStagingDatabase(pairsDatabase, {
            accountId: process.env.CLOUDFLARE_ACCOUNT_ID,
            pinnedId: process.env.STAGING_PAIRS_DATABASE_ID,
            token: process.env.CLOUDFLARE_API_TOKEN,
          })
        : findDeployDatabase(pairsDatabase, { localState: pairsLocal });
    const exported = staging
      ? await exportForDeploy({ base: path.join(SITE_DIR, "wrangler.staging.jsonc"), database, scratch, version: pairsVersion, worker: STAGING_WORKER })
      : await exportForDeploy({ base: path.join(SITE_DIR, "wrangler.jsonc"), database, scratch, version: pairsVersion });
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

// The claims no pair came from keep their pages, as production built them (the operator,
// 2026-11-21; scripts/kept-claims.mjs). A build from a Cloudflare database, which is what staging
// and production publish, is made only with every one of them frozen; a rehearsal from a folder
// or from D1's local engine may use the tests' few, or none.
const keptFolder = process.env.KEPT_CLAIMS_DIR ? path.resolve(SITE_DIR, process.env.KEPT_CLAIMS_DIR) : null;
if (pairs && !pairs.database.local) {
  const { keptProblems } = await import("./kept-claims.mjs");
  const unkept = keptProblems(keptFolder);
  if (unkept.length > 0) stop(unkept);
}

const domain = new URL(siteUrl).hostname;

// The registry search is offered only when its settings are given. The model's key is
// a secret the operator stores once with `wrangler secret put OPENAI_API_KEY`.
// Staging never offers it: its Worker has no saved-results namespace and no model key.
const lookup = !staging && Boolean(process.env.LLM_MODEL && process.env.CONTACT_EMAIL);
const env = {
  ...process.env,
  PUBLIC_BUILD: "1",
  SITE_URL: siteUrl,
  ASTRO_TELEMETRY_DISABLED: "1",
  LOOKUP_URL: lookup ? "/api/lookup" : "",
  PAIRS_BUNDLE: pairs ? pairs.folder : bundleFolder,
  KEPT_CLAIMS_DIR: keptFolder ?? "",
};
delete env.CLOUDFLARE_API_TOKEN;
// The styleguide is for staging only; production never builds it, whatever this shell holds.
if (staging) env.STYLEGUIDE = "1";
else delete env.STYLEGUIDE;
console.log(`Building for ${siteUrl}.`);
run("pnpm", ["run", "build"], env);
if (!staging && fs.existsSync(path.join(dist, "styleguide"))) {
  stop(["The built site holds the styleguide, which only staging and previews may have. Nothing was published."]);
}
if (revision) fs.writeFileSync(path.join(dist, "build-revision.txt"), `${revision}\n`);
// The bundle version the build was made from, for a smoke check to hold the deployment to.
if (pairs) fs.writeFileSync(path.join(dist, "bundle-version.txt"), `${pairs.version}\n`);
// What the bundle holds, for a person to read on the deployment (/bundle-manifest.json, noindex
// in public/_headers) and in this log: its manifest's facts, its pairs and the launch measure.
const factsFolder = pairs ? pairs.folder : bundleFolder;
if (factsFolder) {
  const { bundleFacts, factsLine } = await import("./bundle-facts.mjs");
  const facts = bundleFacts(factsFolder);
  if (pairs && facts.version !== pairs.version) stop([`The exported bundle's manifest names version ${facts.version}, not ${pairs.version}.`]);
  fs.writeFileSync(path.join(dist, "bundle-manifest.json"), `${JSON.stringify(facts, null, 2)}\n`);
  console.log(factsLine(facts));
  // The pair addresses the sitemap lists, beside the pairs: a page left out of it shows here.
  const sitemapPairs = fs.readdirSync(dist).filter((name) => /^sitemap-pairs(-\d+)?\.xml$/.test(name))
    .reduce((sum, name) => sum + (fs.readFileSync(path.join(dist, name), "utf8").match(/<url>/g) ?? []).length, 0);
  console.log(`The sitemap lists ${sitemapPairs.toLocaleString("en-GB")} pair addresses; the manifest counts ${facts.counts?.PairPage?.toLocaleString("en-GB")} pair pages.`);
}

if (!fs.existsSync(path.join(dist, "sitemap.xml"))) {
  stop(["The built site has no sitemap, so it was not built as a public build."]);
}

// Staging is for the operator, never for a search engine: every file it serves says so, and the
// Worker passes the same mark on to the pages it makes (worker/pairs.mjs).
if (staging) {
  const headers = path.join(dist, "_headers");
  fs.writeFileSync(headers, withNoindex(fs.existsSync(headers) ? fs.readFileSync(headers, "utf8") : ""));
}

// The build recorded its bundle's version in the frame the Worker fills, and the Worker
// reads pages of that version only, so it must be the version exported.
if (pairs) {
  const { builtVersion } = await import("./pairs-deploy.mjs");
  const recorded = builtVersion(dist);
  if (recorded !== pairs.version) stop([`The built site records bundle ${recorded ?? "none"}, not ${pairs.version}.`]);
}

// A configuration with pairs carries the rate limit on pages made on request, or is not
// published: the Worker answers without a limit when the binding is missing.
if (pairs) {
  const { limitProblems } = await import("./pairs-preview.mjs");
  const unlimited = limitProblems(pairs.config);
  if (unlimited.length > 0) stop(unlimited);
}

const wranglerArgs = ["deploy", "--domain", domain];
if (pairs) wranglerArgs.push("--config", pairs.config);
if (lookup && !staging) {
  wranglerArgs.push("--var", `LLM_MODEL:${process.env.LLM_MODEL}`, "--var", `CONTACT_EMAIL:${process.env.CONTACT_EMAIL}`);
  for (const name of ["LLM_BASE_URL", "DECISION_BACKEND", "DECISIONS_MODEL"]) {
    if (process.env[name]) wranglerArgs.push("--var", `${name}:${process.env[name]}`);
  }
}
console.log(
  staging
    ? "Without the registry search: staging has no saved-results namespace and no model key."
    : lookup
      ? "With the registry search (/api/lookup)."
      : "Without the registry search: LLM_MODEL and CONTACT_EMAIL are not both set.",
);
if (dryRun) wranglerArgs.push("--dry-run");
const WRANGLER = path.join(SITE_DIR, "node_modules/wrangler/bin/wrangler.js");
if (staging) {
  // A version, then a deployment of it: neither touches a trigger (wrangler's versionsUpload
  // uploads the assets and posts /versions; versions deploy creates a deployment), so the
  // dashboard's custom domain stays attached and workers.dev stays as the operator set it.
  const upload = ["versions", "upload", "--config", pairs.config, "--message", `staging ${revision ?? "local"}`];
  // The contact address is how the trial reader presents itself to the registry, as in previews.
  if (process.env.CONTACT_EMAIL) upload.push("--var", `CONTACT_EMAIL:${process.env.CONTACT_EMAIL}`);
  if (dryRun) upload.push("--dry-run");
  const sent = spawnSync(process.execPath, [WRANGLER, ...upload], { cwd: SITE_DIR, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  process.stdout.write(sent.stdout ?? "");
  process.stderr.write(sent.stderr ?? "");
  if (sent.status !== 0) stop([`"wrangler ${upload.join(" ")}" failed. ${STAGING_WORKER} was not changed.`]);
  if (!dryRun) {
    const id = /Worker Version ID:\s*([0-9a-f-]{36})/.exec(sent.stdout)?.[1];
    if (!id) stop([`The version was uploaded, but Wrangler reported no version id, so it was not deployed.`]);
    run(process.execPath, [WRANGLER, "versions", "deploy", `${id}@100%`, "--config", pairs.config, "--yes", "--message", `staging ${revision ?? "local"}`]);
  }
} else {
  run(process.execPath, [WRANGLER, ...wranglerArgs]);
}
console.log(
  dryRun
    ? pairs
      ? `Dry run finished. Nothing was published. Without --dry-run this would go to ${staging ? `${STAGING_WORKER} (${domain} once its domain is attached)` : domain}, from bundle ${pairs.version}.`
      : "Dry run finished. Nothing was published, and a bundle folder never is."
    : staging
      ? `Deployed ${STAGING_WORKER} from bundle ${pairs.version}, at ${siteUrl} once ${domain} is attached in the dashboard.`
      : `Deployed to ${siteUrl}.`,
);
