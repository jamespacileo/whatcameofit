// The home page's lists, each an order over the same claims (openspec browse-lists).
import assert from "node:assert/strict";
import { test } from "node:test";
import { longestWithoutSignal, promisesByDate, statusMoves } from "../src/lib/feed.ts";

const claim = (slug, extra = {}) => ({
  slug,
  headline: `Claim ${slug}`,
  first_reported_date: extra.first ?? "2020-01-01",
  promises: (extra.promises ?? []).map((parsed_date) => ({ parsed_date, description: "trials", article_url: "" })),
  status: { code: "phase_1", overlay_years: extra.quiet ?? null, history: extra.history },
});

test("Scenario: Status changes, newest first", () => {
  const moves = statusMoves([
    claim("a", { history: [{ on: "2019-01-01", code: "preclinical_only" }, { on: "2022-03-01", code: "phase_1" }] }),
    claim("b", { history: [{ on: "2020-01-01", code: "preclinical_only" }] }),
    claim("c", { history: [{ on: "2021-01-01", code: "phase_1" }, { on: "2024-06-01", code: "phase_2" }] }),
    claim("d"),
  ]);
  // A first status is not a change; an export without history gives none.
  assert.deepEqual(moves.map((move) => [move.claim.slug, move.on, move.before, move.code]), [
    ["c", "2024-06-01", "phase_1", "phase_2"],
    ["a", "2022-03-01", "preclinical_only", "phase_1"],
  ]);
});

test("Scenario: Promises in order of their date", () => {
  const listed = promisesByDate([
    claim("late", { promises: ["2030-01-01"] }),
    claim("none", { promises: [null] }),
    // A claim is placed by its latest dated promise.
    claim("two", { promises: ["2021-01-01", "2027-06-30"] }),
    claim("early", { promises: ["2020-06-30"] }),
  ]);
  assert.deepEqual(listed.map((item) => item.slug), ["early", "two", "late"]);
});

test("Scenario: Longest without a new record", () => {
  const listed = longestWithoutSignal([
    claim("three", { quiet: 3 }),
    claim("moving"),
    claim("ten-later", { quiet: 10, first: "2016-01-01" }),
    claim("ten-earlier", { quiet: 10, first: "2015-01-01" }),
  ]);
  assert.deepEqual(listed.map((item) => item.slug), ["ten-earlier", "ten-later", "three"]);
});
