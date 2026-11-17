// The home page's one claim, reported and on record (openspec home-then-now): how long
// ago a report was, in whole years to the day the registries were last checked.
import assert from "node:assert/strict";
import { test } from "node:test";
import { yearsOn } from "../src/lib/then-now.ts";

test("whole years are counted to the day checked", () => {
  assert.equal(yearsOn("2021-03-31", "2026-11-17"), "5 years on");
  assert.equal(yearsOn("2021-11-18", "2026-11-17"), "4 years on");
  assert.equal(yearsOn("2021-11-17", "2026-11-17"), "5 years on");
  assert.equal(yearsOn("2025-11-17T09:00:00Z", "2026-11-17"), "1 year on");
});

test("a report under a year old says nothing", () => {
  assert.equal(yearsOn("2026-04-13", "2026-11-17"), null);
  assert.equal(yearsOn("2026-11-17", "2026-11-17"), null);
});
