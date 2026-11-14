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
  // Read without its styles the heading is the long date, once: a phone leaves out the
  // weekday and the end of the month's name, and nothing is said twice.
  const title = dated.slice(dated.indexOf('id="days-title"'), dated.indexOf("</h2>", dated.indexOf('id="days-title"')));
  assert.equal(
    title.slice(title.indexOf(">") + 1).replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim(),
    "Registries last checked Wednesday 10 September 2025",
  );
  assert.match(title, /<span class="on-wide">Wednesday <\/span>10 Sep<span class="on-wide">tember<\/span> 2025/);
  // The seven days up to it, each leading to its heading.
  for (const day of ["04", "05", "06", "07", "08", "09", "10"]) {
    assert.ok(dated.includes(`<a href="#d-2025-09-${day}"`), `no link to 2025-09-${day}`);
    assert.ok(dated.includes(`id="d-2025-09-${day}"`), `no heading for 2025-09-${day}`);
  }
  // The day of the last check is marked as that. Which day is today is the reader's
  // browser's to say: the built page calls no day the current date.
  assert.match(dated, /<a href="#d-2025-09-10" data-checked-day/);
  assert.ok(!dated.includes('aria-current="date"'));
  // No heading is dated after the last check, and none says "Today" as built: that
  // word is the reader's browser's to add.
  const days = [...dated.matchAll(/id="d-(\d{4}-\d{2}-\d{2})"/g)].map(([, day]) => day);
  assert.ok(days.every((day) => day <= "2025-09-10"));
  assert.ok(!dated.includes("Today,"));
});

test("Scenario: A day with nothing dated", () => {
  assert.match(group(dated, "d-2025-09-09"), /<span data-says[^>]*>Nothing dated<\/span>/);
  assert.match(group(dated, "d-2025-09-08"), /<span data-says[^>]*>1 report<\/span>/);
});

test("Scenario: A kind read aloud", () => {
  const record = group(dated, "d-2025-09-01");
  assert.match(record, /data-kind="record"/);
  assert.match(record, /<span class="row-label">Registry record<\/span>/);
  assert.match(group(dated, "d-2025-09-08"), /<span class="visually-hidden">News report\. <\/span>/);
  assert.match(dated, /data-kind="promise"[\s\S]*?<span class="row-label">Promised date<\/span>/);
  // The controls that show one kind are the script's, and carry the three grounds.
  assert.match(dated, /<div class="kinds"[^>]*hidden/);
  for (const kind of ["report", "record", "promise"]) {
    assert.match(dated, new RegExp(`data-kind-pick="${kind}"[^>]*>\\s*<span class="swatch ${kind}"`));
  }
});

test("Scenario: A report of an animal study, and what the records add", () => {
  const row = group(dated, "d-2025-09-08");
  assert.match(row, /<a class="followed" href="\/phase-claim"[^>]*>\s*“Example report 5”\s*<\/a>/);
  assert.match(row, /Evidence when first reported/);
  assert.match(row, /On record now<\/span>\s*<strong class="status-name">Phase 3 trial<\/strong>/);
  assert.match(row, /Large late-stage trial in people/);
  assert.match(row, /<p class="row-adds">[^<]*trials on record/);
});

test("Scenario: An approval that changed the status, and a record that changed nothing", () => {
  const changed = group(dated, "d-2025-09-01");
  assert.match(changed, /<span class="new-tag">Changed<\/span>\s*<span>Was: Phase 2 trial\. Now: Phase 3 trial\.<\/span>/);
  const paper = group(dated, "d-2025-09-05");
  assert.ok(!paper.includes("Changed"));
  assert.match(paper, /Status now:\s*<strong class="status-name">Phase 3 trial<\/strong>/);
  // Scenario: A follow-up paper scored 0.6.
  assert.match(paper, /Medium match · 60%/);
  // A registry row names the report it belongs to.
  assert.match(paper, /The report:\s*<a href="\/phase-claim">“Example report 5”<\/a>/);
});

test("Scenario: Promises still to come", () => {
  const toCome = dated.slice(dated.indexOf("data-to-come"), dated.indexOf('<section class="day-group"'));
  assert.match(toCome, /1 promised date to come\./);
  assert.match(toCome, /Next: <span data-to-come-next>31 Dec 2025<\/span>/);
  assert.equal(count(toCome, 'data-kind="promise"'), 1);
  // Nothing says whether a promised date has passed.
  assert.ok(!/overdue|missed|has passed|late\b/i.test(toCome));
});

test("Scenario: The day of the last check shows one older claim", () => {
  const day = group(dated, "d-2025-09-10");
  assert.match(day, /One older claim, picked by the date\./);
  // The one row marked as picked is under that day's heading.
  assert.equal(dated.match(/<li class="day-row report-row"[^>]*data-picked/g).length, 1);
  assert.match(day, /<li class="day-row report-row"[^>]*data-picked/);
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

test("Scenario: Where the four lists stand", () => {
  const order = ['class="band home"', "data-days", "data-scoreboard", "data-day-list", 'id="lists"', 'class="since"', 'role="tablist"', 'id="feed-headlines"'];
  const at = order.map((part) => dated.indexOf(part));
  order.forEach((part, index) => assert.ok(at[index] > -1, `${part} is not on the page`));
  assert.deepEqual([...at].sort((a, b) => a - b), at);
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
