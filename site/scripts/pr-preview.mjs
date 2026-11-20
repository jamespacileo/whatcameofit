// Publish one pull request's copy of the site to its own Worker, thenwhat-pr-<number>,
// at a workers.dev address. Production (wrangler.jsonc, the site's own domain) is not
// touched: this script only ever names a thenwhat-pr-* Worker.
//
//   PR_NUMBER=12 node scripts/pr-preview.mjs            build and publish
//   PR_NUMBER=12 node scripts/pr-preview.mjs --dry-run  check and build only
//   PR_NUMBER=12 node scripts/pr-preview.mjs --state    say whether the copy is already this commit's
//
// A copy carries the key of what it was made from (scripts/build-key.mjs) at
// /build-key.txt. --state reads it back, so a push that changes nothing the site is
// made from publishes nothing. It needs no installed dependencies.
//
// The copy is built from the same reviewed export as production and for the same
// address, so its canonical links point at the real site. Every file is sent with
// "noindex", and the registry search is left out: a copy holds no model key.
// Behaviour: openspec deployment.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { buildKey } from "./build-key.mjs";
import { deployProblems, pullRequestWorker } from "./deploy-checks.mjs";
import { prepareSiteRelease, releaseSettings } from "./site-release-deploy.mjs";

const SITE_DIR = path.resolve(import.meta.dirname, "..");
const dryRun = process.argv.includes("--dry-run");
const stateOnly = process.argv.includes("--state");
const KEY_FILE = "build-key.txt";

function output(pairs) {
  const lines = Object.entries(pairs).map(([name, value]) => `${name}=${value}`).join("\n");
  if (process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, `${lines}\n`);
}

// Where the account's Workers are served, asked of Cloudflare; null when it cannot be learned.
async function workersHost() {
  const { CLOUDFLARE_API_TOKEN: token, CLOUDFLARE_ACCOUNT_ID: account } = process.env;
  if (!token || !account) return null;
  try {
    const answer = await fetch(`https://api.cloudflare.com/client/v4/accounts/${account}/workers/subdomain`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(5000),
    });
    const name = (await answer.json())?.result?.subdomain;
    return typeof name === "string" && /^[a-z0-9-]+$/.test(name) ? `${name}.workers.dev` : null;
  } catch {
    return null;
  }
}

// The key the published copy says it was made from; null when there is no copy or it says nothing.
async function publishedKey(address) {
  try {
    const answer = await fetch(`${address}/${KEY_FILE}`, { signal: AbortSignal.timeout(5000) });
    if (!answer.ok) return null;
    const text = (await answer.text()).trim();
    return /^[0-9a-f]{64}$/.test(text) ? text : null;
  } catch {
    return null;
  }
}

function stop(lines) {
  console.error(["Not published.", ...lines.map((line) => `  - ${line}`)].join("\n"));
  process.exit(1);
}

const worker = pullRequestWorker(process.env.PR_NUMBER);
if (!worker) stop(["PR_NUMBER is not set to a pull request's number, for example PR_NUMBER=12."]);
const siteRelease = releaseSettings(true);

const exportFile = path.resolve(SITE_DIR, process.env.EXPORT_FILE ?? "data/published-export.json");
if (!fs.existsSync(exportFile)) stop([`No export at ${exportFile}.`]);
const data = JSON.parse(fs.readFileSync(exportFile, "utf8"));
const siteUrl = process.env.SITE_URL;
// The listing beside the export is held to what staging holds it to: its schema, its
// size, and naming only claims this export publishes.
// --state runs before dependencies are installed, and the listing's schema check needs
// one, so the listing is checked only where the copy is about to be built.
const { besideProblems } = stateOnly ? { besideProblems: () => [] } : await import("./listing-checks.mjs");
const problems = [...deployProblems({ data, siteUrl }), ...besideProblems(exportFile, data)];
if (problems.length > 0) stop(problems);

// The settings the copy is built with, which are also what its key is made from.
const settings = {
  ...process.env,
  PUBLIC_BUILD: "1",
  SITE_URL: siteUrl,
  EXPORT_FILE: exportFile,
  ASTRO_TELEMETRY_DISABLED: "1",
  LOOKUP_URL: "",
  SITE_RELEASE_BUILD: siteRelease ? "1" : "",
};
delete settings.CLOUDFLARE_API_TOKEN;
const key = buildKey(SITE_DIR, settings);

if (stateOnly) {
  const host = key && (await workersHost());
  const address = host ? `https://${worker}.${host}` : null;
  const same = Boolean(address) && (await publishedKey(address)) === key;
  output({ key: key ?? "", published: same, ...(same ? { url: address, worker } : {}) });
  console.log(
    same
      ? `${worker} at ${address} is already this commit's copy. Nothing to build or send.`
      : `${worker} is to be built and published.`,
  );
  process.exit(0);
}

// How long each part took, in the log, where the timing report can read it.
const seconds = (since) => ((Date.now() - since) / 1000).toFixed(1);
let started = Date.now();

// Pair pages (openspec pairs-site, task 4.5): the bundle is loaded into the preview account's
// pairs database and the copy is built from it, so the pages not built ahead are made by its
// Worker. Without access to that database the copy is the claims site, and the log says why.
// The copy's key is the same either way: the bundle is a folder of the site, in the key already.
const { PREVIEW_PAIRS_BUNDLE, findPairsDatabase, loadPairsBundle, pairsConfig } = await import("./pairs-preview.mjs");
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-preview-"));
process.once("exit", () => fs.rmSync(scratch, { force: true, recursive: true }));
const pairsDatabase = findPairsDatabase();
let pairs = null;
if (pairsDatabase.skip) {
  console.log(`Pair pages left out of this copy: ${pairsDatabase.skip}.`);
  output({ pairs: "left out" });
} else {
  const bundle = path.resolve(process.env.PREVIEW_PAIRS_BUNDLE ?? PREVIEW_PAIRS_BUNDLE);
  if (dryRun) {
    console.log(`Pair pages: bundle ${bundle} would be loaded into ${pairsDatabase.name}. Nothing is written in a dry run.`);
  } else {
    try {
      const load = loadPairsBundle({
        config: pairsConfig({ base: path.join(SITE_DIR, "wrangler.preview.jsonc"), database: pairsDatabase, scratch }),
        database: pairsDatabase,
        bundle,
      });
      console.log(`Pair pages: bundle ${load.version} ${load.loaded ? "loaded into" : "already current in"} ${pairsDatabase.name}, in ${seconds(started)} s.`);
      output({ pairs: load.version });
    } catch (error) {
      stop([`Pair pages: ${error.message}`]);
    }
  }
  pairs = { database: pairsDatabase, bundle };
  settings.PAIRS_BUNDLE = bundle;
  started = Date.now();
}
console.log(`Building ${data.claims.length} claims for ${worker}.`);
const build = spawnSync("pnpm", ["run", "build"], {
  cwd: SITE_DIR,
  stdio: "inherit",
  env: settings,
});
if (build.status !== 0) stop(["The site did not build."]);
console.log(`Built in ${seconds(started)} s.`);

const built = JSON.parse(fs.readFileSync(path.join(SITE_DIR, "dist/lookup.json"), "utf8"));
if (built.preview) stop(["The built site is a preview build."]);

// A copy is for the people reviewing the change, never for a search engine.
fs.appendFileSync(path.join(SITE_DIR, "dist/_headers"), "\n/*\n  X-Robots-Tag: noindex\n");
// What this copy was made from, so the next push can tell whether it is still current.
if (key) fs.writeFileSync(path.join(SITE_DIR, "dist", KEY_FILE), `${key}\n`);

const config = siteRelease ? prepareSiteRelease({
  settings: siteRelease, siteDir: SITE_DIR, dist: path.join(SITE_DIR, "dist"), noindex: true, dryRun,
  run(command, args) {
    const result = spawnSync(command, args, { cwd: SITE_DIR, stdio: "inherit" });
    if (result.status !== 0) stop([`${command} failed while staging the site files.`]);
  },
}) : "wrangler.preview.jsonc";
// With pair pages, the copy's Worker is the one with pairs, given the pairs database.
const deployConfig = pairs ? pairsConfig({ base: config, database: pairs.database, scratch }) : config;
const args = ["deploy", "--config", deployConfig, "--name", worker];
// The contact address is how the trial reader presents itself to the registry.
if (process.env.CONTACT_EMAIL) args.push("--var", `CONTACT_EMAIL:${process.env.CONTACT_EMAIL}`);
if (dryRun) args.push("--dry-run");
started = Date.now();
const sent = spawnSync(process.execPath, [path.join(SITE_DIR, "node_modules/wrangler/bin/wrangler.js"), ...args], {
  cwd: SITE_DIR,
  stdio: ["inherit", "pipe", "inherit"],
  encoding: "utf8",
});
process.stdout.write(sent.stdout ?? "");
if (sent.status !== 0) stop([`Wrangler failed. ${worker} was not updated by this step.`]);
console.log(`${dryRun ? "Checked" : "Sent"} in ${seconds(started)} s.`);

if (dryRun) {
  console.log(`Dry run finished. Nothing was published. Without --dry-run this would go to ${worker}.`);
} else {
  const address = sent.stdout.match(/https:\/\/[^\s]+\.workers\.dev/g)?.at(-1);
  if (!address) stop([`${worker} was uploaded, but Wrangler reported no workers.dev address for it.`]);
  output({ url: address, worker });
  console.log(`Published ${worker} at ${address}.`);
}
