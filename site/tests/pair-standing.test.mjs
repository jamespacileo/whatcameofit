// A pair page's "Where it stands" card, section list and record strip (lib/pair-render.ts;
// lib/blocks.ts standingCard and sectionList; lib/record-strip.ts), drawn for every pair of the
// fixture bundle: the card says the status once, each section the list names is on the page,
// and the strip is drawn only when the page has a day its registries were last checked.
import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { parseHTML } from "linkedom";
import { readBundle } from "../src/lib/bundle.ts";
import { pairView } from "../src/lib/pair-view.ts";
import { renderPairBand, renderPairSheet } from "../src/lib/pair-render.ts";
import { STAGE_PATH, STATUS_GLOSSES, STATUS_LABELS } from "../src/lib/status.ts";

const { pages } = readBundle(fileURLToPath(new URL("./bundle", import.meta.url)));
const views = Object.values(pages.PairPage).map(pairView);
const pageOf = (view) => parseHTML(`<main>${renderPairBand(view)}${renderPairSheet(view)}</main>`).document;

test("the card says where the pair stands once: its label, its gloss and its place on the path", () => {
  assert.ok(views.length > 0);
  for (const view of views) {
    const document = pageOf(view);
    const card = document.querySelector(".band.record > .band-grid > .digest[data-standing-card]");
    assert.ok(card, `${view.address}: the card sits in the band, beside the title`);
    assert.equal(card.querySelector("h2.card-tab").textContent, "Where it stands");
    const marked = document.querySelectorAll("[data-pair-status]");
    assert.equal(marked.length, 1, `${view.address}: the status is said in one place`);
    assert.equal(marked[0].dataset.pairStatus, view.statusCode);
    assert.equal(marked[0].textContent, STATUS_LABELS[view.statusCode]);
    assert.equal(card.querySelector(".gloss").textContent, STATUS_GLOSSES[view.statusCode]);
    if (STAGE_PATH.includes(view.statusCode)) {
      const steps = [...card.querySelectorAll(".track .step")];
      assert.equal(steps.findIndex((step) => step.classList.contains("here")), STAGE_PATH.indexOf(view.statusCode), view.address);
    } else assert.ok(card.querySelector(".track.off"), `${view.address}: off the path, the square alone`);
    // The day the status was worked out is worded as that, never as a record's day.
    assert.match(card.textContent, /Status set by rule, \d+\s\w+\s\d{4}\./);
    const dated = view.trials.flatMap((trial) => trial.events).filter((event) => !event.estimated);
    assert.equal(/Latest record/.test(card.textContent), dated.length > 0, `${view.address}: a latest record only when the registry records one`);
    const posted = view.trials.filter((trial) => trial.resultsPosted).length;
    assert.equal(card.textContent.includes(`${posted} with results posted`), posted > 0, view.address);
  }
});

test("each section the list names is a section of the page", () => {
  for (const view of views) {
    const document = pageOf(view);
    const links = [...document.querySelectorAll(".frame > nav.onpage a")];
    assert.ok(links.length >= 3, view.address);
    for (const link of links) assert.ok(document.getElementById(link.getAttribute("href").slice(1)), `${view.address}: ${link.getAttribute("href")}`);
    assert.equal(document.querySelector('nav.onpage a[href="#trials"] .n').textContent, String(view.trials.length));
    assert.equal(document.querySelector(".frame.no-rail"), null);
  }
});

test("the record strip is drawn only with a day the registries were last checked", () => {
  const view = views.find((one) => one.trials.some((trial) => trial.events.some((event) => !event.estimated)));
  assert.equal(pageOf({ ...view, registryChecks: [] }).querySelector("[data-pair-strip]"), null);
  const checked = pageOf({ ...view, registryChecks: [{ registry: "ClinicalTrials.gov", through: "2026-11-17" }] });
  const strip = checked.querySelector("#trials ~ [data-pair-strip]");
  assert.ok(strip, "under The trials");
  assert.match(strip.querySelector("svg[role=img]").getAttribute("aria-label"), /dated trial events?.* to the last check on 17\sNov\s2026\.$/);
  assert.ok(strip.querySelector(".strip-key"), "with its key");
});
