// The open data file: the pure function, then the built file and page.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { openData } from "../src/lib/open-data.ts";

const LICENCE = "Creative Commons Attribution 4.0 International (CC BY 4.0)";
const CREDIT = "Example credit line";
const METHOD = "https://example.test/how-it-works";

const claim = (slug, extra = {}) => ({
  slug,
  headline: `Headline ${slug}`,
  summary: "A summary.",
  vertical: "topic",
  intervention: { name: "Thing", synonyms: ["Other"] },
  indication: "A condition",
  first_reported_date: "2020-01-01",
  evidence_stage: "preclinical",
  checked_by_person: true,
  status: { code: "phase_1", overlay_years: null, updated_at: "2024-01-01", explained_by: [1] },
  articles: [
    {
      url: "https://news.example/a",
      outlet: "News",
      title: "A report",
      published_date: "2020-01-01",
      archive_url: null,
    },
  ],
  promises: [{ description: "In ten years", parsed_date: "2030-01-01", article_url: "https://news.example/a" }],
  events: [
    {
      id: 1,
      type: "trial_registered",
      event_date: "2021-01-01",
      date_basis: null,
      summary: "A trial.",
      source_name: "registry",
      source_url: "https://registry.example/1",
      trial_id: "NCT0",
      trial_phases: ["PHASE1"],
      trial_state: "recruiting",
      regulatory_outcome: null,
      raw_payload: { secret: true },
    },
  ],
  failure_flags: [],
  ...extra,
});

const exported = (preview = false) => ({
  schema_version: 1,
  generated_at: "2025-01-01T00:00:00Z",
  last_checked_at: "2024-12-31T00:00:00Z",
  preview,
  sources: [{ name: "Registry", url: "https://registry.example" }],
  verticals: [],
  outlets: [{ domain: "news.example", icon: "data:image/png;base64,AAAA", fetched_at: "2024-01-01" }],
  claims: [claim("one"), claim("two")],
});

function everyKey(value, found = []) {
  if (Array.isArray(value)) value.forEach((item) => everyKey(item, found));
  else if (value && typeof value === "object") {
    for (const [name, inner] of Object.entries(value)) {
      found.push(name);
      everyKey(inner, found);
    }
  }
  return found;
}

function everyString(value, found = []) {
  if (typeof value === "string") found.push(value);
  else if (Array.isArray(value)) value.forEach((item) => everyString(item, found));
  else if (value && typeof value === "object") Object.values(value).forEach((item) => everyString(item, found));
  return found;
}

test("the file holds the given claims, the licence and the sources, and no icons or text", () => {
  const out = openData(exported(), LICENCE, CREDIT, METHOD);
  assert.deepEqual(out.claims.map((c) => c.slug), ["one", "two"]);
  assert.equal(out.licence, LICENCE);
  assert.equal(out.credit, CREDIT);
  assert.equal(out.method, METHOD);
  assert.deepEqual(out.sources, [{ name: "Registry", url: "https://registry.example" }]);
  assert.equal(out.preview, false);
  assert.equal(out.last_checked_at, "2024-12-31T00:00:00Z");
  assert.deepEqual(Object.keys(out.claims[0].articles[0]).sort(), [
    "archive_url",
    "outlet",
    "published_date",
    "title",
    "url",
  ]);
  const names = everyKey(out);
  assert.ok(!names.some((name) => /icon|outlets|body|text|payload|failure/i.test(name)), names.join());
  assert.ok(!everyString(out).some((text) => text.startsWith("data:")));
});

test("a preview export gives a preview file", () => {
  assert.equal(openData(exported(true), LICENCE, CREDIT, METHOD).preview, true);
});

test("the built file and page", () => {
  const fixtureFile = "tests/fixture-export.json";
  const fixture = JSON.parse(fs.readFileSync(fixtureFile, "utf8"));
  const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-open-data-"));
  const result = spawnSync("npx", ["astro", "build", "--outDir", dist], {
    env: { ...process.env, EXPORT_FILE: fixtureFile, ASTRO_TELEMETRY_DISABLED: "1" },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);

  const file = JSON.parse(fs.readFileSync(path.join(dist, "data/claims.json"), "utf8"));
  assert.deepEqual(
    file.claims.map((c) => c.slug).sort(),
    fixture.claims.map((c) => c.slug).sort(),
  );
  assert.match(file.licence, /CC BY 4\.0/);
  assert.equal(file.preview, false);
  assert.ok(!everyString(file).some((text) => text.startsWith("data:")));
  const page = fs.readFileSync(path.join(dist, "data/index.html"), "utf8");
  assert.match(page, /href="\/data\/claims\.json"/);

  // A preview export gives a preview file.
  fixture.preview = true;
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-open-data-preview-"));
  const previewFile = path.join(directory, "export.json");
  fs.writeFileSync(previewFile, JSON.stringify(fixture));
  const previewBuild = spawnSync("npx", ["astro", "build", "--outDir", path.join(directory, "dist")], {
    env: { ...process.env, EXPORT_FILE: previewFile, ASTRO_TELEMETRY_DISABLED: "1" },
    encoding: "utf8",
  });
  assert.equal(previewBuild.status, 0, previewBuild.stdout + previewBuild.stderr);
  const previewData = JSON.parse(fs.readFileSync(path.join(directory, "dist/data/claims.json"), "utf8"));
  assert.equal(previewData.preview, true);
});
