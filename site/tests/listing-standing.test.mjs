// Where a listing's pairs stand (lib/blocks.ts stageFilter, statusCell and pairTable;
// lib/status.ts standingSummary), drawn for every listing of the fixture bundle: the summary
// sentence, the counts along the path and the track in each row say the same thing as the rows,
// and the filter script narrows the table it stands before.
import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { parseHTML } from "linkedom";
import { readBundle } from "../src/lib/bundle.ts";
import { interventionListing, topicListing } from "../src/lib/listing-view.ts";
import { renderListingBand, renderListingSheet } from "../src/lib/listing-render.ts";
import { STAGE_FILTER_FROM } from "../src/lib/blocks.ts";
import { STAGE_PATH, STATUS_LABELS, assertNeutral, standingSummary } from "../src/lib/status.ts";

const { pages } = readBundle(fileURLToPath(new URL("./bundle", import.meta.url)));
const published = new Set(Object.keys(pages.PairPage));
const listings = [
  ...Object.values(pages.PairTopicPage).map((file) => topicListing(file, published)),
  ...Object.values(pages.PairInterventionPage).map((file) => interventionListing(file, published)),
];
const pageOf = (view) => parseHTML(`<main>${renderListingBand(view)}${renderListingSheet(view, "")}</main>`).document;

test("the counts along the path add up to the rows, and each row carries its place", () => {
  const listed = listings.filter((view) => view.rows.length >= STAGE_FILTER_FROM);
  assert.ok(listed.length > 0, "the fixture has a listing long enough to have a filter");
  for (const view of listings.filter((one) => one.rows.length < STAGE_FILTER_FROM)) {
    assert.equal(pageOf(view).querySelector(".stage-filter"), null, `${view.path}: a short list has no filter`);
  }
  for (const view of listed) {
    const document = pageOf(view);
    const places = [...document.querySelectorAll(".stage-filter button[data-status]")];
    assert.deepEqual(places.slice(0, STAGE_PATH.length).map((place) => place.dataset.status), STAGE_PATH, `${view.path}: the path's places, in order`);
    const counted = places.reduce((sum, place) => sum + Number(place.querySelector("strong").textContent), 0);
    assert.equal(counted, view.rows.length, `${view.path}: every pair is counted at one place`);
    for (const place of places) {
      const at = view.rows.filter((row) => row.statusCode === place.dataset.status).length;
      assert.equal(Number(place.querySelector("strong").textContent), at, `${view.path}: ${place.dataset.status}`);
      assert.equal(place.hasAttribute("disabled"), at === 0, `${view.path}: a place with no pair cannot be pressed`);
    }
    for (const row of document.querySelectorAll("tr[data-pair]")) {
      const code = row.dataset.status;
      assert.equal(row.querySelector(".status-name").textContent, STATUS_LABELS[code]);
      assert.ok(row.querySelector(STAGE_PATH.includes(code) ? ".track .step.here" : ".track.off"), `${row.dataset.pair}: its place on the path, or the mark for off it`);
    }
  }
});

test("a list is summed up in one sentence, and one pair is not", () => {
  for (const view of listings) {
    const summary = pageOf(view).querySelector("[data-listing-summary]");
    assert.equal(summary !== null, view.rows.length > 1, view.path);
    if (summary) assertNeutral([summary.textContent]);
  }
  assert.equal(standingSummary(new Map()), null);
  assert.equal(standingSummary(new Map([["phase_2", 1]])), "1 treatment and condition followed: it has reached a mid-stage trial in people.");
  assert.equal(standingSummary(new Map([["phase_3", 5]])), "All 5 treatments and conditions followed have reached large late-stage trials in people.");
  // The four statuses with the most pairs are named in path order; the rest are counted together.
  assert.equal(
    standingSummary(new Map([["phase_3", 12], ["preclinical_only", 21], ["phase_2", 10], ["no_trial_found", 10], ["phase_1", 3], ["trial_registered", 5]])),
    "Of 61 treatments and conditions followed, 21 have no trial in people on record, 10 have reached mid-stage trials in people, 12 have reached large late-stage trials in people, 10 have no matching registered trial found and 8 are at other statuses.",
  );
});

test("what every row shares is said once above the table, not in each row", () => {
  const view = listings.find((one) => one.rows.length > 1);
  const document = pageOf(view);
  assert.match(document.querySelector("[data-pair-table-note]").textContent, /^Statuses as of \d+\s\w+\s\d{4}\. Put together by software, not yet checked by a person\.$/);
  assert.equal([...document.querySelectorAll("tr[data-pair]")].filter((row) => /checked|As of/.test(row.textContent)).length, 0);
  // Rows that differ each say their own.
  const mixed = { ...view, rows: view.rows.map((row, index) => ({ ...row, asOf: index === 0 ? "2026-01-02" : row.asOf, checkedByPerson: index === 0 })) };
  const rows = [...pageOf(mixed).querySelectorAll("tr[data-pair]")];
  assert.equal(pageOf(mixed).querySelector("[data-pair-table-note]"), null);
  assert.match(rows[0].textContent, /As of 2\sJan\s2026/);
  assert.doesNotMatch(rows[0].textContent, /not yet checked/);
  assert.match(rows[1].textContent, /not yet checked by a person/);
});

test("the filter script shows only the pairs at the picked place, and all of them again", async () => {
  // The listing with the most statuses, so that a pick leaves some rows out.
  const view = listings.filter((one) => one.rows.length >= STAGE_FILTER_FROM).sort((a, b) => new Set(b.rows.map((row) => row.statusCode)).size - new Set(a.rows.map((row) => row.statusCode)).size)[0];
  const statuses = [...new Set(view.rows.map((row) => row.statusCode))];
  assert.ok(statuses.length > 1, "the fixture has a listing with pairs at more than one status");
  const { document } = parseHTML(`<html><body><main>${renderListingSheet(view, "")}</main></body></html>`);
  Object.assign(globalThis, { document, location: new URL("https://example.test/topic/x"), history: { state: null, replaceState() {} } });
  await import("../src/scripts/pair-filter.ts");
  const rows = [...document.querySelectorAll("tr[data-pair]")];
  const shown = () => rows.filter((row) => !row.hidden).map((row) => row.dataset.status);
  const place = document.querySelector(`.stage-filter button[data-status="${statuses[0]}"]`);
  place.dispatchEvent(new document.defaultView.Event("click"));
  assert.equal(place.getAttribute("aria-pressed"), "true");
  assert.deepEqual([...new Set(shown())], [statuses[0]]);
  assert.equal(document.querySelector("[data-shown-text]").textContent, `Showing ${shown().length} of ${rows.length}.`);
  place.dispatchEvent(new document.defaultView.Event("click"));
  assert.equal(shown().length, rows.length, "picking the place again shows every pair");
  // A word no row holds: the table gives way to a line that says so.
  const input = document.querySelector("[data-words]");
  input.value = "zzzz";
  input.dispatchEvent(new document.defaultView.Event("input"));
  assert.equal(shown().length, 0);
  assert.equal(document.querySelector("[data-none]").hidden, false);
  assert.match(document.querySelector("[data-none-what]").textContent, /zzzz/);
});
