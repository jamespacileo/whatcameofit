// A topic's card: what it says, the drawing it carries, and the image built from it.
import assert from "node:assert/strict";
import fs from "node:fs";
import { registerHooks } from "node:module";
import path from "node:path";
import { test } from "node:test";
import { topicCardAlt, topicCardContent } from "../src/lib/card.ts";
import { topicSummary } from "../src/lib/status.ts";
import { DRAWN, LIBRARY_ICONS, topicDrawing } from "../src/lib/topic-drawing.ts";

// The image module imports its neighbours without an extension, as the site's
// bundler allows; here a missing extension is read as ".ts".
registerHooks({
  resolve(specifier, context, next) {
    try {
      return next(specifier, context);
    } catch (error) {
      if (specifier.startsWith(".") && !path.extname(specifier)) return next(`${specifier}.ts`, context);
      throw error;
    }
  },
});
process.env.EXPORT_FILE = "tests/fixture-export.json";
const { topicCardFor, topicPng } = await import("../src/lib/card-image.ts");
const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));

const tally = (spec) => new Map(Object.entries(spec));
const CHECKED = "2026-11-11T09:00:00Z";

test("a topic with one published claim says one is tracked and where it stands", () => {
  const card = topicCardContent(
    "Gut and liver",
    topicSummary(tally({ preclinical_only: 1 })),
    CHECKED,
  );
  assert.deepEqual(card, {
    title: "Gut and liver",
    summary: "1 reported breakthrough tracked: it has no trial in people on record.",
    checked: "Nov 2026",
  });
  assert.equal(
    topicCardAlt(card),
    "Gut and liver. 1 reported breakthrough tracked: it has no trial in people on record. Checked Nov 2026. Not medical advice.",
  );
});

test("a topic with seven claims shows its name, a count by status and the month checked", () => {
  const summary = topicSummary(tally({ preclinical_only: 3, phase_2: 2, approved: 1, failed: 1 }));
  const card = topicCardContent("Cancer", summary, CHECKED);
  assert.equal(
    topicCardAlt(card),
    "Cancer. Of 7 reported breakthroughs tracked, 3 have no trial in people on record, 2 have reached mid-stage trials in people, 1 has been approved by a regulator and 1 had a trial that did not meet its main goal. Checked Nov 2026. Not medical advice.",
  );
});

test("before any check the card carries no date", () => {
  const card = topicCardContent("Cancer", topicSummary(tally({ phase_1: 2 })), null);
  assert.equal(card.checked, null);
  assert.doesNotMatch(topicCardAlt(card), /Checked/);
  assert.match(topicCardAlt(card), /Not medical advice\.$/);
});

test("the alternative names no claim's headline and no outlet's title", () => {
  const topic = fixture.verticals.find((entry) => entry.slug === "gum-disease");
  const claims = fixture.claims.filter((claim) => claim.vertical === topic.slug);
  const alt = topicCardAlt(topicCardFor(topic, claims));
  assert.match(alt, /^Gum disease\. Of 3 reported breakthroughs tracked, /);
  assert.match(alt, /Checked Nov 2026\. Not medical advice\.$/);
  for (const claim of claims) {
    assert.ok(!alt.includes(claim.headline), claim.headline);
    for (const article of claim.articles) assert.ok(!alt.includes(article.title), article.title);
  }
});

test("a topic takes its group's drawing, else its own, else the plain ring", () => {
  const gum = { slug: "gum-disease", group: { slug: "mouth-and-teeth" } };
  assert.deepEqual(topicDrawing(gum), { paths: DRAWN["mouth-and-teeth"] });
  assert.deepEqual(topicDrawing({ slug: "cancer" }), { icon: "ribbon" });
  assert.equal(topicDrawing({ slug: "empty-topic" }), null);
});

test("the card draws the same topics with the same drawings as the chip", () => {
  const chip = fs.readFileSync("src/components/TopicChip.astro", "utf8");
  const imported = Object.fromEntries(
    [...chip.matchAll(/import (\w+) from "@lucide\/astro\/icons\/([\w-]+)";/g)].map(([, name, icon]) => [
      name,
      icon,
    ]),
  );
  const library = chip.match(/const LIBRARY = \{([\s\S]*?)\} as const;/)[1];
  const chipIcons = Object.fromEntries(
    [...library.matchAll(/"?([\w-]+)"?: (\w+),/g)].map(([, slug, name]) => [slug, imported[name]]),
  );
  assert.deepEqual(chipIcons, LIBRARY_ICONS);
  const drawn = chip.match(/const DRAWN[^=]*= \{([\s\S]*?)\n\};/)[1];
  const chipDrawn = Object.fromEntries(
    [...drawn.matchAll(/"([\w-]+)": \[([\s\S]*?)\],/g)].map(([, slug, lines]) => [
      slug,
      [...lines.matchAll(/"(M[^"]+)"/g)].map(([, d]) => d),
    ]),
  );
  assert.deepEqual(chipDrawn, DRAWN);
});

// A PNG states its width and height in its first chunk.
const size = (png) => {
  const buffer = Buffer.from(png);
  return [buffer.readUInt32BE(16), buffer.readUInt32BE(20)];
};

test("the card renders at 1200 by 630 with every drawing and with the ring", async () => {
  const claims = fixture.claims;
  const slugs = [...Object.keys(LIBRARY_ICONS), ...Object.keys(DRAWN), "empty-topic"];
  for (const slug of slugs) {
    const png = await topicPng({ slug, title: "Bones, joints and muscles" }, claims);
    assert.deepEqual(size(png), [1200, 630], slug);
  }
});
