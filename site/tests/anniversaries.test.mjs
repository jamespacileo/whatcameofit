// Anniversaries of first reports: the pure functions, then the built page and feed.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { calendarByMonth, recentAnniversaries } from "../src/lib/anniversaries.ts";

const claim = (slug, first) => ({ slug, headline: `Headline ${slug}`, first_reported_date: first });

test("a leap-day report has its anniversary on 28 February in a common year", () => {
  const found = recentAnniversaries([claim("leap", "2020-02-29")], "2026-03-02");
  assert.deepEqual(
    found.map((item) => [item.date, item.years]),
    [["2026-02-28", 6]],
  );
  const leapYear = recentAnniversaries([claim("leap", "2020-02-29")], "2028-03-02");
  assert.deepEqual(
    leapYear.map((item) => item.date),
    ["2028-02-29"],
  );
});

test("a claim with no first-reported date is left out of both", () => {
  const claims = [claim("none", null)];
  assert.deepEqual(calendarByMonth(claims), []);
  assert.deepEqual(recentAnniversaries(claims, "2026-11-11"), []);
});

test("a first report under a year old gives no anniversary", () => {
  assert.deepEqual(recentAnniversaries([claim("new", "2026-08-01")], "2026-11-11"), []);
  assert.deepEqual(recentAnniversaries([claim("year", "2025-11-05")], "2026-11-11").length, 1);
  assert.deepEqual(recentAnniversaries([claim("soon", "2025-11-20")], "2026-11-11"), []);
});

test("the window is thirty days up to and including the date, newest first", () => {
  const found = recentAnniversaries(
    [
      claim("a", "2019-10-13"),
      claim("b", "2020-11-11"),
      claim("c", "2021-10-12"),
      claim("d", "2018-11-05"),
    ],
    "2026-11-11",
  );
  assert.deepEqual(
    found.map((item) => [item.claim.slug, item.date, item.years]),
    [
      ["b", "2026-11-11", 6],
      ["d", "2026-11-05", 8],
      ["a", "2026-10-13", 7],
    ],
  );
});

test("a window that spans new year looks back into the last year", () => {
  const found = recentAnniversaries([claim("x", "2020-12-25")], "2027-01-03");
  assert.deepEqual(
    found.map((item) => [item.date, item.years]),
    [["2026-12-25", 6]],
  );
});

test("the calendar runs by month and day, years in order, and skips undated claims", () => {
  const months = calendarByMonth([
    claim("late", "2024-03-31"),
    claim("none", null),
    claim("early", "2021-03-31"),
    claim("jan", "2022-01-02"),
  ]);
  assert.deepEqual(
    months.map((month) => [month.month, month.days.map((day) => day.id)]),
    [
      [1, ["01-02"]],
      [3, ["03-31"]],
    ],
  );
  assert.deepEqual(
    months[1].days[0].entries.map((entry) => [entry.claim.slug, entry.year]),
    [
      ["early", 2021],
      ["late", 2024],
    ],
  );
});

test("Scenario: the built page lists a claim under its date and the feed dates an anniversary", () => {
  // The fixture's generated_at is 2026-11-11. None of its first reports falls in the
  // thirty days before that, so one claim is moved to 5 November 2021 in a copy.
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  const moved = fixture.claims.find((item) => item.slug === "phase-claim");
  moved.first_reported_date = "2021-11-05";
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-anniv-"));
  const file = path.join(dir, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));
  const out = path.join(dir, "dist");
  const run = () =>
    spawnSync("npx", ["astro", "build", "--outDir", out], {
      env: { ...process.env, EXPORT_FILE: file, ASTRO_TELEMETRY_DISABLED: "1" },
      encoding: "utf8",
    });
  let result = run();
  if (result.status !== 0) result = run();
  assert.equal(result.status, 0, result.stdout + result.stderr);

  const html = fs.readFileSync(path.join(out, "anniversaries/index.html"), "utf8");
  const day = html.match(/<li[^>]*data-day="05-01"[^>]*>[\s\S]*?<\/ul>\s*<\/li>/);
  assert.ok(day, "no 1 May entry");
  assert.match(day[0], /First reported <\/span>2018/);
  assert.match(day[0], /href="\/quiet-claim"/);
  assert.match(day[0], /Synthetic claim that went quiet/);
  assert.match(day[0], /Preclinical only/);
  assert.match(html, /data-day="11-05"/);
  assert.match(html, /<h2 class="bar">May<\/h2>/);

  const xml = fs.readFileSync(path.join(out, "anniversaries.xml"), "utf8");
  assert.match(xml, /^<\?xml version="1.0" encoding="utf-8"\?>\n<feed xmlns="http:\/\/www.w3.org\/2005\/Atom">/);
  assert.equal(xml.split("<entry>").length, 2);
  assert.equal(xml.split("</entry>").length, 2);
  assert.match(xml, /<title>Synthetic claim with a started trial<\/title>/);
  assert.match(xml, /<updated>2026-11-05T00:00:00Z<\/updated>/);
  assert.match(xml, /<summary>First reported 5 Nov 2021\. 5 years on: Phase 2 trial\.<\/summary>/);
  assert.match(xml, /<link href="[^"]+\/phase-claim"\/>/);
  assert.ok(!xml.includes("&nbsp;"));
});
