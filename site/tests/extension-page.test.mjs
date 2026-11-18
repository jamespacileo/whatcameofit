import assert from "node:assert/strict";
import { test } from "node:test";
import { exampleClaim, latestChange, registryRecords } from "../src/lib/extension-page.ts";

const claim = (slug, status, articles, promised) => ({
  slug,
  status: { code: status },
  articles: Array.from({ length: articles }, (_, index) => ({ published_date: `2020-01-0${index + 1}` })),
  promises: promised ? [{ description: "Trials by 2025", parsed_date: "2025-01-01" }] : [],
});

test("the example claim is on the path, then has a dated promise, then the most reports", () => {
  const claims = [
    claim("off-path", "retracted", 9, true),
    claim("no-promise", "phase_2", 9, false),
    claim("few-reports", "phase_1", 1, true),
    claim("chosen", "phase_3", 2, true),
    claim("also-two", "trial_registered", 2, true),
  ];
  // "also-two" ties on every count; the slug settles it, so a rebuild picks the same claim.
  assert.equal(exampleClaim(claims).slug, "also-two");
  assert.equal(exampleClaim(claims.filter((c) => c.slug !== "also-two")).slug, "chosen");
});

test("a claim whose three answers can all be drawn comes before one with more reports", () => {
  const drawable = {
    ...claim("drawable", "phase_3", 1, true),
    status: { code: "phase_3", history: [{ on: "2020-01-01", code: "phase_2" }, { on: "2024-01-01", code: "phase_3" }] },
    matches: [{ external_id: "NCT1", score: 0.9, url: "https://clinicaltrials.gov/study/NCT1" }],
    events: [{ trial_id: "NCT1", trial_phases: ["phase_3"], trial_state: "started", event_date: "2024-01-01" }],
  };
  assert.equal(exampleClaim([claim("many-reports", "phase_3", 9, true), drawable]).slug, "drawable");
});

test("a claim with no news report is never the example", () => {
  assert.equal(exampleClaim([claim("unreported", "phase_3", 0, true)]), null);
  assert.equal(exampleClaim([]), null);
});

test("the example draws a status change and known records with the furthest phase first", () => {
  const moved = {
    status: { code: "phase_3", history: [{ on: "2019-12-02", code: "phase_2" }, { on: "2024-09-20", code: "phase_3" }] },
    matches: [
      { external_id: "NCT1", score: 0.99, url: "https://clinicaltrials.gov/study/NCT1" },
      { external_id: "NCT2", score: 0.62, url: null },
      { external_id: "NCT-unseen", score: 0.9, url: null },
    ],
    events: [
      { trial_id: "NCT1", trial_phases: ["phase_2"], trial_state: "completed", event_date: "2021-01-01" },
      { trial_id: "NCT2", trial_phases: ["phase_3"], trial_state: null, event_date: "2024-08-14" },
      { trial_id: "NCT2", trial_phases: ["phase_3"], trial_state: "started", event_date: "2024-09-20" },
    ],
  };
  assert.deepEqual(latestChange(moved), { was: "Phase 2 trial", now: "Phase 3 trial", on: "2024-09-20" });
  // Furthest phase first; a match with no record in the export is not drawn.
  assert.deepEqual(registryRecords(moved), [
    { id: "NCT2", url: null, phase: "Phase 3", state: "Started", confidence: "Medium match · 62%" },
    { id: "NCT1", url: "https://clinicaltrials.gov/study/NCT1", phase: "Phase 2", state: "Completed", confidence: "High match · 99%" },
  ]);
});
