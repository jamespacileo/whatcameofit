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
      confidence: 0.6,
      raw_payload: { secret: true },
    },
  ],
  trials: [
    {
      trial_id: "NCT0",
      source_name: "registry",
      url: "https://registry.example/1",
      title: "A trial",
      phases: ["phase_1"],
      state: "completed",
      facts_as_of: "2024-06-01T00:00:00Z",
      papers: ["10.5555/results"],
      raw_payload: { secret: true },
      facts: {
        study_kind: "interventional",
        participants: { count: 20, basis: "actual" },
        allocation: "randomised",
        masking: "double",
        comparators: ["placebo"],
        healthy_volunteers: true,
        age_groups: ["adult"],
        sponsor: { name: "A hospital", kind: "other" },
        primary_outcomes: [{ measure: "A measure", time_frame: "Study end" }],
        primary_outcomes_total: 1,
        why_stopped: null,
        description: "The sponsor's own conclusion",
        results: {
          outcomes_total: 1,
          outcomes: [
            {
              title: "A measure",
              time_frame: "Study end",
              unit: "units",
              measure: "mean",
              spread_kind: "Standard Deviation",
              rows: 1,
              groups: [
                { title: "Placebo", analysed: "10", value: "3.4", spread: "1.1", lower: null, upper: null, description: "It did well" },
              ],
              comparisons: [{ groups: ["Placebo"], p_value: "0.03", method: "t-test", test: null }],
            },
          ],
        },
      },
    },
  ],
  papers: [
    {
      identifier: "10.5555/results",
      url: "https://doi.org/10.5555/results",
      record_url: "https://index.example/MED/1",
      roles: [
        { role: "trial_result", trial_id: "NCT0", listed: "listed_by_sponsor", decided_by: "rule" },
      ],
      facts_as_of: "2024-06-02T00:00:00Z",
      authors: ["Example A"],
      facts: {
        title: "A report of the trial",
        journal: "Journal of Examples",
        year: 2024,
        kinds: ["randomised_trial", "article"],
        open_access: true,
        retracted: false,
        studied_in: ["people"],
        authorString: "Example A, Sample B.",
        abstractText: "The abstract of the paper",
        affiliation: "A hospital department",
      },
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

test("Scenario: Claim with a trial that has posted results", () => {
  const out = openData(exported(), LICENCE, CREDIT, METHOD);
  const [trial] = out.claims[0].trials;
  assert.equal(trial.facts_as_of, "2024-06-01T00:00:00Z");
  assert.deepEqual(trial.facts.participants, { count: 20, basis: "actual" });
  assert.equal(trial.facts.masking, "double");
  assert.deepEqual(trial.facts.primary_outcomes, [{ measure: "A measure", time_frame: "Study end" }]);
  const [outcome] = trial.facts.results.outcomes;
  assert.equal(outcome.groups[0].value, "3.4");
  assert.equal(outcome.comparisons[0].p_value, "0.03");
  assert.equal(out.claims[0].events[0].confidence, 0.6);
});

test("Scenario: Registry record", () => {
  // Only the fields the claim page shows are copied: no record, and no free text
  // that an export might one day carry beside them.
  const out = openData(exported(), LICENCE, CREDIT, METHOD);
  assert.ok(!everyKey(out).some((name) => /payload/i.test(name)));
  const names = everyKey(out.claims[0].trials);
  assert.ok(!names.some((name) => /payload|description/i.test(name)), names.join());
  assert.ok(!everyString(out).some((text) => /conclusion|did well/.test(text)));
});

test("Scenario: Claim with a results paper", () => {
  const out = openData(exported(), LICENCE, CREDIT, METHOD);
  const [paper] = out.claims[0].papers;
  const [trial] = out.claims[0].trials;
  assert.equal(paper.identifier, "10.5555/results");
  assert.deepEqual(
    [paper.facts.title, paper.facts.journal, paper.facts.year, paper.facts.kinds],
    ["A report of the trial", "Journal of Examples", 2024, ["randomised_trial", "article"]],
  );
  assert.equal(paper.facts_as_of, "2024-06-02T00:00:00Z");
  // The paper names the trial it reports, and the trial lists the paper.
  assert.deepEqual([paper.roles[0].trial_id, paper.roles[0].listed], [trial.trial_id, "listed_by_sponsor"]);
  assert.deepEqual(trial.papers, [paper.identifier]);
});

test("Scenario: Authors", () => {
  const out = openData(exported(), LICENCE, CREDIT, METHOD);
  const names = everyKey(out.claims[0].papers);
  assert.ok(!names.some((name) => /author|abstract|affiliation|payload/i.test(name)), names.join());
  assert.ok(!everyString(out).some((text) => /Example A|The abstract|hospital department/.test(text)));
});

test("an export made before paper facts gives a file with no papers", () => {
  const before = exported();
  for (const entry of before.claims) delete entry.papers;
  assert.deepEqual(openData(before, LICENCE, CREDIT, METHOD).claims[0].papers, []);
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
