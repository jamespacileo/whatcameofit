// Status changes as a feed: in the site's own status wording, each entry dated to its change.
import assert from "node:assert/strict";
import { test } from "node:test";
import { changeSummary, changesFeed } from "../src/lib/changes.ts";

const change = (address, title, on, before, code) => ({ address, title, on, before, code });
const changes = [
  change("moved--condition", "Moved for a condition", "2023-02-01", "trial_registered", "phase_2"),
  change("moved--condition", "Moved for a condition", "2022-01-10", "preclinical_only", "trial_registered"),
  change("moved--condition", "Moved for a condition", "2019-05-03", null, "preclinical_only"),
];

test("a change names the status before", () => {
  assert.equal(changeSummary(changes[2]), "First status: Preclinical only.");
  assert.equal(changeSummary(changes[0]), "Was: Trial registered. Now: Phase 2 trial.");
});

const feed = (given) =>
  changesFeed({
    title: "What came of it? Status changes",
    self: "https://example.test/changes.xml",
    page: "https://example.test/",
    site: "https://example.test",
    changes: given,
    generatedAt: "2026-11-11T09:00:00Z",
  });

test("each entry is dated to its change and links to its pair's page", () => {
  const xml = feed(changes);
  assert.match(xml, /^<\?xml version="1.0" encoding="utf-8"\?>\n<feed xmlns="http:\/\/www.w3.org\/2005\/Atom">/);
  assert.equal(xml.split("<entry>").length, 4);
  assert.match(xml, /<updated>2023-02-01T00:00:00Z<\/updated>\n  <entry>/);
  assert.match(xml, /<summary>Was: Trial registered\. Now: Phase 2 trial\.<\/summary>/);
  assert.match(xml, /<link href="https:\/\/example\.test\/moved--condition"\/>/);
  const ids = [...xml.matchAll(/<id>([^<]+)<\/id>/g)].map((found) => found[1]);
  assert.equal(new Set(ids).size, ids.length);
});

test("a feed with no changes is still a feed, dated to the bundle", () => {
  const xml = feed([]);
  assert.equal(xml.split("<entry>").length, 1);
  assert.match(xml, /<updated>2026-11-11T00:00:00Z<\/updated>/);
});

test("a title's own characters are escaped", () => {
  const xml = feed([change("amp", "Drug A & B <beats> placebo", "2024-01-01", null, "phase_1")]);
  assert.match(xml, /<title>Drug A &amp; B &lt;beats&gt; placebo<\/title>/);
});
