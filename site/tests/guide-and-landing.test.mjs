import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import { yearStrip } from "../src/lib/about.ts";
import { CLAIM_FIELDS, pickClaims } from "../src/lib/audiences.ts";
import { APPLIES, assertNoAdvice, claimsAtWork, guideProblems, readEntry, shelfEntries, statusSlug } from "../src/lib/guide.ts";
import { DATA_LICENCE, openData } from "../src/lib/open-data.ts";
import { topicSentence } from "../src/lib/share.ts";
import { STAGE_PATH, STATUS_LABELS, STATUS_MEANINGS } from "../src/lib/status.ts";

const fixture = JSON.parse(fs.readFileSync(new URL("./fixture-export.json", import.meta.url), "utf8"));
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
// The statuses' entries and the one the record strip's key links to.
const statusEntries = () => [
  ...codes.map((code) => entry(statusSlug(code), { shelf: "status", status: code })),
  entry("record-strip"),
];
const problemsWith = (...extra) => guideProblems([...statusEntries(), ...extra]);

test("a complete set of entries passes, and a status without an entry is named", () => {
  assert.deepEqual(problemsWith(entry("record")), []);
  const missing = guideProblems(statusEntries().filter((held) => held.status !== "retracted"));
  assert.equal(missing.length, 1);
  assert.match(missing[0], /Origin paper retracted.*has no guide entry/);
});

test("Scenario: Guide entry missing", () => {
  const without = guideProblems(statusEntries().filter((held) => held.slug !== "record-strip"));
  assert.equal(without.length, 1);
  assert.match(without[0], /no entry "record-strip"/);
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

test("an entry lists up to three claims its word applies to, newest report first", () => {
  const claims = fixture.claims;
  const work = claimsAtWork(entry("claim", { applies: "claims" }), claims);
  assert.equal(work.total, claims.length);
  assert.ok(work.shown.length <= 3);
  const dates = work.shown.map((claim) => claim.first_reported_date ?? "");
  assert.deepEqual(dates, [...dates].sort().reverse());
  assert.equal(claimsAtWork(entry("origin-paper"), claims), null);
  for (const code of codes) assert.ok(APPLIES[code], `no set of claims for ${code}`);
});

test("the journalists' search finds a claim by every word typed, and nothing for a blank", () => {
  const claims = [{ words: "aspirin dentine repair" }, { words: "usag-1 tooth regrowth" }];
  assert.deepEqual(pickClaims(claims, "Tooth  regrowth"), [claims[1]]);
  assert.deepEqual(pickClaims(claims, "tooth aspirin"), []);
  assert.deepEqual(pickClaims(claims, "  "), []);
});

test("the copied topic sentence is the summary, the checked month and the address", () => {
  assert.equal(
    topicSentence("1 reported breakthrough tracked: it has no trial in people on record.", "2026-11-13T19:17:20Z", "https://example.org/topic/x"),
    "1 reported breakthrough tracked: it has no trial in people on record. Checked November 2026. https://example.org/topic/x",
  );
});

test("the about page's years join the empty ones and mark the promised and checked years", () => {
  const claim = {
    first_reported_date: "2019-05-01",
    articles: [{ url: "https://example.org/a", published_date: "2019-05-01" }],
    events: [{ event_date: "2022-03-01" }, { event_date: "2022-09-01" }],
    promises: [{ description: "Trials by 2027", parsed_date: "2027-01-01", article_url: "https://example.org/a" }],
  };
  const strip = yearStrip(claim, "2026-11-13");
  assert.deepEqual(
    strip.map((cell) => (cell.kind === "gap" ? `${cell.from}-${cell.to}` : cell.year)),
    [2019, "2020-2021", 2022, "2023-2025", 2026, 2027],
  );
  assert.equal(strip[2].records, 2);
  assert.equal(strip[0].reports, 1);
  assert.ok(strip[4].checked && strip[5].promised);
});

test("every field of a claim in the data file has words on the researchers' page", () => {
  const file = openData(fixture, DATA_LICENCE, "credit", "https://example.org/how-it-works");
  for (const field of Object.keys(file.claims[0])) {
    assert.ok(CLAIM_FIELDS[field], `the data file's field ${field} is not described`);
  }
});
