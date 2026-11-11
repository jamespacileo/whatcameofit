// The status card: what it says, and the three images built from it.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";
import { CARD_NOTICE, cardAlt, cardContent, clip } from "../src/lib/card.ts";
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

// Built images: three shapes for every published claim, each at its stated size.
const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-cards-"));
const SIZES = { "og": [1200, 630], "og/square": [1080, 1080], "og/tall": [1080, 1920] };

before(() => {
  const result = spawnSync("npx", ["astro", "build", "--outDir", dist], {
    env: { ...process.env, EXPORT_FILE: "tests/fixture-export.json", ASTRO_TELEMETRY_DISABLED: "1" },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

test("every published claim has the card in three shapes", () => {
  const slugs = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8")).claims.map(
    (entry) => entry.slug,
  );
  for (const [folder, [width, height]] of Object.entries(SIZES)) {
    for (const slug of slugs) {
      const png = fs.readFileSync(path.join(dist, folder, `${slug}.png`));
      // A PNG states its width and height in its first chunk.
      assert.deepEqual([png.readUInt32BE(16), png.readUInt32BE(20)], [width, height], `${folder}/${slug}`);
    }
  }
});

test("the link preview's alternative quotes the outlet and says it is not advice", () => {
  const html = fs.readFileSync(path.join(dist, "phase-claim/index.html"), "utf8");
  const alt = html.match(/property="og:image:alt" content="([^"]+)"/)?.[1] ?? "";
  assert.match(alt, /“Example report 3” \(Example Outlet 3\)/);
  assert.match(alt, /Status now Phase 2 trial/);
  assert.match(alt, /Not medical advice\.$/);
});

// What a reader takes away from a claim page.
const { shareSentence } = await import("../src/lib/card.ts");

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

test("a claim page offers the sentence and both images", () => {
  const html = fs.readFileSync(path.join(dist, "phase-claim/index.html"), "utf8");
  assert.match(html, /id="sentence">[^<]*First reported May 2019\.[^<]*Phase 2 trial\.[^<]*\/phase-claim</);
  for (const shape of ["square", "tall"]) {
    assert.ok(html.includes(`href="/og/${shape}/phase-claim.png"`), `${shape} link`);
    assert.ok(fs.existsSync(path.join(dist, `og/${shape}/phase-claim.png`)));
  }
  // The snippet is the frame tag and nothing else.
  assert.ok(/&lt;iframe src=(&quot;|&#34;|")[^&"]*\/embed\/phase-claim/.test(html), "embed snippet");
});

test("Embed shows status and links out", () => {
  const html = fs.readFileSync(path.join(dist, "embed/quiet-claim/index.html"), "utf8");
  assert.match(html, /Preclinical only/);
  assert.match(html, /No signal for 6 years/);
  assert.match(html, /Not medical advice/);
  // Its links leave the frame, and search engines are asked to pass it by.
  assert.match(html, /<a href="[^"]*\/quiet-claim" target="_top"/);
  assert.doesNotMatch(html, /<a (?![^>]*target="_top")[^>]*href=/);
  assert.match(html, /<meta name="robots" content="noindex"/);
});

test("Embed asks no other host", () => {
  const html = fs.readFileSync(path.join(dist, "embed/quiet-claim/index.html"), "utf8");
  assert.doesNotMatch(html, /<(script|link|img)[^>]+(src|href)="https?:\/\//);
  assert.doesNotMatch(html, /document\.cookie|localStorage|sessionStorage/);
});
