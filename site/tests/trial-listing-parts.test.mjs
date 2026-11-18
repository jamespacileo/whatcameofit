import assert from "node:assert/strict";
import { test } from "node:test";
import { NOT_AN_OPTION, setNote } from "../src/lib/trial-page.mjs";
import { partFor, splitListing } from "../src/lib/trial-listing-parts.mjs";

test("the listing's scope is described from the registry set's name", () => {
  assert.equal(setNote("active-since-2025", "2026-11-17"), `Phase 2 and 3 studies that ClinicalTrials.gov lists as not finished. ${NOT_AN_OPTION}`);
  assert.equal(setNote("active-or-ended-this-year", "2026-11-17"), `Studies that ClinicalTrials.gov lists as not finished, or as ended in 2026. ${NOT_AN_OPTION}`);
  assert.equal(setNote("constructor", null), `Studies registered on ClinicalTrials.gov. ${NOT_AN_OPTION}`);
});

test("listing parts preserve every trial and let a reader find the part by its identifier", () => {
  const rows = Array.from({ length: 500 }, (_, at) => [
    `NCT${90000000 - at * 7}`, `A synthetic study ${at}`, null, [], "under_way", null, [], [], null,
  ]);
  const parts = splitListing(rows, 2000);
  assert.ok(parts.length > 10);
  assert.deepEqual(parts.flatMap(({ trials }) => trials.map(([id]) => id)), rows.map(([id]) => id).sort());
  assert.equal(new Set(parts.map(({ name }) => name)).size, parts.length);
  for (const part of parts) {
    assert.ok(JSON.stringify(part.trials).length <= 2002);
    assert.deepEqual([part.first, part.last], [part.trials[0][0], part.trials.at(-1)[0]]);
    for (const [id] of part.trials) assert.equal(partFor({ parts }, id.toLowerCase()), part);
  }
  assert.equal(partFor({ parts }, "NCT00000001"), null);
  assert.deepEqual(splitListing([]), []);
  assert.equal(splitListing([["NCT00000001", "x".repeat(50)], ["NCT00000002", "y"]], 10).length, 2);
});
