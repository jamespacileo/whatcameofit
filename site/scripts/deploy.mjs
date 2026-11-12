// Deploy the site to Cloudflare. Refuses unless the export is a reviewed, non-preview
// one and SITE_URL is the public address; then builds a public build and hands the
// built files to Wrangler, which serves them at SITE_URL's domain.
//
//   SITE_URL=https://example.org node scripts/deploy.mjs            deploy
//   SITE_URL=https://example.org node scripts/deploy.mjs --dry-run  check and build only
//
// Needs Wrangler on the PATH, signed in to the Cloudflare account that holds the domain.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { deployProblems } from "./deploy-checks.mjs";

const SITE_DIR = path.resolve(import.meta.dirname, "..");
const dryRun = process.argv.includes("--dry-run");

function stop(lines) {
  console.error(["Not deployed.", ...lines.map((line) => `  - ${line}`)].join("\n"));
  process.exit(1);
}

function run(command, args, env = {}) {
  const result = spawnSync(command, args, {
    cwd: SITE_DIR,
    stdio: "inherit",
    env: { ...process.env, ...env },
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

const problems = deployProblems({ data, siteUrl });
if (problems.length > 0) stop(problems);

const domain = new URL(siteUrl).hostname;
// The registry search is offered only when its settings are given. The model's key is
// a secret the operator stores once with `wrangler secret put OPENAI_API_KEY`.
const lookup = Boolean(process.env.LLM_MODEL && process.env.CONTACT_EMAIL);
console.log(`Building ${data.claims.length} claims for ${siteUrl}.`);
run("npm", ["run", "build"], {
  PUBLIC_BUILD: "1",
  SITE_URL: siteUrl,
  EXPORT_FILE: exportFile,
  ASTRO_TELEMETRY_DISABLED: "1",
  LOOKUP_URL: lookup ? "/api/lookup" : "",
});

// The built files are checked too: what is uploaded is what was just built from that export.
const built = JSON.parse(fs.readFileSync(path.join(SITE_DIR, "dist/lookup.json"), "utf8"));
if (built.preview) stop(["The built site is a preview build."]);
if (!fs.existsSync(path.join(SITE_DIR, "dist/sitemap.xml"))) {
  stop(["The built site has no sitemap, so it was not built as a public build."]);
}

const args = ["deploy", "--domain", domain];
if (lookup) {
  args.push("--var", `LLM_MODEL:${process.env.LLM_MODEL}`, "--var", `CONTACT_EMAIL:${process.env.CONTACT_EMAIL}`);
  for (const name of ["LLM_BASE_URL", "DECISION_BACKEND", "DECISIONS_MODEL"]) {
    if (process.env[name]) args.push("--var", `${name}:${process.env[name]}`);
  }
}
console.log(lookup ? "With the registry search (/api/lookup)." : "Without the registry search: LLM_MODEL and CONTACT_EMAIL are not both set.");
if (dryRun) args.push("--dry-run");
run("wrangler", args);
console.log(
  dryRun
    ? `Dry run finished. Nothing was published. Without --dry-run this would go to ${domain}.`
    : `Deployed to ${siteUrl}.`,
);
