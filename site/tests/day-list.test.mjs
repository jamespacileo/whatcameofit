// The home page's day-by-day list (openspec home-day-by-day). Pure functions over the
// fixture export (synthetic data); the day of the last check is passed in.
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import {
  countKinds,
  countsText,
  dayList,
  headingTitle,
  olderClaim,
} from "../src/lib/day-list.ts";

const fixture = JSON.parse(fs.readFileSync(new URL("./fixture-export.json", import.meta.url), "utf8"));
const claim = (slug) => structuredClone(fixture.claims.find((entry) => entry.slug === slug));
const article = (published_date, outlet, title) => ({
  url: `https://outlet.example/${outlet.toLowerCase().replaceAll(" ", "-")}/${published_date}`,
  outlet,
  title,
  published_date,
  archive_url: null,
});
const heading = (list, id) => list.headings.find((entry) => entry.id === id);

// Checked on Wednesday 10 September 2025: the fixture's results posted on 1 September
// are then nine days old, and its promise for the end of 2025 is still to come.
const CHECKED = "2025-09-10T07:00:00Z";

test("Scenario: A day in the last fortnight", () => {
  const phase = claim("phase-claim");
  phase.articles.push(article("2025-09-01", "Example Outlet 5", "A later report"));
  const other = claim("approved-claim");
  other.articles.push(article("2025-09-01", "Example Outlet 6", "Another report that day"));
  const list = dayList([phase, other], CHECKED);
  const day = heading(list, "d-2025-09-01");
  assert.equal(day.span, "day");
  assert.equal(headingTitle(day), "Monday 1 September");
  assert.equal(countsText(countKinds(day.rows)), "2 reports, 1 registry record");
  assert.deepEqual(day.rows.map((row) => row.kind), ["report", "report", "record"]);
});

test("Scenario: Earlier in the year", () => {
  const phase = claim("phase-claim");
  phase.articles.push(article("2025-07-15", "Example Outlet 5", "A summer report"));
  const list = dayList([phase], CHECKED);
  const week = heading(list, "w-2025-07-14");
  assert.equal(week.span, "week");
  assert.equal(headingTitle(week), "Week of 14 July");
  assert.equal(week.rows.length, 1);
});

test("Scenario: An earlier year", () => {
  const list = dayList(fixture.claims, CHECKED);
  const year = heading(list, "y-2017");
  assert.equal(headingTitle(year), "2017");
  assert.deepEqual(year.rows.map((row) => row.claim.slug), ["approved-claim"]);
  // Newest first throughout: every heading is dated on or before the one above it.
  const dates = list.headings.map((entry) => entry.date);
  assert.deepEqual(dates, [...dates].sort().reverse());
  assert.ok(dates.every((date) => date <= "2025-09-10"));
});

test("Scenario: Two outlets on one day", () => {
  const phase = claim("phase-claim");
  phase.articles = [
    article("2025-09-02", "Outlet B", "Zebra title"),
    article("2025-09-02", "Outlet A", "Aardvark title"),
  ];
  const day = heading(dayList([phase], CHECKED), "d-2025-09-02");
  const reports = day.rows.filter((row) => row.kind === "report");
  assert.equal(reports.length, 1);
  // The first title, in the order the Headlines list uses, is the one quoted.
  assert.deepEqual(reports[0].reports.map((report) => report.outlet), ["Outlet A", "Outlet B"]);
});

test("Scenario: One claim reported on two days", () => {
  const list = dayList([claim("quiet-claim")], CHECKED);
  assert.equal(heading(list, "y-2018").rows.filter((row) => row.kind === "report").length, 1);
  assert.equal(heading(list, "y-2019").rows.filter((row) => row.kind === "report").length, 1);
});

test("Scenario: A day with nothing dated", () => {
  const list = dayList(fixture.claims, CHECKED);
  assert.deepEqual(list.week.map((day) => day.date), [
    "2025-09-04", "2025-09-05", "2025-09-06", "2025-09-07", "2025-09-08", "2025-09-09", "2025-09-10",
  ]);
  // Each of the seven keeps its heading, and says nothing is dated when it holds no row.
  for (const day of list.week) {
    const at = heading(list, `d-${day.date}`);
    assert.ok(at, `no heading for ${day.date}`);
    assert.equal(countsText(countKinds(at.rows)), "Nothing dated");
  }
  // A day before the seven has a heading only when something is dated on it.
  assert.equal(heading(list, "d-2025-09-03"), undefined);
  assert.ok(heading(list, "d-2025-09-01"));
});

test("The seven days count news reports, not rows", () => {
  const phase = claim("phase-claim");
  phase.articles = [article("2025-09-09", "Outlet A", "One"), article("2025-09-09", "Outlet B", "Two")];
  const list = dayList([phase], CHECKED);
  assert.equal(list.week.find((day) => day.date === "2025-09-09").reports, 2);
  assert.equal(heading(list, "d-2025-09-09").rows.length, 1);
});

test("Scenario: An export with no day of last check", () => {
  assert.equal(dayList(fixture.claims, null), null);
});

test("Scenario: A report dated after the last check has no heading", () => {
  const phase = claim("phase-claim");
  phase.articles.push(article("2025-09-11", "Outlet A", "Tomorrow's report"));
  const list = dayList([phase], CHECKED);
  assert.ok(list.headings.every((entry) => entry.date <= "2025-09-10"));
  assert.ok(!list.headings.some((entry) => entry.rows.some((row) => row.date === "2025-09-11")));
});

test("Scenario: Promises still to come, and a promise for a past year", () => {
  const list = dayList(fixture.claims, CHECKED);
  assert.deepEqual(list.toCome.map((row) => [row.claim.slug, row.date]), [["quiet-claim", "2025-12-31"]]);
  // Checked a year later, the same promise stands under its year, as a row.
  const later = dayList(fixture.claims, "2026-11-11T11:00:00Z");
  assert.deepEqual(later.toCome, []);
  // The results posted in September 2025 are by then more than ninety days old.
  const rows = heading(later, "y-2025").rows;
  assert.deepEqual(rows.map((row) => row.kind), ["promise"]);
});

test("Scenario: A record that changed nothing", () => {
  const list = dayList(fixture.claims, CHECKED);
  const [row] = heading(list, "d-2025-09-01").rows;
  assert.equal(row.kind, "record");
  assert.equal(row.event.type, "trial_results_posted");
  assert.equal(row.change, null);
});

test("Scenario: An approval that changed the status", () => {
  // The fixture's status became Phase 2 trial on 1 February 2023, the day of a record.
  const phase = claim("phase-claim");
  const list = dayList([phase], "2023-02-10T07:00:00Z");
  const rows = heading(list, "d-2023-02-01").rows.filter((row) => row.kind === "record");
  assert.equal(rows.length, 1);
  assert.deepEqual(rows[0].change, { before: "trial_registered", code: "phase_2" });

  // With a second record that day, only the first listed says so.
  const second = { ...phase.events.find((event) => event.event_date === "2023-02-01"), id: 9999 };
  phase.events.push(second);
  const both = heading(dayList([phase], "2023-02-10T07:00:00Z"), "d-2023-02-01").rows;
  assert.deepEqual(both.map((row) => row.change !== null), [true, false]);
});

test("Scenario: A follow-up paper scored 0.6", () => {
  const phase = claim("phase-claim");
  const paper = phase.events.find((event) => event.event_date === "2023-02-01");
  paper.confidence = 0.6;
  const [row] = heading(dayList([phase], "2023-02-10T07:00:00Z"), "d-2023-02-01").rows;
  assert.equal(row.event.confidence, 0.6);
});

test("Scenario: A record from last year", () => {
  // The approval of 1 April 2024 is more than ninety days before the check.
  const list = dayList([claim("approved-claim")], CHECKED);
  assert.ok(!list.headings.some((entry) => entry.rows.some((row) => row.kind === "record")));
});

test("Scenario: Two readers on one day, and the next day", () => {
  const first = olderClaim(fixture.claims, "2025-09-10");
  assert.equal(first.kind, "report");
  assert.equal(olderClaim(fixture.claims, "2025-09-10").claim.slug, first.claim.slug);
  assert.notEqual(olderClaim(fixture.claims, "2025-09-11").claim.slug, first.claim.slug);
  // Shown as the claim's newest report.
  const quiet = olderClaim([claim("quiet-claim")], "2025-09-10");
  assert.equal(quiet.date, "2019-05-02");
});

test("Scenario: No claim first reported in an earlier year", () => {
  assert.equal(olderClaim(fixture.claims, "2017-06-01"), null);
  assert.equal(dayList(fixture.claims, "2017-06-01T00:00:00Z").older, null);
});
