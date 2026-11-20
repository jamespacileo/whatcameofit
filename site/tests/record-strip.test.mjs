// The record strip (lib/record-strip.ts) and the stage track and basis mark (lib/blocks.ts),
// from the fixture's real pair pages: a mark for each dated registry record up to the last
// check, results above the axis, the key naming only what is drawn, and no status coloured.
import assert from "node:assert/strict";
import { test } from "node:test";
import { parseHTML } from "linkedom";
import { readBundle } from "../src/lib/bundle.ts";
import { pairView } from "../src/lib/pair-view.ts";
import { STRIP_KEY, recordStrip, stripKey, stripOf } from "../src/lib/record-strip.ts";
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
    assert.match(svg.getAttribute("aria-label"), /dated registry records?, .*from \d{4} to the last check on/);
    assert.equal(document.querySelectorAll(".strip-record").length, strip.counts.record, view.address);
    assert.equal(document.querySelectorAll(".strip-results").length, strip.counts.results, view.address);
  }
  assert.ok(drawn > 0, "the fixture draws at least one strip");
});

test("the key names each mark it draws, once, and only the marks a pair can have", () => {
  const document = parseHTML(`<main>${stripKey()}</main>`).document;
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
  assert.match(basisMark(), /basis of status/);
  assert.doesNotMatch(basisMark(false), /basis of status/);
});
