// The home page holds what a reader sees on arrival; the rest of each list is a file
// of rows the page fetches when asked (openspec landing-rows-on-demand). One site is
// built from the fixture export with twelve more claims (synthetic data), so that three
// of its lists are longer than a page and one is not.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";

const work = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-rows-"));
const dist = path.join(work, "dist");
const fixture = JSON.parse(fs.readFileSync(new URL("./fixture-export.json", import.meta.url), "utf8"));
const count = (text, part) => text.split(part).length - 1;
const built = (file) => fs.readFileSync(path.join(dist, file), "utf8");
const words = (html) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

let home;
// One list's part of the page, from its panel's opening tag to the next panel's.
const panel = (view) => {
  const from = home.indexOf(`id="feed-${view}"`);
  assert.ok(from > -1, `no ${view} list`);
  const to = home.indexOf('<section class="feed-panel"', from);
  return home.slice(from, to > -1 ? to : home.indexOf('class="home-section keep-up"', from));
};
// The rows of a table's body: every row but the one of column headers.
const bodyRows = (html) => count(html, '<tr role="row" data-status=');

before(() => {
  const data = structuredClone(fixture);
  const quiet = data.claims.find((claim) => claim.slug === "quiet-claim");
  for (let number = 1; number <= 12; number += 1) {
    const day = `2016-03-${String(number).padStart(2, "0")}`;
    const url = `https://news.example.org/extra-${number}`;
    data.claims.push({
      ...structuredClone(quiet),
      slug: `extra-claim-${number}`,
      headline: `Extra claim ${number}`,
      intervention: { name: `extra-${number} agent`, synonyms: [] },
      first_reported_date: day,
      articles: [{ ...quiet.articles[0], url, title: `Extra report ${number}`, published_date: day }],
      promises: [{ ...quiet.promises[0], article_url: url }],
      events: [],
    });
  }
  const file = path.join(work, "export.json");
  fs.writeFileSync(file, JSON.stringify(data));
  const result = spawnSync("npx", ["astro", "build", "--outDir", dist], {
    env: { ...process.env, EXPORT_FILE: file, ASTRO_TELEMETRY_DISABLED: "1" },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  home = built("index.html");
});

test("Scenario: Opening the home page", () => {
  // Sixteen reports, fifteen claims, thirteen dated promises: ten rows of each are in
  // the page, and the tab and the pager state the whole list's number.
  for (const [view, total, noun] of [
    ["headlines", 16, "headlines"],
    ["claims", 15, "claims"],
    ["promised", 13, "claims"],
  ]) {
    const list = panel(view);
    assert.equal(bodyRows(list), 10, view);
    assert.match(list, new RegExp(`data-rest="/rows/${view}\\.txt"`), view);
    assert.match(home, new RegExp(`id="tab-${view}"[^>]*>\\s*[\\w ]+<span class="count">${total}</span>`), view);
    assert.match(words(list), new RegExp(`1–10 of ${total} ${noun}`), view);
  }
  // No earlier heading of the day-by-day list, and no day of the calendar, is in the page.
  assert.ok(!home.includes("data-earlier="), "an earlier heading is in the page");
  assert.ok(!home.includes("data-to-come"), "the promised dates to come are in the page");
  assert.ok(!home.includes("data-day="), "a calendar day is in the page");
});

test("Scenario: Stepping to the next page", () => {
  // The file holds the rows the page does not, drawn the same way: between them every
  // row of the list, once, in the list's order.
  for (const [view, total] of [["headlines", 16], ["claims", 15], ["promised", 13]]) {
    const rest = built(`rows/${view}.txt`);
    assert.equal(bodyRows(rest), total - 10, view);
    assert.ok(rest.trimStart().startsWith("<tr "), `${view}: a file of rows begins with a row`);
  }
  const titles = (html) => [...html.matchAll(/(Example|Extra) report \d+/g)].map(([title]) => title);
  const all = [...titles(panel("headlines")), ...titles(built("rows/headlines.txt"))];
  assert.equal(all.length, 16);
  assert.equal(new Set(all).size, 16, "a report is drawn twice");
  // Newest first across the two: the fixture's four reports of 2017 to 2019, then 2016's.
  assert.deepEqual(all.slice(0, 4), ["Example report 3", "Example report 2", "Example report 1", "Example report 4"]);
  // A fetched row carries what the status, the topic and the last visit narrow by.
  assert.match(built("rows/headlines.txt"), /<tr role="row" data-status="\w+" data-topic="[\w-]+" data-on="2016-03-\d\d">/);
});

test("Scenario: A count pressed on the line about the last visit", () => {
  // The line is counted from every row's date, which the page holds without the rows.
  const dates = panel("headlines").match(/data-dates="([^"]+)"/)[1].split(" ");
  assert.equal(dates.length, 16);
  assert.equal(dates[0], "2019-05-03");
  assert.match(panel("promised"), /data-dates="[\d\- ]+"/);
});

test("Scenario: A list that is whole in the page", () => {
  // Two status changes: both are in the page, the list names no file and none is built.
  const moved = panel("moved");
  assert.equal(bodyRows(moved), 2);
  assert.ok(!moved.includes("data-rest="));
  assert.ok(!moved.includes("rest-first"));
  assert.ok(!fs.existsSync(path.join(dist, "rows/moved.txt")));
});

test("Scenario: Rows that do not arrive", () => {
  // The words are the page's own: the script sets them where a reader is told.
  const list = panel("headlines");
  assert.match(list, /data-rest-said data-loading="Loading the rest of this list\." data-failed="The rest of this list did not load\."/);
  assert.match(list, /<span role="status" data-rest-line><\/span>/);
  assert.match(list, /<button type="button" class="text-control" hidden data-rest-again>Try again<\/button>/);
  // The rows go where the table's own rows are.
  assert.match(list, /<tbody role="rowgroup" data-rest-into>/);
});

test("Scenario: Scripting off", () => {
  // Read with scripting off, and on paper while the rest are not in the page.
  assert.match(
    words(panel("headlines")),
    /The first 10 of 16 headlines are shown\. Every claim is also listed under its topic: all topics \./,
  );
  assert.match(panel("headlines"), /<p class="rest-first">[^]*?<a href="\/topics">all topics<\/a>/);
  assert.match(words(panel("claims")), /The first 10 of 15 claims are shown\./);
  // The day-by-day list says what it leaves out: sixteen reports and thirteen promises
  // dated before its day headings.
  const days = home.slice(home.indexOf("data-day-list"), home.indexOf('id="lists"'));
  assert.match(days, /data-day-list data-rest="\/rows\/latest\.txt"/);
  assert.match(words(days), /Shown here: what is dated in the 14 days up to the last check\. 29 earlier rows are not shown\./);
});

test("Scenario: Widening the span", () => {
  // The earlier headings are in the file, each waiting for the control as before.
  const rest = built("rows/latest.txt");
  assert.match(rest, /<section class="day-group" id="y-2016"[^>]*data-earlier/);
  assert.equal(count(rest, 'data-kind="report"'), 16);
  assert.equal(count(rest, 'data-kind="promise"'), 13);
  // They are put before the line that says nothing is left, under the day headings.
  assert.match(home, /<p class="none" hidden data-days-none data-rest-before>/);
});

test("Scenario: A file of rows asked for by its address", () => {
  // Rows only: not a page, so no footer, no script and no document around them.
  for (const file of ["rows/headlines.txt", "rows/latest.txt", "rows/on-this-day/05-01.txt"]) {
    const rest = built(file);
    assert.ok(!/<html|<head|<body|<script|<footer/.test(rest), file);
  }
  assert.match(built("_headers"), /\/rows\/\*\n {2}X-Robots-Tag: noindex/);
});

test("Scenario: Opening the home page on a day with an anniversary", () => {
  // The page holds which days have a first report and in which years; each day's
  // reports are a file of their own.
  const block = home.slice(home.indexOf("data-on-this-day"), home.indexOf('id="topics"'));
  const years = JSON.parse(block.match(/data-years="([^"]+)"/)[1].replaceAll("&quot;", '"'));
  assert.deepEqual(years["05-01"], [2018]);
  assert.deepEqual(years["03-01"], [2016]);
  assert.match(block, /data-rows="\/rows\/on-this-day\/DAY\.txt"/);
  for (const [id, list] of Object.entries(years)) {
    const day = built(`rows/on-this-day/${id}.txt`);
    assert.match(day, new RegExp(`<li class="day" data-day="${id}"`), id);
    assert.equal(count(day, "data-year="), list.length, id);
  }
  assert.match(block, /data-failed="The anniversaries for this day did not load\."/);
});
