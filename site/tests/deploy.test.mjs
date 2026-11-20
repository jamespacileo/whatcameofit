// What must be true before the site is deployed. Pure function, synthetic exports.
// No build, no network and no Cloudflare account.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import { deployProblems, pullRequestWorker } from "../scripts/deploy-checks.mjs";
import { MARKER, addedClaims, previewComment } from "../scripts/pr-preview-comment.mjs";

const PUBLIC = "https://tracker.example.org";
const claim = (slug, checked = true) => ({ slug, checked_by_person: checked });
const exported = (claims, preview = false) => ({ schema_version: 2, preview, claims });

test("Scenario: Reviewed export and a public address", () => {
  const data = exported([claim("quiet-claim"), claim("phase-claim")]);

  assert.deepEqual(deployProblems({ data, siteUrl: PUBLIC }), []);
});

test("Scenario: Preview export", () => {
  const data = exported([claim("quiet-claim")], true);

  const problems = deployProblems({ data, siteUrl: PUBLIC });

  assert.equal(problems.length, 1);
  assert.match(problems[0], /preview/i);
});

test("Scenario: Claim not checked by a person", () => {
  const data = exported([claim("quiet-claim"), claim("rule-approved-claim", false)]);

  assert.deepEqual(deployProblems({ data, siteUrl: PUBLIC }), []);
});

test("an export with no claims is refused", () => {
  assert.match(deployProblems({ data: exported([]), siteUrl: PUBLIC })[0], /no claims/i);
});

for (const [name, siteUrl] of [
  ["missing", undefined],
  ["local", "http://localhost:4321"],
  ["not https", "http://tracker.example.org"],
  ["not an address", "tracker"],
  ["with a path", "https://example.org/tracker"],
]) {
  test(`Scenario: Address ${name}`, () => {
    const problems = deployProblems({ data: exported([claim("quiet-claim")]), siteUrl });

    assert.equal(problems.length, 1);
    assert.match(problems[0], /SITE_URL/);
  });
}

test("every problem is reported at once", () => {
  const data = exported([], true);

  // No address, a preview, and no claims.
  assert.equal(deployProblems({ data, siteUrl: undefined }).length, 3);
});

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

test("the comment links the preview, its pages, the added claims and the build", () => {
  const added = addedClaims(exported([claim("old-claim")]), exported([claim("old-claim"), claim("new-claim")]));
  const body = previewComment({
    state: "published",
    url: PREVIEW,
    worker: "thenwhat-pr-12",
    sha: "9e1838e0de388b80467f49aabb40c2dcdfb7fe79",
    repoUrl: "https://github.com/example/tracker",
    runUrl: "https://github.com/example/tracker/actions/runs/7",
    claims: 2,
    added,
  });

  assert.deepEqual(added, ["new-claim"]);
  assert.ok(body.startsWith(MARKER));
  assert.match(body, /\[How it works\]\(https:\/\/thenwhat-pr-12\.example\.workers\.dev\/how-it-works\)/);
  assert.match(body, /\[new-claim\]\(https:\/\/thenwhat-pr-12\.example\.workers\.dev\/new-claim\)/);
  assert.doesNotMatch(body, /old-claim/);
  assert.match(body, /\[`9e1838e`\]\(https:\/\/github\.com\/example\/tracker\/commit\/9e1838e0/);
  assert.match(body, /\[build log\]\(https:\/\/github\.com\/example\/tracker\/actions\/runs\/7\)/);
});

test("a long list of added claims is cut short and counted", () => {
  const added = Array.from({ length: 25 }, (_, index) => `claim-${index}`);
  const body = previewComment({ state: "published", url: PREVIEW, worker: "thenwhat-pr-12", added });

  assert.equal(body.match(/^- \[claim-/gm).length, 10);
  assert.match(body, /and 15 more/);
});

test("the comment for a copy built from a bundle counts its pairs, as the workflow runs it", () => {
  // The workflow's own call: pr-preview.mjs's outputs passed on as PAIRS_COUNT and PAIRS_VERSION.
  const run = spawnSync(process.execPath, ["scripts/pr-preview-comment.mjs"], {
    encoding: "utf8",
    env: { ...process.env, STATE: "published", PREVIEW_URL: PREVIEW, PR_NUMBER: "12", PAIRS_COUNT: "12", PAIRS_VERSION: "230ee727aab2d32c" },
  });
  assert.equal(run.status, 0, run.stderr);
  assert.match(run.stdout, /12 pairs from bundle `230ee727aab2d32c`/);
  assert.doesNotMatch(run.stdout, /\d+ claims/);
  assert.doesNotMatch(run.stdout, /Claims this pull request adds/);

  const claimsCopy = spawnSync(process.execPath, ["scripts/pr-preview-comment.mjs"], {
    encoding: "utf8",
    env: { ...process.env, STATE: "published", PREVIEW_URL: PREVIEW, PR_NUMBER: "12", PAIRS_COUNT: "", PAIRS_VERSION: "" },
  });
  assert.equal(claimsCopy.status, 0, claimsCopy.stderr);
  assert.doesNotMatch(claimsCopy.stdout, /pairs/);
});

test("a failed build says so in the same comment and offers no address", () => {
  const body = previewComment({ state: "failed", worker: "thenwhat-pr-12", sha: "abcdef1234" });

  assert.ok(body.startsWith(MARKER));
  assert.match(body, /not updated/i);
  assert.doesNotMatch(body, /workers\.dev/);
});
