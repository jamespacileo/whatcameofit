// The home page's day-by-day list as built (openspec home-day-by-day). Two sites are
// built from the fixture export (synthetic data): one checked on a day that puts a
// record, a report and a promise to come in the list, and one with no day of last check.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";

const work = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-days-"));
const fixture = JSON.parse(fs.readFileSync(new URL("./fixture-export.json", import.meta.url), "utf8"));
const count = (text, part) => text.split(part).length - 1;
// Dates are set with spaces that do not break; the tests read them as plain spaces.
const plain = (text) => text.replaceAll(" ", " ").replaceAll("&nbsp;", " ").replaceAll("&#160;", " ");

function build(name, change) {
  const data = structuredClone(fixture);
  change(data);
  const file = path.join(work, `${name}.json`);
  fs.writeFileSync(file, JSON.stringify(data));
  const outDir = path.join(work, name);
  const result = spawnSync("npx", ["astro", "build", "--outDir", outDir], {
    env: { ...process.env, EXPORT_FILE: file, ASTRO_TELEMETRY_DISABLED: "1" },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  return plain(fs.readFileSync(path.join(outDir, "index.html"), "utf8"));
}

// A heading's part of the page, from its opening tag to the next heading's.
function group(html, id) {
  const from = html.indexOf(`id="${id}"`);
  assert.ok(from > -1, `no heading ${id}`);
  const to = html.indexOf('<section class="day-group"', from);
  return html.slice(from, to > -1 ? to : html.indexOf("data-earlier-control", from));
}

let dated;
let undated;

before(() => {
  dated = build("dated", (data) => {
    // Checked on Wednesday 10 September 2025.
    data.last_checked_at = "2025-09-10T07:00:00Z";
    const phase = data.claims.find((claim) => claim.slug === "phase-claim");
    phase.articles.push({
      url: "https://uk.news.example.org/5",
      outlet: "Example Outlet 5",
      title: "Example report 5",
      published_date: "2025-09-08",
      archive_url: null,
    });
    // The status changes on the day its results were posted, and a paper scored below
    // certain is dated a few days later.
    phase.status.code = "phase_3";
    phase.status.history.push({ on: "2025-09-01", code: "phase_3" });
    const paper = phase.events.find((event) => event.type === "followup_paper");
    phase.events.push({ ...paper, id: 9001, event_date: "2025-09-05", confidence: 0.6 });
  });
  undated = build("undated", (data) => {
    data.last_checked_at = null;
  });
});

test("Scenario: Checked on the reader's own date", () => {
  // Read without its styles the line is the long date, once: a phone leaves out the
  // weekday and the end of the month's name, and nothing is said twice.
  const from = dated.indexOf('class="checked-on"');
  const line = dated.slice(from, dated.indexOf("</p>", from));
  assert.equal(
    line.slice(line.indexOf(">") + 1).replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim(),
    "Registries last checked Wednesday 10 September 2025",
  );
  // The page calls no day the current date: which day is today is the reader's
  // browser's to say.
  assert.ok(!dated.includes('aria-current="date"'));
  assert.ok(dated.includes('data-checked="2025-09-10"'));
  // No heading is dated after the last check, and none says "Today" as built: that
  // word is the reader's browser's to add.
  const days = [...dated.matchAll(/id="d-(\d{4}-\d{2}-\d{2})"/g)].map(([, day]) => day);
  assert.ok(days.every((day) => day <= "2025-09-10"));
  assert.ok(!dated.includes("Today,"));
});

test("Scenario: A kind read aloud", () => {
  const record = group(dated, "d-2025-09-01");
  assert.match(record, /data-kind="record"/);
  assert.match(record, /<span class="visually-hidden">Registry record\. <\/span>/);
  assert.match(group(dated, "d-2025-09-08"), /<span class="visually-hidden">News report\. <\/span>/);
  assert.match(dated, /data-kind="promise"[\s\S]*?<span class="row-label">Promised date<\/span>/);
  // The field that shows one kind is the script's, and names each kind in words.
  const field = dated.slice(dated.indexOf('id="feed-kind"'), dated.indexOf("</select>", dated.indexOf('id="feed-kind"')));
  assert.match(dated, /<label class="pick" hidden data-kinds>/);
  for (const [kind, name] of [["report", "News reports"], ["record", "Registry records"], ["promise", "Promised dates"]]) {
    assert.match(field, new RegExp(`<option value="${kind}">${name}</option>`));
  }
});

test("Scenario: A report of an animal study, and what the records add", () => {
  const row = group(dated, "d-2025-09-08");
  assert.match(row, /<a class="followed" href="\/phase-claim"[^>]*>\s*“Example report 5”\s*<\/a>/);
  // The headline and the claim lead; the status is the column after them, a button
  // that opens the detail under the row (openspec latest-rows).
  assert.ok(row.indexOf("row-title") < row.indexOf('class="row-now"'));
  // Its name is short: the status and what it opens. The counts and sentences describe it.
  assert.match(row, /<button type="button" class="row-now" aria-expanded="false" aria-controls="more-phase-claim-2025-09-08" aria-label="Phase 3 trial\. More on phase-claim agent" aria-describedby="more-phase-claim-2025-09-08-said" data-row-open>\s*<strong class="status-name">Phase 3 trial<\/strong>/);
  // What the column says is named once, above the list.
  assert.equal(count(dated, 'class="list-key"'), 1);
  assert.match(row, /<div class="row-more" id="more-phase-claim-2025-09-08" role="region" aria-label="More on phase-claim agent" data-row-more>/);
  assert.match(row, /<p class="row-then">\s*<strong>[^<]+<\/strong>\s+when first reported, [^<]*\. Large late-stage trial in people\.<\/p>/);
  assert.match(row, /Large late-stage trial in people/);
  // What the records add is said in words: the counts in sight, the row's sentences
  // for a screen reader only. The records by date are drawn on the claim page.
  assert.match(row, /<span class="row-counts" id="more-phase-claim-2025-09-08-said">\d+ trials?( · \d+ with results posted)?<span class="visually-hidden"> [^<]*trials on record[^<]*<\/span><\/span>/);
  assert.ok(!row.includes("record-strip"));
  assert.ok(!row.includes("row-adds"));
});

test("Scenario: An approval that changed the status, and a record that changed nothing", () => {
  const changed = group(dated, "d-2025-09-01");
  assert.match(changed, /class="row-now is-changed"[^>]*aria-label="Changed from Phase 2 trial to Phase 3 trial\. More on phase-claim agent"/);
  assert.match(changed, /<span class="new-tag">Changed<\/span>\s*<span class="row-was">from Phase 2 trial<\/span><\/span>\s*<strong class="status-name">Phase 3 trial<\/strong>/);
  // What was recorded is said of the record, not in a status's words.
  assert.match(changed, /<li class="row-item is-record"><a href="[^"]+">NCT00000002<\/a><span>results posted<\/span>/);
  const paper = group(dated, "d-2025-09-05");
  assert.ok(!paper.includes("Changed"));
  assert.match(paper, /class="row-now" [^>]*aria-label="Phase 3 trial\. More on phase-claim agent"/);
  // Scenario: A follow-up paper scored 0.6.
  assert.match(paper, /Medium match · 60%/);
  // A registry row leads with the report it belongs to, and says how long ago the claim
  // was first reported; what was recorded is one dated item.
  assert.match(paper, /<span class="row-age">First reported 6 years ago<\/span>/);
  assert.match(paper, /<h4 class="row-title"><a href="\/phase-claim">“Example report 5”<\/a><\/h4>/);
  assert.match(paper, /<li class="row-item is-record"><a href="https:\/\/registry\.example\/record\/4">[^<]+<\/a><span>Follow-up paper<\/span><span class="when">5 Sep 2025<\/span><\/li>/);
});

test("Scenario: Promises still to come", () => {
  const toCome = dated.slice(dated.indexOf("data-to-come"), dated.indexOf('<section class="day-group"'));
  assert.match(toCome, /1 promised date to come\./);
  assert.match(toCome, /Next: <span data-to-come-next>31 Dec 2025<\/span>/);
  assert.equal(count(toCome, 'data-kind="promise"'), 1);
  // Nothing says whether a promised date has passed.
  assert.ok(!/overdue|missed|has passed|late\b/i.test(toCome));
});

test("Scenario: One older claim under the list", () => {
  const from = dated.indexOf("data-older");
  const older = dated.slice(from, dated.indexOf("</section>", from));
  assert.match(older, /One older claim, picked by the date\./);
  // The one row marked as picked is under that heading, after every dated heading.
  assert.equal(dated.match(/<li class="day-row report-row"[^>]*data-picked/g).length, 1);
  assert.match(older, /<li class="day-row report-row"[^>]*data-picked/);
  assert.ok(from > dated.lastIndexOf('<section class="day-group"'));
});

test("Scenario: The spans a reader can keep to", () => {
  const from = dated.indexOf('id="feed-span"');
  const field = dated.slice(from, dated.indexOf("</select>", from));
  assert.deepEqual(
    [...field.matchAll(/<option value="([a-z]+)">([^<]+)</g)].map(([, value, name]) => `${value}: ${name}`),
    ["week: Past week", "month: Past month", "year: Past year", "all: All time"],
  );
  // The span and its end are the script's: as built every row is shown.
  assert.match(dated, /<label class="pick" hidden data-spans>/);
  assert.match(dated, /<p class="earlier" hidden data-span-end>/);
});

test("Scenario: Scripting off", () => {
  // Every row is in the page as built: five reports and the older claim, two records,
  // one promise.
  assert.equal(count(dated, 'data-kind="report"'), 6);
  assert.equal(count(dated, 'data-kind="record"'), 2);
  assert.equal(count(dated, 'data-kind="promise"'), 1);
  // Earlier headings wait for the control only where scripts run; day headings never.
  assert.match(dated, /<section class="day-group" id="y-2019"[^>]*data-earlier/);
  assert.ok(!/<section class="day-group" id="d-[^>]*data-earlier/.test(dated));
  assert.match(dated, /<p class="earlier" hidden data-earlier-control>/);
});

test("A headline's name is on the page once", () => {
  const names = [...dated.matchAll(/view-transition-name: ([^";]+)/g)].map(([, name]) => name);
  assert.ok(names.length > 0);
  assert.equal(new Set(names).size, names.length, "a name is used twice");
  // The names are on the day-by-day list's rows, not on the Headlines table's.
  const headlines = dated.slice(dated.indexOf('id="feed-headlines"'));
  assert.ok(!headlines.includes("view-transition-name"));
});

test("Scenario: An export with no day of last check", () => {
  assert.ok(!undated.includes('<section class="days"'));
  assert.ok(!undated.includes('class="day-row'));
  // The four lists follow the lookup, with their counts and their named headlines.
  assert.ok(undated.indexOf("data-scoreboard") < undated.indexOf('role="tablist"'));
  assert.ok(undated.includes("view-transition-name"));
  assert.ok(!undated.includes('id="lists"'));
});

test("the home page says it is not medical advice", () => {
  assert.match(dated, /Not medical advice\. A registered trial is not a treatment option\./);
});
