// The record strip (lib/record-strip.ts) and the stage track and basis mark (lib/blocks.ts),
// from the fixture's real pair pages: a mark for each dated registry record up to the last
// check, results above the axis, the key naming only what is drawn, and no status coloured.
import assert from "node:assert/strict";
import { test } from "node:test";
import { parseHTML } from "linkedom";
import { readBundle } from "../src/lib/bundle.ts";
import { pairView } from "../src/lib/pair-view.ts";
import { STRIP_KEY, recordStrip, stripKey, stripKinds, stripOf } from "../src/lib/record-strip.ts";
import { assertNeutral } from "../src/lib/status.ts";
import { basisMark, stageTrack } from "../src/lib/blocks.ts";
import { STAGE_PATH } from "../src/lib/status.ts";

const views = Object.values(readBundle("tests/bundle").pages.PairPage).map(pairView);

test("a pair's strip marks each recorded date up to the last check, results apart, on one axis", () => {
  let drawn = 0;
  for (const view of views) {
    const strip = stripOf(view);
    const recorded = view.trials.flatMap((trial) => trial.events).filter((event) => !event.estimated && event.day <= strip?.lastChecked);
    if (!strip) {
      assert.equal(recordStrip(view), "", view.address);
      continue;
    }
    drawn += 1;
    assert.equal(strip.marks.length, recorded.length, view.address);
    assert.equal(strip.counts.results, recorded.filter((event) => event.kind === "results_posted").length, view.address);
    for (const mark of strip.marks) assert.ok(mark.at >= 0 && mark.at <= 1, view.address);
    const document = parseHTML(`<main>${recordStrip(view)}</main>`).document;
    const svg = document.querySelector("svg.strip-line");
    assert.equal(svg.getAttribute("role"), "img");
    assert.match(svg.getAttribute("aria-label"), /^\d+ dated trial events?(, \d+ of them results posted)?, from \d{4} to the last check on /);
    assertNeutral([svg.getAttribute("aria-label")]);
    // The key names only what this strip draws.
    const key = parseHTML(`<main>${stripKey(stripKinds(strip))}</main>`).document;
    assert.equal(key.querySelectorAll("li").length, (strip.counts.record > 0) + (strip.counts.results > 0) + 1, view.address);
    // Notches every year on a span of fifteen years or fewer.
    const span = Number(strip.lastChecked.slice(0, 4)) - strip.startYear;
    if (span <= 15) assert.equal(strip.notches.length, Number(strip.lastChecked.slice(0, 4)) - strip.startYear, view.address);
    assert.equal(document.querySelectorAll(".strip-record").length, strip.counts.record, view.address);
    assert.equal(document.querySelectorAll(".strip-results").length, strip.counts.results, view.address);
  }
  assert.ok(drawn > 0, "the fixture draws at least one strip");
});

test("a pair whose registries have no day of last check has no strip", () => {
  const view = views.find((one) => one.registryChecks.length === 0);
  assert.ok(view, "the fixture has a pair with no check");
  assert.equal(stripOf(view), null);
  assert.equal(recordStrip(view), "");
});

test("the key names each mark it draws, once, and only the marks a pair can have", () => {
  const document = parseHTML(`<main>${stripKey(["record", "results", "check"])}</main>`).document;
  assert.deepEqual([...document.querySelectorAll("li")].map((item) => item.textContent), Object.values(STRIP_KEY));
  for (const words of Object.values(STRIP_KEY)) assert.doesNotMatch(words, /promise|decision|approv|news/i);
});

test("the stage track marks one place by shape, never colour, and says it in words", () => {
  for (const [index, code] of STAGE_PATH.entries()) {
    const document = parseHTML(`<main>${stageTrack(code, { ends: true })}</main>`).document;
    assert.equal(document.querySelectorAll(".step").length, STAGE_PATH.length);
    assert.equal(document.querySelectorAll(".step.here").length, 1);
    assert.equal([...document.querySelectorAll(".step")].findIndex((step) => step.classList.contains("here")), index);
    assert.match(document.querySelector(".ends").textContent, new RegExp(`Place ${index + 1} of ${STAGE_PATH.length}`));
    assert.equal(document.querySelectorAll("[style]").length, 0);
  }
  assert.match(stageTrack("not_a_place", { off: true }), /Not a place on the path/);
  assert.equal(stageTrack("not_a_place"), "");
  // A named track has no square for a status off the path, as StageTrack drew it.
  assert.equal(stageTrack("not_a_place", { named: true, off: true }), "");
  assert.match(basisMark(), /basis of status/);
  assert.doesNotMatch(basisMark(false), /basis of status/);
});
