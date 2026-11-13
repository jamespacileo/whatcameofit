// A reminder is one event on a date the reader chose, made without the network.
import assert from "node:assert/strict";
import { test } from "node:test";
import { calendarFile, reminderDate } from "../src/lib/calendar.ts";

const dates = { today: "2026-11-13", promiseDue: "2027-12-31", firstReported: "2021-03-31" };

test("each choice stands for one date after today", () => {
  assert.equal(reminderDate("promise", dates), "2027-12-31");
  assert.equal(reminderDate("six-months", dates), "2027-05-13");
  assert.equal(reminderDate("year", dates), "2027-11-13");
  assert.equal(reminderDate("anniversary", dates), "2027-03-31");
});

test("a promise is offered only when it is dated and still to come", () => {
  assert.equal(reminderDate("promise", { ...dates, promiseDue: null }), null);
  assert.equal(reminderDate("promise", { ...dates, promiseDue: "2025-12-31" }), null);
  assert.equal(reminderDate("promise", { ...dates, promiseDue: "2026-11-13" }), null);
});

test("an anniversary still to come this year is this year's", () => {
  assert.equal(reminderDate("anniversary", { ...dates, firstReported: "2020-12-01" }), "2026-12-01");
  assert.equal(reminderDate("anniversary", { ...dates, firstReported: null }), null);
});

test("a day a month does not have becomes that month's last day", () => {
  assert.equal(reminderDate("six-months", { ...dates, today: "2026-08-31" }), "2027-02-28");
  assert.equal(
    reminderDate("anniversary", { ...dates, today: "2026-03-01", firstReported: "2024-02-29" }),
    "2027-02-28",
  );
});

const file = calendarFile({
  site: "What came of it?",
  headline: "Antibody against USAG-1 regrows teeth in mice; a long, long headline, with commas",
  url: "https://example.test/tooth-regrowth-usag1",
  slug: "tooth-regrowth-usag1",
  date: "2027-12-31",
  madeAt: "2026-11-13T12:20:00.000Z",
});
const lines = file.split("\r\n");
const unfolded = file.replaceAll("\r\n ", "").split("\r\n");

test("the file holds one all-day event on the chosen date", () => {
  assert.equal(lines.filter((line) => line === "BEGIN:VEVENT").length, 1);
  assert.ok(unfolded.includes("DTSTART;VALUE=DATE:20271231"));
  assert.ok(unfolded.includes("DTEND;VALUE=DATE:20280101"));
  assert.ok(unfolded.includes("DTSTAMP:20261113T122000Z"));
  assert.ok(unfolded.includes("UID:tooth-regrowth-usag1-20271231@example.test"));
  assert.ok(file.endsWith("END:VCALENDAR\r\n"));
});

test("the event names the claim and links to its page", () => {
  assert.ok(
    unfolded.includes(
      "SUMMARY:What came of it? Antibody against USAG-1 regrows teeth in mice\\; a long\\, long headline\\, with commas",
    ),
  );
  assert.ok(unfolded.includes("URL:https://example.test/tooth-regrowth-usag1"));
  assert.ok(
    unfolded.includes("DESCRIPTION:Look at the record again: https://example.test/tooth-regrowth-usag1"),
  );
});

test("no line is longer than the format allows", () => {
  const encoder = new TextEncoder();
  for (const line of lines) assert.ok(encoder.encode(line).length <= 75, line);
});
