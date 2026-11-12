// Retired topic addresses: the redirect file, and the build's refusal to drop a
// published topic without one. Runs scripts/redirects.mjs on its own against a variant
// of tests/fixture-export.json.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

function run({ retired = [], published = null }) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-redirects-"));
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  fixture.retired_verticals = retired;
  const exportFile = path.join(directory, "export.json");
  fs.writeFileSync(exportFile, JSON.stringify(fixture));
  const record = path.join(directory, "published-topics.json");
  if (published) fs.writeFileSync(record, JSON.stringify(published));
  const dist = path.join(directory, "dist");
  fs.mkdirSync(dist);
  const result = spawnSync("node", ["scripts/redirects.mjs"], {
    env: { ...process.env, EXPORT_FILE: exportFile, PUBLISHED_TOPICS_FILE: record, DIST_DIR: dist },
    encoding: "utf8",
  });
  const file = path.join(dist, "_redirects");
  return { result, redirects: fs.existsSync(file) ? fs.readFileSync(file, "utf8") : null };
}

test("Scenario: Vertical renamed after launch", () => {
  const { result, redirects } = run({
    retired: [{ slug: "dental-regeneration", successor: "gum-disease" }],
    published: ["dental-regeneration", "empty-topic"],
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(redirects, "/topic/dental-regeneration /topic/gum-disease 301\n");
});

test("Scenario: Retired vertical with no record", () => {
  const { result } = run({ published: ["dental-regeneration", "gum-disease"] });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /neither current nor retired: dental-regeneration\./);
});

test("before launch nothing is recorded and no redirect file is written", () => {
  const { result, redirects } = run({});
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(redirects, null);
});

test("the previously published transplant topic leads to the health-area directory", () => {
  const { result, redirects } = run({ published: ["transplants"] });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(redirects, "/topic/transplants /topics 301\n");
});
