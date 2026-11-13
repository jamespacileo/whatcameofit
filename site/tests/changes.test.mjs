// Status changes as feeds: built from the history the pipeline exports, in the site's
// own status wording, each entry dated to its change.
import assert from "node:assert/strict";
import { test } from "node:test";
import { allChanges, changeSummary, changesFeed, changesOf } from "../src/lib/changes.ts";

const claim = (slug, headline, history) => ({ slug, headline, status: { code: history?.at(-1)?.code, history } });
const moved = claim("moved", "Moved claim", [
  { on: "2019-05-03", code: "preclinical_only" },
  { on: "2022-01-10", code: "trial_registered" },
  { on: "2023-02-01", code: "phase_2" },
]);
const still = claim("still", "A still claim", [{ on: "2022-01-10", code: "preclinical_only" }]);
const older = claim("older", "Older export's claim", undefined);

test("a claim's changes name the status before, oldest first", () => {
  const changes = changesOf(moved);
  assert.deepEqual(changes.map((change) => [change.on, change.before, change.code]), [
    ["2019-05-03", null, "preclinical_only"],
    ["2022-01-10", "preclinical_only", "trial_registered"],
    ["2023-02-01", "trial_registered", "phase_2"],
  ]);
  assert.equal(changeSummary(changes[0]), "First status: Preclinical only.");
  assert.equal(changeSummary(changes[2]), "Was: Trial registered. Now: Phase 2 trial.");
});

test("an export without a history gives no changes", () => {
  assert.deepEqual(changesOf(older), []);
});

test("all claims' changes run newest first, and by headline on one day", () => {
  const order = allChanges([moved, still, older]).map((change) => `${change.on} ${change.claim.slug}`);
  assert.deepEqual(order, ["2023-02-01 moved", "2022-01-10 still", "2022-01-10 moved", "2019-05-03 moved"]);
});

const feed = (changes) =>
  changesFeed({
    title: "What came of it? Status changes",
    self: "https://example.test/changes.xml",
    page: "https://example.test/",
    site: "https://example.test",
    changes,
    generatedAt: "2026-11-11T09:00:00Z",
  });

test("each entry is dated to its change and links to its claim page", () => {
  const xml = feed(allChanges([moved]));
  assert.match(xml, /^<\?xml version="1.0" encoding="utf-8"\?>\n<feed xmlns="http:\/\/www.w3.org\/2005\/Atom">/);
  assert.equal(xml.split("<entry>").length, 4);
  assert.match(xml, /<updated>2023-02-01T00:00:00Z<\/updated>\n  <entry>/);
  assert.match(xml, /<summary>Was: Trial registered\. Now: Phase 2 trial\.<\/summary>/);
  assert.match(xml, /<link href="https:\/\/example\.test\/moved"\/>/);
  const ids = [...xml.matchAll(/<id>([^<]+)<\/id>/g)].map((found) => found[1]);
  assert.equal(new Set(ids).size, ids.length);
});

test("a feed with no changes is still a feed, dated to the export", () => {
  const xml = feed([]);
  assert.equal(xml.split("<entry>").length, 1);
  assert.match(xml, /<updated>2026-11-11T00:00:00Z<\/updated>/);
});

test("a headline's own characters are escaped", () => {
  const xml = feed(changesOf(claim("amp", "Drug A & B <beats> placebo", [{ on: "2024-01-01", code: "phase_1" }])));
  assert.match(xml, /<title>Drug A &amp; B &lt;beats&gt; placebo<\/title>/);
});
