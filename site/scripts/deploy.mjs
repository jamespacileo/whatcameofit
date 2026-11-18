// Deploy the site to Cloudflare. Refuses unless the export is a non-preview one
// and SITE_URL is the public address. Builds locally or takes the checked CI
// build, then hands the files to Wrangler for SITE_URL's domain.
//
//   SITE_URL=https://example.org node scripts/deploy.mjs            deploy
//   SITE_URL=https://example.org node scripts/deploy.mjs --dry-run  check and build only
//   BUILD_REVISION=<sha> node scripts/deploy.mjs --reuse-build     deploy a verified CI build
//
// Uses the locked project dependency; authenticate with OAuth locally or a CI token.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { besideProblems } from "./listing-checks.mjs";
import { deployProblems } from "./deploy-checks.mjs";

const SITE_DIR = path.resolve(import.meta.dirname, "..");
const dist = path.join(SITE_DIR, "dist");
const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const reuse = args.includes("--reuse-build");
const revision = process.env.BUILD_REVISION;

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

const domain = new URL(siteUrl).hostname;
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
  };
  delete env.CLOUDFLARE_API_TOKEN;
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

const wranglerArgs = ["deploy", "--domain", domain];
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
    ? `Dry run finished. Nothing was published. Without --dry-run this would go to ${domain}.`
    : `Deployed to ${siteUrl}.`,
);
