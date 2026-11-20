// Staging and releases (docs/deploy.md, "Staging" and "Releases"): what the two workflows may be
// started by, and what deploy.mjs --staging refuses before it reads or builds anything. The
// workflows are read as GitHub reads them, as YAML.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
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
  // Every waiting run is kept, so a late older run cannot push the tip's run out of the queue.
  assert.deepEqual(staging.concurrency, { group: "staging", "cancel-in-progress": false, queue: "max" });
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
  // The commit checked out is the one the tip guard found to be main's tip.
  assert.equal(publish.steps[0].id, "tip");
  assert.equal(checkout.with.ref, "${{ steps.tip.outputs.sha }}");
  assert.equal(checkout.if, "steps.tip.outputs.current == 'true'");
  assert.equal(checkout.with["persist-credentials"], false);
  const withToken = publish.steps.filter((step) => JSON.stringify(step).includes("secrets."));
  assert.deepEqual(withToken.map((step) => step.name), ["See that staging is set up", "Build, publish and check staging"]);
  assert.ok(withToken.every((step) => publish.steps.indexOf(step) > publish.steps.indexOf(checkout)));
  // Dependencies are installed before any token is in reach, with no secret of their own.
  for (const job of [publish, workflow("release.yml").jobs.publish]) {
    const install = job.steps.findIndex((step) => step.name === "Install dependencies");
    assert.ok(install >= 0);
    assert.ok(!JSON.stringify(job.steps[install]).includes("secrets."));
    assert.ok(job.steps.every((step, at) => !JSON.stringify(step).includes("secrets.") || at > install));
  }
});

test("production is published from a v* tag only, while the operator has publishing on", () => {
  const release = workflow("release.yml");
  assert.deepEqual(release.on, { push: { tags: ["v*"] } });
  assert.deepEqual(release.permissions, { contents: "read", actions: "read" });
  assert.equal(release.jobs.publish.environment, "production");
  assert.match(release.jobs.publish.if, /vars\.PRODUCTION_PUBLISHING == 'on'/);
  assert.match(release.jobs.paused.if, /vars\.PRODUCTION_PUBLISHING != 'on'/);
  const steps = release.jobs.publish.steps.map((step) => step.run ?? "").join("\n");
  assert.match(steps, /git merge-base --is-ancestor "\$GITHUB_SHA" origin\/main/);
  assert.match(steps, /make deploy ARGS=--cutover/);
  // CI must have passed for the tagged commit before it is published, and the live site is
  // checked after, in that order.
  const order = ["git merge-base --is-ancestor", "actions/workflows/ci.yml/runs?head_sha=$GITHUB_SHA&event=push&branch=main&status=success", "make deploy ARGS=--cutover", "node site/scripts/smoke-live.mjs"];
  const at = order.map((text) => steps.indexOf(text));
  assert.ok(at.every((index) => index >= 0), JSON.stringify(at));
  assert.deepEqual([...at].sort((a, b) => a - b), at);
  // CI on main publishes nothing.
  assert.doesNotMatch(fs.readFileSync(new URL("../../.github/workflows/ci.yml", import.meta.url), "utf8"), /--cutover|deploy-staging|CLOUDFLARE_STAGING/);
});

function deploy(args, env) {
  return spawnSync(process.execPath, ["scripts/deploy.mjs", ...args], {
    encoding: "utf8",
    env: { ...process.env, PAIRS_BUNDLE: "", CLOUDFLARE_API_TOKEN: "", CLOUDFLARE_ACCOUNT_ID: "", STAGING_PAIRS_DATABASE_ID: "", BUILD_REVISION: "", ...env },
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
    [["--staging"], { ...STAGING, BUILD_REVISION: "0".repeat(40) }, /STAGING_PAIRS_DATABASE_ID is not set to the staging database's id/],
    // Staging is published only with the commit it is, which the smoke checks hold it to.
    [["--staging"], STAGING, /Staging is published with the commit it is: set BUILD_REVISION/],
  ];
  for (const [args, env, refusal] of cases) {
    const run = deploy(args, env);
    assert.equal(run.status, 1, `${args} ${JSON.stringify(env)}`);
    assert.match(run.stderr, refusal);
    assert.doesNotMatch(run.stdout, /Building/);
  }
});

test("no run step of staging or release puts an expression into shell text", () => {
  // A tag's name, a commit or an event's field reaches a script as a quoted variable set in
  // env, never as text GitHub writes into the script, which would run whatever it holds.
  for (const name of ["staging.yml", "release.yml"]) {
    for (const [id, job] of Object.entries(workflow(name).jobs)) {
      for (const step of job.steps) {
        if (step.run) assert.ok(!step.run.includes("${{"), `${name} ${id} "${step.name ?? step.run.slice(0, 40)}" puts an expression into its script`);
      }
    }
  }
});

/** A git remote whose main is at the commit returned, on this machine. */
function remoteWithMain() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-staging-tip-"));
  const git = (...args) => spawnSync("git", args, { cwd: dir, encoding: "utf8", env: { ...process.env, GIT_AUTHOR_NAME: "t", GIT_AUTHOR_EMAIL: "t@example.org", GIT_COMMITTER_NAME: "t", GIT_COMMITTER_EMAIL: "t@example.org" } });
  git("init", "-q", "-b", "main");
  git("commit", "-q", "--allow-empty", "-m", "older");
  const older = git("rev-parse", "HEAD").stdout.trim();
  git("commit", "-q", "--allow-empty", "-m", "tip");
  return { remote: dir, older, tip: git("rev-parse", "HEAD").stdout.trim() };
}

/** The tip guard's own script, run as the job runs it, with its outputs. */
function guard(env) {
  const script = workflow("staging.yml").jobs.publish.steps[0].run;
  const output = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-staging-output-")), "output");
  fs.writeFileSync(output, "");
  const run = spawnSync("bash", ["-e", "-c", script], { encoding: "utf8", env: { ...process.env, GITHUB_OUTPUT: output, ...env } });
  return { run, outputs: Object.fromEntries(fs.readFileSync(output, "utf8").trim().split("\n").filter(Boolean).map((line) => line.split("="))) };
}

test("staging publishes main's tip only: an older CI run is skipped, and a run by hand takes the tip", () => {
  const { remote, older, tip } = remoteWithMain();
  const late = guard({ EVENT: "workflow_run", RUN_SHA: older, REMOTE: remote });
  assert.equal(late.run.status, 0, late.run.stderr);
  assert.deepEqual(late.outputs, { current: "false" });
  assert.match(late.run.stdout, new RegExp(`Staging was skipped: this CI run is for ${older}, and main is now at ${tip}`));
  const current = guard({ EVENT: "workflow_run", RUN_SHA: tip, REMOTE: remote });
  assert.deepEqual(current.outputs, { sha: tip, current: "true" });
  const byHand = guard({ EVENT: "workflow_dispatch", RUN_SHA: "", REMOTE: remote });
  assert.deepEqual(byHand.outputs, { sha: tip, current: "true" });
  // A remote that cannot be read stops the run: nothing is published on a guess.
  const unread = guard({ EVENT: "workflow_run", RUN_SHA: tip, REMOTE: path.join(remote, "missing") });
  assert.notEqual(unread.run.status, 0);
});
