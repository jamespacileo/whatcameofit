import assert from "node:assert/strict";
import { test } from "node:test";
import { CARD_NOTICE, cardAlt, cardContent, clip, shareSentence } from "../src/lib/card.ts";
import { assertNeutral } from "../src/lib/status.ts";

const claim = (articles) => ({
  headline: "The site's own headline",
  first_reported_date: "2021-03-31",
  articles,
});
const article = (published_date, title, outlet) => ({ published_date, title, outlet });

test("Card facts: claim with two articles picks the earliest", () => {
  const card = cardContent(
    claim([
      article("2022-05-01", "Later report", "Second Outlet"),
      article("2021-03-31", "Scientists regrow teeth", "First Outlet"),
    ]),
    "Phase 1 trial",
    null,
    "2030-12-31",
    "2026-11-11T09:00:00Z",
  );
  assert.equal(card.quote, "Scientists regrow teeth");
  assert.equal(card.outlet, "First Outlet");
  assert.deepEqual(
    card.facts.map(({ label, value }) => `${label} ${value}`),
    ["First reported 2021", "Promised by 2030", "Status now Phase 1 trial", "Checked Nov 2026"],
  );
});

test("Card facts: claim with no article", () => {
  const card = cardContent(claim([]), "Preclinical only", "No signal for 6 years", null, null);
  assert.equal(card.quote, null);
  assert.equal(card.outlet, null);
  // With nothing to quote, the alternative leads with the claim's headline, unquoted.
  assert.match(cardAlt(card), /^The site's own headline\. /);
  assert.doesNotMatch(cardAlt(card), /“/);
});

test("the text alternative states the same facts, dated and never counted in days", () => {
  const card = cardContent(
    claim([article("2021-03-31", "Scientists regrow teeth", "First Outlet")]),
    "Phase 1 trial",
    null,
    null,
    "2026-11-11T09:00:00Z",
  );
  assert.equal(
    cardAlt(card),
    "“Scientists regrow teeth” (First Outlet). First reported 2021. Status now Phase 1 trial. Checked Nov 2026. Not medical advice.",
  );
  assert.doesNotMatch(cardAlt(card), /\b(days?|years? (later|on|ago))\b/);
});

test("a long title ends at a word with an ellipsis", () => {
  const long = "word ".repeat(60).trim();
  const cut = clip(long, 150);
  assert.ok(cut.length <= 151);
  assert.match(cut, /word…$/);
  assert.equal(clip("short", 150), "short");
});

test("the card's own words are held to the verdict rule", () => {
  // The card module checks its fixed strings when it loads; this is the check it runs.
  assert.doesNotThrow(() => assertNeutral([CARD_NOTICE, "First reported", "Status now"]));
  assert.throws(() => assertNeutral(["Status now", "Debunked"]), /Verdict wording/);
});

test("the sentence to copy is dated and carries the page's address", () => {
  const sentence = shareSentence(
    { headline: "Antibody regrows teeth in mice.", first_reported_date: "2021-03-31" },
    "Phase 1 trial",
    "2026-11-11T09:00:00Z",
    "https://example.org/tooth",
  );
  assert.equal(
    sentence,
    "Antibody regrows teeth in mice. First reported Mar 2021. Status when checked in Nov 2026: Phase 1 trial. Not medical advice. https://example.org/tooth",
  );
});
