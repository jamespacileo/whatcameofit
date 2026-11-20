import assert from "node:assert/strict";
import { test } from "node:test";
import { yearStrip } from "../src/lib/about.ts";
import { pickPairs } from "../src/lib/audiences.ts";
import { assertNoAdvice, guideProblems, readEntry, shelfEntries, statusSlug } from "../src/lib/guide.ts";
import { topicSentence } from "../src/lib/share.ts";
import { STAGE_PATH, STATUS_LABELS, STATUS_MEANINGS } from "../src/lib/status.ts";

const codes = Object.keys(STATUS_LABELS);

const TEXT = `## In the records\n\n${"A registry holds a record of the trial. ".repeat(12)}\n\n## What it does not tell you\n\n${"It does not say what the trial found. ".repeat(12)}`;

/** An entry that passes every check; a test changes one thing about it. */
const entry = (slug, front = {}, text = TEXT) =>
  readEntry(
    slug,
    {
      shelf: "site",
      title: "Record",
      answer: "A record is a dated fact held by a public source.",
      rule: "where-the-data-comes-from",
      on_site: "Every record links to its source.",
      ...front,
    },
    text,
  );
const statusEntries = () => codes.map((code) => entry(statusSlug(code), { shelf: "status", status: code }));
const problemsWith = (...extra) => guideProblems([...statusEntries(), ...extra]);

test("a complete set of entries passes, and a status without an entry is named", () => {
  assert.deepEqual(problemsWith(entry("record")), []);
  const missing = guideProblems(statusEntries().filter((held) => held.status !== "retracted"));
  assert.equal(missing.length, 1);
  assert.match(missing[0], /Origin paper retracted.*has no guide entry/);
});

test("an entry on how research is recorded needs a source with the day it was checked", () => {
  const source = { name: "A registry", url: "https://example.org/a", checked: "2026-11-14" };
  assert.deepEqual(problemsWith(entry("trial-registry", { shelf: "research", sources: [source] })), []);
  assert.match(problemsWith(entry("trial-registry", { shelf: "research" })).join("\n"), /lists at least one source/);
  const undated = entry("trial-registry", { shelf: "research", sources: [{ ...source, checked: "" }] });
  assert.match(problemsWith(undated).join("\n"), /no day it was checked/);
});

test("a related entry must exist", () => {
  assert.deepEqual(problemsWith(entry("record", { related: ["approved"] })), []);
  assert.match(problemsWith(entry("record", { related: ["nowhere"] })).join("\n"), /"nowhere" does not exist/);
});

test("verdict wording and advice wording are each refused, with the entry named", () => {
  const verdict = entry("record", {}, TEXT.replace("It does not say", "The work was abandoned. It does not say"));
  assert.match(problemsWith(verdict).join("\n"), /Guide entry "record".*Verdict wording "abandoned"/);
  const advice = entry("record", {}, TEXT.replace("It does not say", "You should ask for it. It does not say"));
  assert.match(problemsWith(advice).join("\n"), /Guide entry "record".*Advice wording "You should"/);
  assert.doesNotThrow(() => assertNoAdvice(["This site gives no medical advice."]));
  assert.throws(() => assertNoAdvice(["It is worth joining a trial."]), /Advice wording/);
});

test("an entry's text keeps its two parts, its length and a rule on the method page", () => {
  assert.match(problemsWith(entry("record", {}, "## In the records\n\nShort.")).join("\n"), /What it does not tell you/);
  assert.match(problemsWith(entry("record", {}, TEXT + " word".repeat(500))).join("\n"), /runs to \d+ words/);
  assert.match(problemsWith(entry("record", { rule: "nowhere" })).join("\n"), /not a section of the method page/);
});

test("a status entry takes its words from the status wording, and statuses run along the path", () => {
  const held = entry("phase-3-trial", { shelf: "status", status: "phase_3", title: "Typed again" });
  assert.equal(held.title, STATUS_LABELS.phase_3);
  assert.equal(held.answer, STATUS_MEANINGS.phase_3);
  const order = shelfEntries(statusEntries().reverse(), "status").map((item) => item.status);
  assert.deepEqual(order.slice(0, STAGE_PATH.length), STAGE_PATH);
});

test("the journalists' search finds a pair by every word typed, and nothing for a blank", () => {
  const pairs = [{ words: "aspirin dentine repair" }, { words: "usag-1 tooth regrowth" }];
  assert.deepEqual(pickPairs(pairs, "Tooth  regrowth"), [pairs[1]]);
  assert.deepEqual(pickPairs(pairs, "tooth aspirin"), []);
  assert.deepEqual(pickPairs(pairs, "  "), []);
});

test("the copied topic sentence is the summary, the checked month and the address", () => {
  assert.equal(
    topicSentence("1 reported breakthrough tracked: it has no trial in people on record.", "2026-11-13T19:17:20Z", "https://example.org/topic/x"),
    "1 reported breakthrough tracked: it has no trial in people on record. Checked November 2026. https://example.org/topic/x",
  );
});

test("the about page's years join the empty ones and mark the year the records were gathered", () => {
  const pair = { trials: [{ events: [{ day: "2019-05-01" }] }, { events: [{ day: "2022-03-01" }, { day: "2022-09-01" }] }] };
  const strip = yearStrip(pair, "2026-11-13T00:00:00Z");
  assert.deepEqual(
    strip.map((cell) => (cell.kind === "gap" ? `${cell.from}-${cell.to}` : cell.year)),
    [2019, "2020-2021", 2022, "2023-2025", 2026],
  );
  assert.equal(strip[0].records, 1);
  assert.equal(strip[2].records, 2);
  assert.ok(strip[4].checked);
});
