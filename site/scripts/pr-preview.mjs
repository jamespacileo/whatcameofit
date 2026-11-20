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
// The copy is built from a bundle of pairs (tests/bundle unless PREVIEW_PAIRS_BUNDLE names
// another folder) and for production's address, so its canonical links point at the real
// site. Every file is sent with
// "noindex", and the registry search is left out: a copy holds no model key.
// Behaviour: openspec deployment.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { buildKey } from "./build-key.mjs";
import { deployProblems, publishAgain, pullRequestWorker, withNoindex } from "./deploy-checks.mjs";

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

// How many pairs the published copy's open data index lists; null when it has none.
async function publishedPairs(address) {
  try {
    const answer = await fetch(`${address}/data/pairs.json`, { signal: AbortSignal.timeout(5000) });
    if (!answer.ok) return null;
    const entries = (await answer.json())?.entries;
    return Array.isArray(entries) ? entries.length : null;
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
const siteUrl = process.env.SITE_URL;
// --state runs before dependencies are installed, and the listing's schema check needs
// one, so a listing is checked only where the copy is about to be built.
const { listingFileProblems } = stateOnly ? { listingFileProblems: () => [] } : await import("./listing-checks.mjs");
const problems = [...deployProblems({ siteUrl }), ...listingFileProblems()];
if (problems.length > 0) stop(problems);

// The bundle is a folder of the site unless another is named, so the key below covers it.
const bundle = path.resolve(process.env.PREVIEW_PAIRS_BUNDLE ?? path.join(SITE_DIR, "tests/bundle"));

// The settings the copy is built with, which are also what its key is made from.
const settings = {
  ...process.env,
  PUBLIC_BUILD: "1",
  SITE_URL: siteUrl,
  PAIRS_BUNDLE: bundle,
  ASTRO_TELEMETRY_DISABLED: "1",
  LOOKUP_URL: "",
  // A preview shows the styleguide; production never builds it (scripts/deploy.mjs).
  STYLEGUIDE: "1",
};
delete settings.CLOUDFLARE_API_TOKEN;
const key = buildKey(SITE_DIR, settings);

if (stateOnly) {
  const host = key && (await workersHost());
  const address = host ? `https://${worker}.${host}` : null;
  const same = Boolean(address) && (await publishedKey(address)) === key;
  // A copy says how many pairs it holds, for the comment.
  const pairsCount = same ? await publishedPairs(address) : null;
  output({ key: key ?? "", published: same, ...(same ? { url: address, worker } : {}), ...(pairsCount === null ? {} : { pairs_count: pairsCount }) });
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

// The pages not built ahead (openspec pairs-site, task 4.5): the bundle is loaded into the
// preview account's pairs database, so the copy's Worker makes them on request. Without
// access to that database the copy holds only the pages built ahead, and the log says why.
const { findPairsDatabase, limitProblems, loadPairsBundle, pairsConfig } = await import("./pairs-preview.mjs");
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-preview-"));
process.once("exit", () => fs.rmSync(scratch, { force: true, recursive: true }));
const pairsDatabase = findPairsDatabase();
let pairs = null;
if (pairsDatabase.skip) {
  console.log(`Pages made on request left out of this copy: ${pairsDatabase.skip}.`);
  output({ pairs_count: fs.readdirSync(path.join(bundle, "p12_pair_page")).filter((name) => name.endsWith(".json")).length });
} else {
  if (dryRun) {
    console.log(`Bundle ${bundle} would be loaded into ${pairsDatabase.name}. Nothing is written in a dry run.`);
  } else {
    try {
      const load = loadPairsBundle({
        config: pairsConfig({ base: path.join(SITE_DIR, "wrangler.preview.jsonc"), database: pairsDatabase, scratch }),
        database: pairsDatabase,
        bundle,
      });
      console.log(`Bundle ${load.version} ${load.loaded ? "loaded into" : "already current in"} ${pairsDatabase.name}, in ${seconds(started)} s.`);
      output({ pairs: load.version, pairs_count: fs.readdirSync(path.join(bundle, "p12_pair_page")).filter((name) => name.endsWith(".json")).length });
    } catch (error) {
      stop([`Pair pages: ${error.message}`]);
    }
  }
  pairs = { database: pairsDatabase };
  started = Date.now();
}
console.log(`Building ${worker} from ${bundle}.`);
const build = spawnSync("pnpm", ["run", "build"], {
  cwd: SITE_DIR,
  stdio: "inherit",
  env: settings,
});
if (build.status !== 0) stop(["The site did not build."]);
console.log(`Built in ${seconds(started)} s.`);

// A copy is for the people reviewing the change, never for a search engine.
// Into the existing "/*" rule: a second one would replace it and drop the security headers.
fs.writeFileSync(path.join(SITE_DIR, "dist/_headers"), withNoindex(fs.readFileSync(path.join(SITE_DIR, "dist/_headers"), "utf8")));
// What this copy was made from, so the next push can tell whether it is still current.
if (key) fs.writeFileSync(path.join(SITE_DIR, "dist", KEY_FILE), `${key}\n`);

// With the pairs database, the copy's Worker is the one that makes pages on request.
const deployConfig = pairs ? pairsConfig({ base: "wrangler.preview.jsonc", database: pairs.database, scratch }) : "wrangler.preview.jsonc";
// A configuration with pairs carries the rate limit on pages made on request, or is not published.
if (pairs) {
  const unlimited = limitProblems(deployConfig);
  if (unlimited.length > 0) stop(unlimited);
}
const args = ["deploy", "--config", deployConfig, "--name", worker];
// The contact address is how the trial reader presents itself to the registry.
if (process.env.CONTACT_EMAIL) args.push("--var", `CONTACT_EMAIL:${process.env.CONTACT_EMAIL}`);
if (dryRun) args.push("--dry-run");
started = Date.now();
// A pull request's first publish creates its Worker. Cloudflare can answer a call Wrangler
// makes right after the upload with "This Worker does not exist on your account. [code:
// 10007]" before it has registered the new Worker. That answer, and the half-registered one
// that can follow it, are sent again after a wait (`publishAgain` in deploy-checks.mjs says
// which and why); the upload is idempotent, so a second send uploads nothing already there.
// Any other failure stops at once.
const ATTEMPTS = 4;
const WAIT_MS = 5_000;
let sent;
let unregistered = false;
for (let attempt = 1; ; attempt += 1) {
  sent = spawnSync(process.execPath, [path.join(SITE_DIR, "node_modules/wrangler/bin/wrangler.js"), ...args], {
    cwd: SITE_DIR,
    stdio: ["inherit", "pipe", "pipe"],
    encoding: "utf8",
  });
  process.stdout.write(sent.stdout ?? "");
  process.stderr.write(sent.stderr ?? "");
  const answer = publishAgain(`${sent.stdout}${sent.stderr}`, unregistered);
  unregistered = answer.unregistered;
  if (sent.status === 0 || attempt === ATTEMPTS || !answer.again) break;
  console.log(`Cloudflare had not yet registered ${worker}. Sending again in ${(WAIT_MS * attempt) / 1000} s, attempt ${attempt + 1} of ${ATTEMPTS}.`);
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, WAIT_MS * attempt);
}
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
