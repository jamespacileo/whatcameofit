// What must be true before the site is deployed. Pure functions.
// No build, no network and no Cloudflare account.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import { deployProblems, publishAgain, pullRequestWorker } from "../scripts/deploy-checks.mjs";
import { MARKER, previewComment } from "../scripts/pr-preview-comment.mjs";

const PUBLIC = "https://tracker.example.org";

test("Scenario: A public address", () => {
  assert.deepEqual(deployProblems({ siteUrl: PUBLIC }), []);
});

for (const [name, siteUrl] of [
  ["missing", undefined],
  ["local", "http://localhost:4321"],
  ["not https", "http://tracker.example.org"],
  ["not an address", "tracker"],
  ["with a path", "https://example.org/tracker"],
]) {
  test(`Scenario: Address ${name}`, () => {
    const problems = deployProblems({ siteUrl });

    assert.equal(problems.length, 1);
    assert.match(problems[0], /SITE_URL/);
  });
}

test("Scenario: A pull request's copy has its own Worker", () => {
  assert.equal(pullRequestWorker("247"), "thenwhat-pr-247");
  assert.equal(pullRequestWorker(247), "thenwhat-pr-247");
});

for (const number of [undefined, "", "0", "-1", "12 --name thenwhat", "thenwhat", "1.5"]) {
  test(`Scenario: Not a pull request number (${JSON.stringify(number)})`, () => {
    assert.equal(pullRequestWorker(number), null);
  });
}

const PREVIEW = "https://thenwhat-pr-12.example.workers.dev";

test("the comment links the preview, its pages and the build", () => {
  const body = previewComment({
    state: "published",
    url: PREVIEW,
    worker: "thenwhat-pr-12",
    sha: "9e1838e0de388b80467f49aabb40c2dcdfb7fe79",
    repoUrl: "https://github.com/example/tracker",
    runUrl: "https://github.com/example/tracker/actions/runs/7",
    pairs: { count: 15 },
  });

  assert.ok(body.startsWith(MARKER));
  assert.match(body, /\[How it works\]\(https:\/\/thenwhat-pr-12\.example\.workers\.dev\/how-it-works\)/);
  assert.match(body, /15 pairs/);
  assert.match(body, /\[`9e1838e`\]\(https:\/\/github\.com\/example\/tracker\/commit\/9e1838e0/);
  assert.match(body, /\[build log\]\(https:\/\/github\.com\/example\/tracker\/actions\/runs\/7\)/);
});

test("the comment for a copy built from a bundle counts its pairs, as the workflow runs it", () => {
  // The workflow's own call: pr-preview.mjs's outputs passed on as PAIRS_COUNT and PAIRS_VERSION.
  const run = spawnSync(process.execPath, ["scripts/pr-preview-comment.mjs"], {
    encoding: "utf8",
    env: { ...process.env, STATE: "published", PREVIEW_URL: PREVIEW, PR_NUMBER: "12", PAIRS_COUNT: "12", PAIRS_VERSION: "230ee727aab2d32c" },
  });
  assert.equal(run.status, 0, run.stderr);
  assert.match(run.stdout, /12 pairs from bundle `230ee727aab2d32c`/);
  assert.doesNotMatch(run.stdout, /claims/i);
  // There is no Anniversaries page to link (pairs-site task 5.7).
  assert.doesNotMatch(run.stdout, /\/anniversaries/);
});

test("a failed build says so in the same comment and offers no address", () => {
  const body = previewComment({ state: "failed", worker: "thenwhat-pr-12", sha: "abcdef1234" });

  assert.ok(body.startsWith(MARKER));
  assert.match(body, /not updated/i);
  assert.doesNotMatch(body, /workers\.dev/);
});

// Wrangler's own lines from pull request 383's first preview publish (run 44738112545).
const NOT_REGISTERED = "✘ [ERROR] A request to the Cloudflare API (/accounts/0/workers/workers/thenwhat-pr-383) failed.\n\n  This Worker does not exist on your account. [code: 10007]";
const NULL_TAG = "✘ [ERROR] Cannot read properties of null (reading 'tag')";

test("a first preview publish is sent again while Cloudflare has not yet registered its Worker", () => {
  const first = publishAgain(NOT_REGISTERED, false);
  assert.deepEqual(first, { again: true, unregistered: true });
  // The send after it found the Worker half registered: sent again too.
  assert.deepEqual(publishAgain(NULL_TAG, first.unregistered), { again: true, unregistered: true });
});

test("the null tag answer with no 10007 before it, or any other failure, stops the publish", () => {
  assert.deepEqual(publishAgain(NULL_TAG, false), { again: false, unregistered: false });
  assert.equal(publishAgain("✘ [ERROR] Authentication error [code: 10000]", true).again, false);
});
