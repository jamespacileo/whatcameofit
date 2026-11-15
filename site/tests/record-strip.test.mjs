// The record strip (openspec record-strip): a claim's dated records as marks on one
// shared time axis. Pure functions over the fixture export (synthetic data).
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import { STRIP_KEY, STRIP_KEY_ORDER, TABLE_KINDS, axisStart, claimAxis, notches, stripFor } from "../src/lib/record-strip.ts";
import { assertRowSentence, countsLine, sampleSentences, stripName } from "../src/lib/row-sentences.ts";

const fixture = JSON.parse(fs.readFileSync(new URL("./fixture-export.json", import.meta.url), "utf8"));
const claim = (slug) => structuredClone(fixture.claims.find((entry) => entry.slug === slug));
// Dates are set with spaces that do not break; the tests read them as plain spaces.
const plain = (text) => text.replaceAll(" ", " ");
const CHECKED = "2026-11-14";
const event = (type, event_date) => ({ ...claim("phase-claim").events[0], type, event_date });
const kinds = (strip) => strip.marks.map((mark) => mark.kind);
const at = (strip, kind) => strip.marks.find((mark) => mark.kind === kind).at;

/** A claim reported once in 2026 with the given events and promises. */
function reported(events = [], promises = []) {
  const one = claim("phase-claim");
  one.first_reported_date = "2026-11-05";
  one.articles = [{ ...one.articles[0], published_date: "2026-11-05" }];
  one.events = events;
  one.promises = promises;
  return one;
}

test("Scenario: Records before and after a report", () => {
  const strip = stripFor(
    reported([event("trial_registered", "2012-05-10"), event("trial_results_posted", "2015-03-01")]),
    2005,
    CHECKED,
  );
  assert.deepEqual(kinds(strip), ["record", "results", "report"]);
  assert.ok(at(strip, "record") < at(strip, "results"));
  assert.ok(at(strip, "results") < at(strip, "report"));
  assert.ok(at(strip, "report") < 1);
});

test("Scenario: A claim with a report and nothing else", () => {
  const strip = stripFor(reported(), 2005, CHECKED);
  assert.deepEqual(kinds(strip), ["report"]);
  assert.equal(strip.records, 0);
  assert.equal(strip.reports, 1);
});

test("Scenario: A promise with no date in the export", () => {
  const undated = [{ description: "Trials soon", parsed_date: null, article_url: "x" }];
  assert.ok(!kinds(stripFor(reported([], undated), 2005, CHECKED)).includes("promise"));
});

test("Scenario: A promise dated after the last check", () => {
  const promise = (parsed_date) => [{ description: "Trials", parsed_date, article_url: "x" }];
  assert.ok(!kinds(stripFor(reported([], promise("2027-12-31")), 2005, CHECKED)).includes("promise"));
  assert.ok(kinds(stripFor(reported([], promise("2020-12-31")), 2005, CHECKED)).includes("promise"));
});

test("Scenario: Many records in one year", () => {
  const events = Array.from({ length: 78 }, (_, index) =>
    event("trial_status_change", `2019-${String((index % 12) + 1).padStart(2, "0")}-10`),
  );
  const strip = stripFor(reported([...events, event("trial_results_posted", "2019-06-10")]), 2005, CHECKED);
  assert.equal(strip.records, 79);
  // Results keep a kind of their own, so the drawing can set them above the other marks.
  assert.equal(strip.marks.filter((mark) => mark.kind === "results").length, 1);
});

test("Scenario: Two claims in one list share one scale", () => {
  const older = claim("quiet-claim");
  const newer = reported();
  const start = axisStart([older, newer]);
  const first = older.articles.map((article) => article.published_date).sort()[0];
  const a = stripFor(older, start, CHECKED).marks.find((mark) => mark.date === first);
  const b = at(stripFor(newer, start, CHECKED), "report");
  assert.ok(a.at < b);
  // The same day is the same place in both strips.
  older.articles = newer.articles;
  older.events = [];
  assert.equal(at(stripFor(older, start, CHECKED), "report"), b);
});

test("the axis starts at the earliest dated year, taken down to a multiple of five", () => {
  const one = reported([event("trial_registered", "2006-02-01")]);
  const two = reported([event("trial_registered", "2017-02-01")]);
  assert.equal(axisStart([one, two]), 2005);
  assert.deepEqual(
    notches(2005, CHECKED).map((notch) => notch.year),
    [2010, 2015, 2020, 2025],
  );
  assert.throws(() => axisStart([]), /no axis/);
});

test("a regulator's decision has a mark of its own; a retraction is a record like any other", () => {
  const strip = stripFor(
    reported([event("regulatory_decision", "2026-09-03"), event("retraction", "2024-01-01")]),
    2005,
    CHECKED,
  );
  assert.deepEqual(kinds(strip), ["record", "decision", "report"]);
});

test("counts are the export's own, and absent when it holds no list of trials", () => {
  const none = reported();
  none.trials = [];
  assert.equal(countsLine(stripFor(none, 2005, CHECKED).counts), "0 trials");
  delete none.trials;
  assert.equal(stripFor(none, 2005, CHECKED).counts, null);
  assert.equal(countsLine({ trials: 5, results: 2 }), "5 trials · 2 with results posted");
  assert.equal(countsLine({ trials: 1, results: 0 }), "1 trial");
});

test("Scenario: Screen reader on a report row", () => {
  const phase = reported([event("trial_registered", "2012-05-10")]);
  phase.trials = phase.trials.slice(0, 5).map((trial, index) => ({
    ...trial,
    state: index < 3 ? "completed" : "under_way",
    facts: { ...trial.facts, results: index < 2 ? { outcomes: [], outcomes_total: 0 } : null },
  }));
  const strip = stripFor(phase, 2005, CHECKED);
  assert.equal(
    plain(stripName(phase, "2026-11-05", strip, CHECKED)),
    "Records by date. The first trial was registered in 2012, 14 years before this report. 5 trials on record, 3 completed, 2 with results posted.",
  );
  // Each sentence's subject is on the strip or in its counts.
  assert.equal(strip.marks.find((mark) => mark.kind === "record").date.slice(0, 4), "2012");
  assert.deepEqual(strip.counts, { trials: 5, results: 2 });
});

test("a decision the sentences give has its mark at that date", () => {
  const approved = reported([event("regulatory_decision", "2026-09-03")]);
  approved.trials = [];
  const strip = stripFor(approved, 2005, CHECKED);
  assert.match(plain(stripName(approved, "2026-11-05", strip, CHECKED)), /Dated 3 Sep 2026\./);
  assert.equal(strip.marks.find((mark) => mark.kind === "decision").date, "2026-09-03");
});

test("Scenario: A claim with a report and nothing else, read aloud", () => {
  const bare = reported();
  bare.trials = [];
  bare.status = { ...bare.status, overlay_years: null };
  assert.equal(
    plain(stripName(bare, "2026-11-05", stripFor(bare, 2005, CHECKED), CHECKED)),
    "Records by date. 1 news report and no dated record on file as of 14 Nov 2026.",
  );
  // Away from a report's row the years before a report are not counted.
  const old = reported([event("trial_registered", "2012-05-10")]);
  delete old.trials;
  old.status = { ...old.status, overlay_years: null };
  assert.equal(
    plain(stripName(old, "", stripFor(old, 2005, CHECKED), CHECKED)),
    "Records by date. 1 news report and 1 dated record on file as of 14 Nov 2026.",
  );
});

test("the key names six marks, and its wording is checked like a row sentence", () => {
  const named = Object.entries(STRIP_KEY).map(([name]) => name);
  assert.deepEqual([...STRIP_KEY_ORDER].sort(), named.sort());
  assert.equal(STRIP_KEY_ORDER.length, 6);
  assert.throws(() => assertRowSentence("strip key: promise", "Promise still not kept"), /Characterising wording/);
  for (const [name, text] of sampleSentences()) assert.doesNotThrow(() => assertRowSentence(name, text));
});

test("Scenario: A claim's own axis on its page", () => {
  // Reported in 2026 with a trial from 2012: the axis starts at the trial's year.
  const old = claimAxis(reported([event("trial_registered", "2012-05-10")]), CHECKED);
  assert.equal(old.startYear, 2012);
  assert.deepEqual(old.notches.map((notch) => notch.year).slice(0, 2), [2013, 2014]);
  // Reported with nothing before it: five years of axis before the report.
  const bare = claimAxis(reported(), CHECKED);
  assert.equal(bare.startYear, 2021);
  assert.equal(bare.lastChecked, CHECKED);
  // A span longer than fifteen years is notched every five.
  const long = claimAxis(reported([event("trial_registered", "2005-05-10")]), CHECKED);
  assert.deepEqual(long.notches.map((notch) => notch.year), [2010, 2015, 2020, 2025]);
  // A dated promise older than every record reaches the axis back to its year.
  const later = claimAxis(reported([], [{ description: "Trials", parsed_date: "1999-12-31", article_url: "x" }]), CHECKED);
  assert.equal(later.startYear, 1999);
});

test("a list's key names the three marks it draws", () => {
  assert.deepEqual(TABLE_KINDS, ["record", "results", "report"]);
});
