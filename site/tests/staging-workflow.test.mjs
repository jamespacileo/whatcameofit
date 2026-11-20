// Staging and releases (docs/deploy.md, "Staging" and "Releases"): what the two workflows may be
// started by, and what deploy.mjs --staging refuses before it reads or builds anything. The
// workflows are read as GitHub reads them, as YAML.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import { test } from "node:test";
import { parse } from "yaml";

const workflow = (name) => parse(fs.readFileSync(new URL(`../../.github/workflows/${name}`, import.meta.url), "utf8"));

test("staging runs only after CI on main or by hand on main, never for a pull request", () => {
  const staging = workflow("staging.yml");
  // The token is released to these triggers only: a pull_request or pull_request_target
  // trigger would put staging's token within reach of a pull request's code.
  assert.deepEqual(Object.keys(staging.on).sort(), ["workflow_dispatch", "workflow_run"]);
  assert.deepEqual(staging.on.workflow_run, { workflows: ["CI and deploy"], types: ["completed"], branches: ["main"] });
  assert.deepEqual(staging.permissions, { contents: "read" });
  const { publish, off } = staging.jobs;
  assert.equal(publish.environment, "staging");
  assert.match(publish.if, /vars\.STAGING_ENABLED == 'on'/);
  assert.match(publish.if, /github\.event\.workflow_run\.event == 'push'/);
  assert.match(publish.if, /github\.event\.workflow_run\.head_branch == 'main'/);
  assert.match(publish.if, /github\.event_name == 'workflow_dispatch' && github\.ref == 'refs\/heads\/main'/);
  assert.match(off.if, /vars\.STAGING_ENABLED != 'on'/);
  assert.equal(off.environment, undefined, "the job that says staging is off never asks for the environment");
  // The token reaches only the steps after the checkout of main's commit, and no step checks out
  // anything else.
  const checkout = publish.steps.find((step) => String(step.uses).startsWith("actions/checkout@"));
  assert.equal(checkout.with.ref, "${{ github.event.workflow_run.head_sha || github.sha }}");
  assert.equal(checkout.with["persist-credentials"], false);
  const withToken = publish.steps.filter((step) => JSON.stringify(step).includes("secrets."));
  assert.deepEqual(withToken.map((step) => step.name), ["See that staging is set up", "Build, publish and check staging"]);
  assert.ok(withToken.every((step) => publish.steps.indexOf(step) > publish.steps.indexOf(checkout)));
});

test("production is published from a v* tag only, while the operator has publishing on", () => {
  const release = workflow("release.yml");
  assert.deepEqual(release.on, { push: { tags: ["v*"] } });
  assert.deepEqual(release.permissions, { contents: "read" });
  assert.equal(release.jobs.publish.environment, "production");
  assert.match(release.jobs.publish.if, /vars\.PRODUCTION_PUBLISHING == 'on'/);
  assert.match(release.jobs.paused.if, /vars\.PRODUCTION_PUBLISHING != 'on'/);
  const steps = release.jobs.publish.steps.map((step) => step.run ?? "").join("\n");
  assert.match(steps, /git merge-base --is-ancestor "\$GITHUB_SHA" origin\/main/);
  assert.match(steps, /make deploy ARGS=--cutover/);
  // CI on main publishes nothing.
  assert.doesNotMatch(fs.readFileSync(new URL("../../.github/workflows/ci.yml", import.meta.url), "utf8"), /--cutover|deploy-staging|CLOUDFLARE_STAGING/);
});

function deploy(args, env) {
  return spawnSync(process.execPath, ["scripts/deploy.mjs", ...args], {
    encoding: "utf8",
    env: { ...process.env, PAIRS_BUNDLE: "", CLOUDFLARE_API_TOKEN: "", CLOUDFLARE_ACCOUNT_ID: "", STAGING_PAIRS_DATABASE_ID: "", ...env },
  });
}

test("staging refuses production's database, production's address and the cutover, before anything is read", () => {
  const STAGING = { SITE_URL: "https://staging.whatcameofit.com", PAIRS_DATABASE: "thenwhat-store-preview" };
  const cases = [
    [["--staging", "--cutover"], STAGING, /--staging never takes --cutover/],
    [["--staging"], { ...STAGING, PAIRS_DATABASE: "thenwhat-store" }, /Staging reads only a database whose name ends in -preview, not thenwhat-store/],
    [["--staging"], { ...STAGING, PAIRS_DATABASE: "" }, /Staging is built from a database/],
    [["--staging"], { ...STAGING, SITE_URL: "https://whatcameofit.com" }, /SITE_URL is production's address/],
    // The database is found by the id pinned for staging, or not at all.
    [["--staging"], STAGING, /STAGING_PAIRS_DATABASE_ID is not set to the staging database's id/],
  ];
  for (const [args, env, refusal] of cases) {
    const run = deploy(args, env);
    assert.equal(run.status, 1, `${args} ${JSON.stringify(env)}`);
    assert.match(run.stderr, refusal);
    assert.doesNotMatch(run.stdout, /Building/);
  }
});
