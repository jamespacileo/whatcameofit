// The pills that pass a page on (lib/blocks.ts pageActions; scripts/page-actions.ts), drawn for
// every pair and listing of the fixture bundle: the sentence a reader copies says where things
// stand in the site's own words, is dated, and ends with the address the reader is at.
import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { parseHTML } from "linkedom";
import { readBundle } from "../src/lib/bundle.ts";
import { pairView } from "../src/lib/pair-view.ts";
import { renderPairBand } from "../src/lib/pair-render.ts";
import { interventionListing, topicListing } from "../src/lib/listing-view.ts";
import { listingSentence, renderListingBand } from "../src/lib/listing-render.ts";
import { CARD_NOTICE } from "../src/lib/card.ts";
import { STATUS_LABELS, assertNeutral } from "../src/lib/status.ts";

const { pages } = readBundle(fileURLToPath(new URL("./bundle", import.meta.url)));
const published = new Set(Object.keys(pages.PairPage));
const pairs = Object.values(pages.PairPage).map(pairView);
const listings = [
  ...Object.values(pages.PairTopicPage).map((file) => topicListing(file, published)),
  ...Object.values(pages.PairInterventionPage).map((file) => interventionListing(file, published)),
];
const actionsOf = (html) => parseHTML(`<main>${html}</main>`).document.querySelector(".band.record .band-main > [data-page-actions]");
const MONTH = /(January|February|March|April|May|June|July|August|September|October|November|December) \d{4}/;

test("a pair page's sentence names the pair, its status and the month, and gives no advice", () => {
  assert.ok(pairs.length > 0);
  for (const view of pairs) {
    const actions = actionsOf(renderPairBand(view));
    assert.ok(actions, `${view.address}: the pills are in the band, under the title`);
    // Hidden as sent: a pill shows only once the script finds it can work.
    assert.equal(actions.querySelector("[data-share]").hasAttribute("hidden"), true);
    assert.equal(actions.querySelector("[data-copy]").hasAttribute("hidden"), true);
    const sentence = actions.querySelector("[data-share-sentence]").textContent;
    assert.ok(sentence.startsWith(`${view.title.replace(/[.\s]+$/, "")}. Status when checked in `), view.address);
    assert.match(sentence, /checked in [A-Z][a-z]{2} \d{4}: /);
    assert.ok(sentence.endsWith(`: ${STATUS_LABELS[view.statusCode]}. ${CARD_NOTICE}.`), `${view.address}: ${sentence}`);
    assertNeutral([sentence]);
  }
});

test("a listing's sentence is its summary, dated; one pair's list has Share alone", () => {
  assert.ok(listings.some((view) => view.rows.length > 1) && listings.some((view) => view.rows.length === 1));
  for (const view of listings) {
    const actions = actionsOf(renderListingBand(view));
    assert.ok(actions.querySelector("[data-share]"), view.path);
    const sentence = actions.querySelector("[data-share-sentence]");
    assert.equal(sentence !== null, view.rows.length > 1, view.path);
    assert.equal(actions.querySelector("[data-copy]") !== null, view.rows.length > 1, view.path);
    if (!sentence) continue;
    assert.equal(sentence.textContent, listingSentence(view));
    assert.ok(sentence.textContent.startsWith(`${view.title}. `), view.path);
    assert.ok(sentence.textContent.includes(parseHTML(`<main>${renderListingBand(view)}</main>`).document.querySelector("[data-listing-summary]").textContent), `${view.path}: the sentence says what the band says`);
    assert.match(sentence.textContent, new RegExp(`Checked ${MONTH.source}\\.$`));
    assertNeutral([sentence.textContent]);
  }
});

test("the script shows the pills where the clipboard can be written, and copies the sentence with the address", async () => {
  const view = pairs[0];
  const { document } = parseHTML(`<html><body><main>${renderPairBand(view)}</main></body></html>`);
  // A browser with a clipboard and no share sheet, standing in for the page's own.
  const copied = [];
  const stand = { document, location: new URL(`https://example.test/${view.address}?page=2`), navigator: { clipboard: { writeText: async (text) => void copied.push(text) } } };
  for (const [name, value] of Object.entries(stand)) Object.defineProperty(globalThis, name, { value, configurable: true });
  await import("../src/scripts/page-actions.ts");
  const [share, copy] = [document.querySelector("[data-share]"), document.querySelector("[data-copy]")];
  assert.equal(share.hidden, false);
  assert.equal(copy.hidden, false);
  const press = async (button) => {
    button.dispatchEvent(new document.defaultView.Event("click"));
    await new Promise((done) => setImmediate(done));
  };
  await press(copy);
  await press(share);
  const address = `https://example.test/${view.address}`;
  assert.deepEqual(copied, [`${document.querySelector("[data-share-sentence]").textContent} ${address}`, address]);
  assert.equal(copy.querySelector("[data-copy-text]").textContent, "Copied");
  assert.equal(share.querySelector("[data-share-text]").textContent, "Link copied");
  assert.ok(copy.classList.contains("done"));
});
