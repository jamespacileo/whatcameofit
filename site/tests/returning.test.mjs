// What a returning reader is shown (openspec return-to-home). Pure functions: the
// storage values and the day are passed in.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  changedParts,
  followedRows,
  isSince,
  nextVisit,
  readFollowed,
  sinceOf,
} from "../src/lib/returning.ts";

test("Scenario: A first visit", () => {
  const visit = nextVisit(null, "2026-11-14");
  assert.deepEqual(visit, { current: "2026-11-14", previous: null });
  // With no earlier visit the summary covers the last thirty days.
  assert.deepEqual(sinceOf(visit, "2026-11-14"), { from: "2026-10-15", visited: false });
});

test("Scenario: A later visit", () => {
  const stored = JSON.stringify({ current: "2026-11-07", previous: null });
  const visit = nextVisit(stored, "2026-11-14");
  assert.deepEqual(visit, { current: "2026-11-14", previous: "2026-11-07" });
  assert.deepEqual(sinceOf(visit, "2026-11-14"), { from: "2026-11-07", visited: true });
});

test("Scenario: A second look on the same day", () => {
  // The earlier visit is kept, so what was marked new is still marked after a reload.
  const stored = JSON.stringify({ current: "2026-11-14", previous: "2026-11-07" });
  assert.deepEqual(nextVisit(stored, "2026-11-14"), { current: "2026-11-14", previous: "2026-11-07" });
});

test("Scenario: Storage holds something else", () => {
  for (const raw of ["not json", "[]", '{"current":"tomorrow"}', '{"current":"2030-01-01"}']) {
    assert.deepEqual(nextVisit(raw, "2026-11-14"), { current: "2026-11-14", previous: null }, raw);
  }
  assert.deepEqual(readFollowed("not json"), {});
  assert.deepEqual(readFollowed('{"a":{"status":"Phase 1 trial"},"b":7}'), {});
});

test("Scenario: What is dated since the last visit", () => {
  // The day of the last visit counts; a day still to come does not.
  assert.equal(isSince("2026-11-07", "2026-11-07", "2026-11-14"), true);
  assert.equal(isSince("2026-11-06", "2026-11-07", "2026-11-14"), false);
  assert.equal(isSince("2026-12-31", "2026-11-07", "2026-11-14"), false);
  assert.deepEqual(changedParts({ reports: 12, moves: 1, promises: 0 }), [
    { view: "headlines", text: "12 news reports" },
    { view: "moved", text: "1 status change" },
  ]);
  assert.deepEqual(changedParts({ reports: 0, moves: 0, promises: 2 }), [
    { view: "promised", text: "2 promised dates reached" },
  ]);
  assert.deepEqual(changedParts({ reports: 0, moves: 0, promises: 0 }), []);
});

test("Scenario: A followed claim has changed status", () => {
  const followed = {
    steady: { headline: "Steady claim", status: "Phase 1 trial", since: "2026-11-10" },
    moved: { headline: "Moved claim", status: "Phase 2 trial", since: "2026-10-01" },
    gone: { headline: "Claim taken down", status: "Preclinical only", since: "2026-09-01" },
  };
  const rows = followedRows(followed, {
    steady: { headline: "Steady claim", page: "/steady", status: "Phase 1 trial" },
    moved: { headline: "Moved claim, as now worded", page: "/moved", status: "Phase 3 trial" },
  });
  // The changed claim leads, with the status the reader last saw.
  assert.deepEqual(rows, [
    { slug: "moved", headline: "Moved claim, as now worded", page: "/moved", status: "Phase 3 trial", was: "Phase 2 trial" },
    { slug: "steady", headline: "Steady claim", page: "/steady", status: "Phase 1 trial", was: null },
    // A claim the site no longer lists keeps its stored headline and has no page.
    { slug: "gone", headline: "Claim taken down", page: null, status: null, was: null },
  ]);
});
