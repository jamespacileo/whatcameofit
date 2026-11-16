// Publish one pull request's copy of the site to its own Worker, thenwhat-pr-<number>,
// at a workers.dev address. Production (wrangler.jsonc, the site's own domain) is not
// touched: this script only ever names a thenwhat-pr-* Worker.
//
//   PR_NUMBER=12 node scripts/pr-preview.mjs            build and publish
//   PR_NUMBER=12 node scripts/pr-preview.mjs --dry-run  check and build only
//
// The copy is built from the same reviewed export as production and for the same
// address, so its canonical links point at the real site. Every file is sent with
// "noindex", and the registry search is left out: a copy holds no model key.
// Behaviour: openspec deployment.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { deployProblems, pullRequestWorker } from "./deploy-checks.mjs";

const SITE_DIR = path.resolve(import.meta.dirname, "..");
const dryRun = process.argv.includes("--dry-run");

function stop(lines) {
  console.error(["Not published.", ...lines.map((line) => `  - ${line}`)].join("\n"));
  process.exit(1);
}

const worker = pullRequestWorker(process.env.PR_NUMBER);
if (!worker) stop(["PR_NUMBER is not set to a pull request's number, for example PR_NUMBER=12."]);

const exportFile = path.resolve(SITE_DIR, process.env.EXPORT_FILE ?? "data/published-export.json");
if (!fs.existsSync(exportFile)) stop([`No export at ${exportFile}.`]);
const data = JSON.parse(fs.readFileSync(exportFile, "utf8"));
const siteUrl = process.env.SITE_URL;
const problems = deployProblems({ data, siteUrl });
if (problems.length > 0) stop(problems);

console.log(`Building ${data.claims.length} claims for ${worker}.`);
const build = spawnSync("npm", ["run", "build"], {
  cwd: SITE_DIR,
  stdio: "inherit",
  env: {
    ...process.env,
    PUBLIC_BUILD: "1",
    SITE_URL: siteUrl,
    EXPORT_FILE: exportFile,
    ASTRO_TELEMETRY_DISABLED: "1",
    LOOKUP_URL: "",
  },
});
if (build.status !== 0) stop(["The site did not build."]);

const built = JSON.parse(fs.readFileSync(path.join(SITE_DIR, "dist/lookup.json"), "utf8"));
if (built.preview) stop(["The built site is a preview build."]);

// A copy is for the people reviewing the change, never for a search engine.
fs.appendFileSync(path.join(SITE_DIR, "dist/_headers"), "\n/*\n  X-Robots-Tag: noindex\n");

const args = ["deploy", "--config", "wrangler.preview.jsonc", "--name", worker];
// The contact address is how the trial reader presents itself to the registry.
if (process.env.CONTACT_EMAIL) args.push("--var", `CONTACT_EMAIL:${process.env.CONTACT_EMAIL}`);
if (dryRun) args.push("--dry-run");
const sent = spawnSync(process.execPath, [path.join(SITE_DIR, "node_modules/wrangler/bin/wrangler.js"), ...args], {
  cwd: SITE_DIR,
  stdio: ["inherit", "pipe", "inherit"],
  encoding: "utf8",
});
process.stdout.write(sent.stdout ?? "");
if (sent.status !== 0) stop([`Wrangler failed. ${worker} was not updated by this step.`]);

if (dryRun) {
  console.log(`Dry run finished. Nothing was published. Without --dry-run this would go to ${worker}.`);
} else {
  const address = sent.stdout.match(/https:\/\/[^\s]+\.workers\.dev/g)?.at(-1);
  if (!address) stop([`${worker} was uploaded, but Wrangler reported no workers.dev address for it.`]);
  if (process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, `url=${address}\nworker=${worker}\n`);
  console.log(`Published ${worker} at ${address}.`);
}
