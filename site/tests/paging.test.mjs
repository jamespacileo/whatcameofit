// Which rows a page of a long list holds (openspec browse-lists).
import assert from "node:assert/strict";
import { test } from "node:test";
import { pageLine, pageOf } from "../src/lib/paging.ts";

test("Scenario: More rows than one page", () => {
  assert.deepEqual(pageOf(104, 10, 1), { page: 1, pages: 11, from: 1, to: 10 });
  assert.deepEqual(pageOf(104, 10, 2), { page: 2, pages: 11, from: 11, to: 20 });
  // The last page is shorter.
  assert.deepEqual(pageOf(104, 10, 11), { page: 11, pages: 11, from: 101, to: 104 });
  assert.equal(pageLine(pageOf(104, 10, 2), 104, "headline", "headlines"), "11–20 of 104 headlines");
});

test("Scenario: A list that fits one page", () => {
  assert.deepEqual(pageOf(4, 10, 1), { page: 1, pages: 1, from: 1, to: 4 });
  assert.equal(pageLine(pageOf(4, 10, 1), 4, "claim", "claims"), "4 claims");
  assert.equal(pageLine(pageOf(1, 10, 1), 1, "claim", "claims"), "1 claim");
  assert.deepEqual(pageOf(0, 10, 1), { page: 1, pages: 1, from: 0, to: 0 });
});

test("Scenario: A page that does not exist", () => {
  // An address naming a page past the end, before the start or not a number.
  assert.equal(pageOf(104, 10, 99).page, 11);
  assert.equal(pageOf(104, 10, 0).page, 1);
  assert.equal(pageOf(104, 10, Number("x")).page, 1);
  assert.equal(pageOf(104, 10, 2.5).page, 1);
});
