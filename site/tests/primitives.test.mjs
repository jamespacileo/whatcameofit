// The claim page's one scale (openspec claim-primitives): every list, table and panel
// takes its row padding, row rule, label size, note size and panel padding from the
// same custom properties. This holds each family to it, so a new section cannot drift.
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";

const css = fs.readFileSync(new URL("../src/styles/global.css", import.meta.url), "utf8");

/** The first rule whose selector list is exactly `selector`, as its declarations. */
function rule(selector) {
  const start = css.indexOf(`\n${selector} {\n`);
  assert.notEqual(start, -1, `no rule for ${selector}`);
  return css.slice(start, css.indexOf("\n}", start));
}

const uses = (selector, property, token) =>
  assert.match(
    rule(selector),
    new RegExp(`\\n  ${property}: [^;]*var\\(--${token}\\)[^;]*;`),
    `${selector} takes ${property} from --${token}`,
  );

test("the scale is defined once", () => {
  for (const token of ["radius-s", "row-pad", "row-rule", "label-size", "note-size", "panel-pad", "label-col"]) {
    assert.equal(css.split(`\n  --${token}:`).length - 1, 1, `--${token} is defined once`);
  }
});

test("rows take their padding and their rule from the scale", () => {
  uses(".glance-rows > div", "padding", "row-pad");
  uses(".glance-rows > div", "border-bottom", "row-rule");
  uses(".record-row", "padding", "row-pad");
  uses(".record-row", "border-bottom", "row-rule");
  uses(".trial-row", "padding", "row-pad");
  uses(".timetable th,\n.timetable td,\n.index th,\n.index td", "padding", "row-pad");
  uses(".timetable th,\n.timetable td,\n.index th,\n.index td", "border-top", "row-rule");
  uses(".result-table th,\n.result-table td", "border-top", "row-rule");
});

test("labels and column heads are one size, notes another", () => {
  uses(".glance-rows dt,\n.glance-facts dt", "font-size", "label-size");
  uses(".record-fields dt", "font-size", "label-size");
  uses(".trial-facts dt", "font-size", "label-size");
  uses(".timetable thead th,\n.index thead th", "font-size", "label-size");
  uses(".trial-columns", "font-size", "label-size");
  uses(".entry-note", "font-size", "note-size");
  uses(".record .origin", "font-size", "note-size");
  uses(".glance-note", "font-size", "note-size");
  uses(".glance-more summary", "font-size", "note-size");
});

test("every table has the same quiet head", () => {
  uses(".timetable thead th,\n.index thead th", "background", "table-head");
  uses(".trial-columns", "background", "table-head");
});

test("panels share their padding and their corners", () => {
  for (const panel of [".trial-facts", ".brief-open", ".card-facts", ".term-card"]) {
    uses(panel, "padding", "panel-pad");
    uses(panel, "border-radius", "radius-s");
  }
  assert.doesNotMatch(css, /border-radius: 0\.65rem/, "the small corner is written as --radius-s");
});

test("label columns are one width", () => {
  uses(".glance-rows > div", "grid-template-columns", "label-col");
  uses(".brief-group", "grid-template-columns", "label-col");
});
