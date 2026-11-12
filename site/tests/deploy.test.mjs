// What must be true before the site is deployed. Pure function, synthetic exports.
// No build, no network and no Cloudflare account.
import assert from "node:assert/strict";
import { test } from "node:test";
import { deployProblems } from "../scripts/deploy-checks.mjs";

const PUBLIC = "https://tracker.example.org";
const claim = (slug, checked = true) => ({ slug, checked_by_person: checked });
const exported = (claims, preview = false) => ({ schema_version: 1, preview, claims });

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
  const data = exported([claim("quiet-claim"), claim("seeded-claim", false)]);

  const problems = deployProblems({ data, siteUrl: PUBLIC });

  assert.equal(problems.length, 1);
  assert.match(problems[0], /seeded-claim/);
  assert.doesNotMatch(problems[0], /quiet-claim/);
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
  const data = exported([claim("seeded-claim", false)], true);

  assert.equal(deployProblems({ data, siteUrl: undefined }).length, 3);
});
