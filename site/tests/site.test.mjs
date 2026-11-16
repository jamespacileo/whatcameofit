// The built site, checked against the scenarios in openspec site-publishing.
// Builds once from tests/fixture-export.json (synthetic data) into a temporary directory.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";

const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-site-"));
const page = (relative) => fs.readFileSync(path.join(dist, relative), "utf8");
const count = (text, part) => text.split(part).length - 1;

function htmlFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) return htmlFiles(full);
    return entry.name.endsWith(".html") ? [full] : [];
  });
}

function build(exportFile, outDir) {
  return spawnSync("npx", ["astro", "build", "--outDir", outDir], {
    env: { ...process.env, EXPORT_FILE: exportFile, ASTRO_TELEMETRY_DISABLED: "1" },
    encoding: "utf8",
  });
}

before(() => {
  const result = build("tests/fixture-export.json", dist);
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

test("Scenario: Reader opens a claim", () => {
  const html = page("phase-claim/index.html");
  assert.match(html, /Phase 2 trial/);
  assert.match(html, /Synthetic claim with a started trial/);
  // Four approved events, each a record that links straight to its source.
  for (const id of [2, 3, 4, 5]) {
    assert.ok(html.includes(`https://registry.example/record/${id}"`), `event ${id} has no link`);
  }
  assert.equal(count(html, 'id="record-'), 4);
});

test("Scenario: Unknown slug", () => {
  assert.match(page("404.html"), /No page at this address/);
  // The path with no place marked: six places, none of them the marker.
  const drawing = page("404.html").match(/<svg class="unfound"[\s\S]*?<\/svg>/)[0];
  assert.equal(count(drawing, 'class="place"'), 6);
  assert.doesNotMatch(drawing, /here/);
});

test("Scenario: The mark in the masthead", () => {
  // Drawn into the page so its parts can move; the drawing is the reverse mark's own.
  const drawn = page("index.html").match(/<svg class="mark"[\s\S]*?<\/svg>/)[0];
  const file = fs.readFileSync("public/mark-reverse.svg", "utf8");
  const shapes = (svg) => [...svg.matchAll(/ (?:d|r|cx|cy|fill|stroke-width)="[^"]+"/g)].map(([part]) => part.trim()).sort();
  assert.deepEqual(shapes(drawn).filter((part) => part !== 'fill="none"'), shapes(file).filter((part) => part !== 'fill="none"'));
});

test("Scenario: The method page's drawing", () => {
  const figure = page("how-it-works/index.html").match(/<figure class="made"[\s\S]*?<\/figure>/)[0];
  assert.match(figure, /made-up records, not a tracked claim/);
  // Whole without scripting or motion: the control that plays it starts hidden.
  assert.match(figure, /<button[^>]*data-made-play[^>]*hidden|<button[^>]*hidden[^>]*data-made-play/);
  assert.match(figure, /Place 3 of 6/);
});

test("Scenario: Status produced by one trial", () => {
  const html = page("phase-claim/index.html");
  // The registered and started events produced the status; the paper and results did not.
  // Each is marked in the timetable, and the mark is named once in the key.
  assert.equal(count(html, ">basis of status<"), 2);
  assert.equal(count(html, "Basis of status"), 1);
  assert.match(html, /The status rests on these records/);
});

test("Scenario: Claim with two articles", () => {
  const html = page("quiet-claim/index.html");
  for (const number of [1, 2]) {
    assert.ok(html.includes(`href="https://news.example.org/${number}"`));
    assert.ok(html.includes(`Example Outlet ${number}`));
    assert.ok(html.includes(`Example report ${number}`));
  }
  assert.match(html, /archived copy/);
});

test("Scenario: Vertical with claims", () => {
  const html = page("topic/gum-disease/index.html");
  for (const slug of ["quiet-claim", "phase-claim", "approved-claim"]) {
    assert.ok(html.includes(`href="/${slug}"`), `${slug} is not listed`);
  }
  assert.match(html, /3 reported breakthroughs tracked/);
  assert.match(html, /Preclinical only/);
  assert.match(html, /Phase 2 trial/);
});

test("Scenario: Vertical with no published claims", () => {
  // Its page exists, but nothing links to it until a claim is published in it.
  assert.match(page("topic/empty-topic/index.html"), /0 reported breakthroughs tracked/);
  for (const file of ["index.html", "404.html", "phase-claim/index.html"]) {
    assert.ok(!page(file).includes("empty-topic"), `${file} links to an empty topic`);
  }
  // With one listed topic, the menu names it.
  assert.match(page("index.html"), /<a href="\/topic\/gum-disease"[^>]*>Gum disease<\/a>/);
});

test("the topic directory lists every listed topic and no empty one", () => {
  const html = page("topics/index.html");
  assert.match(html, /<a href="\/topic\/gum-disease">Gum disease<\/a>/);
  assert.ok(!html.includes("empty-topic"));
  assert.match(html, /1 topic, 3\s+claims tracked/);
});

test("Scenario: Topics with groups", () => {
  const html = page("topics/index.html");
  // The topic sits under its group's heading, and the jump row names the group.
  const section = html.slice(html.indexOf('<section class="letter" id="group-mouth-and-teeth"'));
  assert.match(section, /^<section[^>]*data-match="Mouth and teeth"[^>]*>\s*<h2[^>]*>Mouth and teeth<\/h2>/);
  assert.ok(section.indexOf("/topic/gum-disease") < section.indexOf("</section>"));
  assert.match(html, /aria-label="Jump to a group"[^>]*>\s*<a href="#group-mouth-and-teeth">Mouth and teeth<\/a>/);
  assert.ok(!html.includes('id="letter-G"'));
});

test("Scenario: No topic has a group", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  for (const vertical of fixture.verticals) delete vertical.group;
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-flat-")), "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-site-flat-"));
  const result = build(file, out);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const html = fs.readFileSync(path.join(out, "topics/index.html"), "utf8");
  assert.match(html, /aria-label="Jump to a letter"[^>]*>\s*<a href="#letter-G">G<\/a>/);
  assert.match(html, /<section class="letter" id="letter-G"/);
  assert.ok(!html.includes('id="group-'));
});

test("a topic page marks each row with its status and keeps amber for promises", () => {
  const html = page("topic/gum-disease/index.html");
  // Each row names its status, so the filter can narrow the table. Three claims are
  // read at a glance, so the filter itself is left out of so short a list.
  assert.equal(count(html, 'class="place"'), 0);
  for (const code of ["preclinical_only", "phase_2", "approved"]) {
    assert.equal(count(html, `<tr data-status="${code}"`), 1, code);
  }
  // Only one claim has a dated promise, so the amber column is present here
  // and absent from the approved list, where none has.
  assert.match(html, /Latest promise/);
  assert.doesNotMatch(page("it-happened/index.html"), /Latest promise/);
});

test("Scenario: Topic index: every row of a claim list carries its record strip and its status label", () => {
  for (const file of ["topic/gum-disease/index.html", "it-happened/index.html"]) {
    const html = page(file);
    const rows = html.split("<tr data-status=").slice(1).map((row) => row.slice(0, row.indexOf("</tr>")));
    assert.ok(rows.length > 0, file);
    for (const row of rows) {
      // One image, named in sentences, under a status label that stays in sight.
      assert.equal(count(row, '<svg class="strip-line" role="img" aria-label="Records by date. '), 1, file);
      assert.match(row, /class="status-name"/);
      // The counts are in the column beside it, not said twice.
      assert.ok(!row.includes("strip-counts"));
    }
    // One key, before the first strip, naming the three marks a list draws.
    assert.equal(count(html, 'class="strip-key"'), 1, file);
    assert.ok(html.indexOf('class="strip-key"') < html.indexOf('class="record-strip"'));
    const key = html.slice(html.indexOf('class="strip-key"'), html.indexOf("</div>", html.indexOf('class="strip-key"')));
    for (const name of ["Registry record", "Results posted", "News report"]) assert.ok(key.includes(name), name);
    for (const name of ["Regulator decision", "Promised date"]) assert.ok(!key.includes(name), name);
    // A list draws no promise and no decision: its columns and status say them.
    assert.ok(!html.includes('class="strip-promise"') && !html.includes('class="strip-decision"'), file);
  }
});

test("Scenario: Claim page: the claim's own record strip, its years and a key of its marks", () => {
  const html = page("phase-claim/index.html");
  const block = html.slice(html.indexOf('class="claim-strip"'), html.indexOf('class="legend"'));
  assert.equal(count(block, '<svg class="strip-line" role="img" aria-label="Records by date. '), 1);
  assert.match(block, /class="strip-years"[^>]*><span>\d{4}<\/span><span>Last checked [^<]+<\/span>/);
  // The key names the marks drawn and no others; the axis end is named under it.
  assert.ok(block.includes("News report"));
  assert.ok(!block.includes("Registries last checked"));
  assert.ok(!block.includes("How to read it"));
});

test("Scenario: Search by intervention name", () => {
  // Search indexes the part of a claim page marked for it; the synonyms must be inside.
  const html = page("quiet-claim/index.html");
  const indexed = html.slice(html.indexOf("data-pagefind-body"), html.indexOf("</article>"));
  assert.match(indexed, /QC-77/);
  assert.match(indexed, /quietamab/);
});

test("Scenario: Search with no result", () => {
  const scripts = fs
    .readdirSync(path.join(dist, "_astro"))
    .filter((name) => name.endsWith(".js"))
    .map((name) => page(path.join("_astro", name)))
    .join("\n");
  assert.match(scripts + page("index.html"), /Nothing tracked here matches/);
  assert.match(page("index.html"), /<template id="unfound">\s*<svg class="unfound"/);
});

test("Scenario: Home lists the newest reports", () => {
  const html = page("index.html");
  assert.match(html, /Headlines reported most recently/);
  // Newest first, across claims: reports 3, 2, 1, then 4. Read in the Headlines list:
  // the day-by-day list above it holds the same reports under their dates.
  const headlines = html.slice(html.indexOf('id="feed-headlines"'));
  const order = [3, 2, 1, 4].map((number) => headlines.indexOf(`Example report ${number}`));
  assert.ok(order.every((position) => position > -1), "a report is missing from the home page");
  assert.deepEqual([...order].sort((a, b) => a - b), order);
  // The headline opens the claim; the outlet opens the report itself.
  assert.match(html, /<a class="followed" href="\/phase-claim"[^>]*>“Example report 3”<\/a>/);
  assert.match(html, /<a href="https:\/\/uk\.news\.example\.org\/3">Example Outlet 3<\/a>/);
});

test("Scenario: A list that fits one page", () => {
  // Four reports and two status changes: every row is on the first page, with a pager that
  // stays out of sight under each list.
  const html = page("index.html");
  assert.doesNotMatch(html, /<tr[^>]*data-later/);
  assert.match(html, /<nav class="pager"[^>]*data-pager="headlines"[^>]*hidden/);
  assert.match(html, /<nav class="pager"[^>]*data-pager="moved"[^>]*hidden/);
  assert.match(page("topic/gum-disease/index.html"), /data-pager="claims"/);
});

test("Scenario: Lists on the home page", () => {
  const html = page("index.html");
  // One tab per list that has rows, in a fixed order.
  const tabs = [...html.matchAll(/role="tab"[^>]*data-view="(\w+)"/g)].map((match) => match[1]);
  assert.deepEqual(tabs, ["headlines", "claims", "moved", "promised", "quiet"]);
  // A change names the status from that day and the one before, in the site's wording.
  const moved = html.slice(html.indexOf('id="feed-moved"'), html.indexOf('id="feed-promised"'));
  assert.equal(count(moved, "<tr role=\"row\""), 3, "two changes under one header row");
  assert.ok(moved.indexOf("Was: Trial registered") < moved.indexOf("Was: Preclinical only"));
  // A dated promise sits beside the status now; the no-signal list holds the quiet claim.
  const promised = html.slice(html.indexOf('id="feed-promised"'), html.indexOf('id="feed-quiet"'));
  assert.match(promised, /human trials by <strong>2025<\/strong>/);
  assert.match(promised, /Preclinical only/);
  assert.match(html.slice(html.indexOf('id="feed-quiet"')), /No signal for 6 years/);
});

// Openspec site-publishing, change home-claims-list: the claims themselves, as a list.
const claimsPanel = () => {
  const html = page("index.html");
  return html.slice(html.indexOf('id="feed-claims"'), html.indexOf('id="feed-moved"'));
};
const rowsOf = (panel) => panel.split('<tr role="row"').slice(2);

test("Scenario: Every claim once", () => {
  const html = page("index.html");
  const headlines = html.slice(html.indexOf('id="feed-headlines"'), html.indexOf('id="feed-claims"'));
  // A claim with several reports has a row for each under Headlines and one under Claims.
  assert.ok(count(headlines, 'href="/phase-claim/"') + count(headlines, 'href="/phase-claim"') >= 1);
  const rows = rowsOf(claimsPanel());
  assert.equal(rows.length, 3);
  for (const slug of ["phase-claim", "quiet-claim", "approved-claim"]) {
    assert.equal(rows.filter((row) => row.includes(`href="/${slug}`)).length, 1, slug);
  }
  assert.match(claimsPanel(), /<span class="count">3<\/span>|1–3 of 3|3 claims/);
});

test("Scenario: Claims in order of first report", () => {
  const order = rowsOf(claimsPanel()).map((row) => row.match(/href="\/([\w-]+)/)[1]);
  // 2019, then 2018, then 2017: a date, whatever the status or the testing.
  assert.deepEqual(order, ["phase-claim", "quiet-claim", "approved-claim"]);
});

test("Scenario: Narrowed to a status", () => {
  // The home page's own status counts and topic choice narrow every list by these marks.
  for (const row of rowsOf(claimsPanel())) {
    assert.match(row, /data-status="\w+"/);
    assert.match(row, /data-topic="gum-disease"/);
  }
  assert.match(claimsPanel(), /data-none hidden>Nothing in this list for that choice\./);
});

test("Scenario: Narrowed to a topic", () => {
  // Every row names its topic, which the home page's topic choice narrows by.
  const rows = rowsOf(claimsPanel());
  assert.equal(rows.filter((row) => /data-topic="[\w-]+"/.test(row)).length, rows.length);
});

test("Scenario: A list named in the address", () => {
  const html = page("index.html");
  // The tab names the panel it shows; the page's script records the one in view as
  // "view" in the address. Without scripting the tabs stay hidden and every list is
  // shown under its own heading, Claims after Headlines.
  assert.match(html, /role="tab"[^>]*aria-controls="feed-claims"[^>]*data-view="claims"/);
  assert.match(html, /role="tablist" aria-label="Lists of tracked claims" hidden/);
  assert.match(claimsPanel(), /<h2 class="bar">\s*Every claim tracked\s*<\/h2>/);
  assert.ok(html.indexOf('id="feed-headlines"') < html.indexOf('id="feed-claims"'));
});

test("Scenario: More claims than a page holds", () => {
  const panel = claimsPanel();
  // The list's own pager, which says which rows of the total are in view.
  assert.match(panel, /data-pager="claims"/);
  assert.match(wordsOf(panel), /3 claims/);
});

test("Scenario: Narrow screen, a list of claims", () => {
  const styles = fs
    .readdirSync(path.join(dist, "_astro"))
    .filter((name) => name.endsWith(".css"))
    .map((name) => fs.readFileSync(path.join(dist, "_astro", name), "utf8"))
    .join("");
  // Under 40rem each claim is a block: no cell keeps a column's share of the width.
  assert.match(styles, /\.index td\.tested,[^{]*\.index:has\(\.tested\) \.status[^{]*\{width:auto\}/);
  assert.match(claimsPanel(), /class="tested" data-column="Tested in people"/);
});

test("Scenario: Promise beside the record", () => {
  const panel = claimsPanel();
  const heads = [...panel.matchAll(/<th role="columnheader"[^>]*>([^<]+)</g)].map((match) => match[1].trim());
  assert.deepEqual(heads, ["Claim", "First reported", "Tested in people", "Promised", "Status now"]);
  const quiet = rowsOf(panel).find((row) => row.includes('href="/quiet-claim'));
  // The promise, on the promise colour, between how much it was tested and its status.
  assert.ok(quiet.indexOf('class="tested"') < quiet.indexOf('class="promise"'));
  assert.ok(quiet.indexOf('class="promise"') < quiet.indexOf('class="status"'));
  assert.match(quiet, /<strong>2025<\/strong>/);
});

test("Scenario: Claim with three trials", () => {
  const words = (slug) => wordsOf(rowsOf(claimsPanel()).find((row) => row.includes(`href="/${slug}`)));
  // The count, the largest size and whether results are posted: never what was found.
  assert.match(words("phase-claim"), /In 7 trials\s+1,200 people in the largest\. Results posted by 1 of 7/);
  assert.match(words("quiet-claim"), /None on record\s+The first report was about a study in animals/);
  assert.match(claimsPanel(), /counts the trials on record; it does not say what they found\./);
  assert.doesNotMatch(wordsOf(claimsPanel()), /p\s*[=<]|\d\.\d/);
});

test("Scenario: Same words as the claim page", () => {
  const row = wordsOf(rowsOf(claimsPanel()).find((entry) => entry.includes('href="/phase-claim')));
  const brief = wordsOf(sectionOf(page("phase-claim/index.html"), "brief"));
  assert.match(brief, /In 7 trials\. 1,200 people in the largest/);
  assert.match(row, /In 7 trials/);
  assert.match(row, /1,200 people in the largest/);
});

test("Scenario: Topic page", () => {
  const html = page("topic/gum-disease/index.html");
  const heads = [...html.matchAll(/<th role="columnheader"[^>]*>([^<]+)</g)].map((match) => match[1].trim());
  assert.ok(heads.includes("Tested in people"), heads.join(", "));
  assert.equal(count(html, 'class="tested"'), 3);
  // Under 40rem the cell is a labelled line of its block.
  assert.match(html, /class="tested" data-column="Tested in people"/);
});

test("Scenario: Counts on the path", () => {
  const html = page("index.html");
  const strip = html.slice(html.indexOf("data-stage-filter"), html.indexOf('role="tablist"'));
  // Three claims: one preclinical, one in phase 2, one approved. The field narrows
  // every list under it and keeps the pick in the address.
  assert.match(strip, /data-scope="\[data-feed\]"/);
  assert.match(strip, /data-param="status"/);
  for (const [code, label] of [["preclinical_only", "Preclinical only"], ["phase_2", "Phase 2 trial"], ["approved", "Approved"]]) {
    assert.match(strip, new RegExp(`<option value="${code}"[^>]*>\\s*${label} \\(1\\)\\s*</option>`));
  }
  assert.match(strip, /<option value="phase_1"[^>]*disabled/);
  // Each row carries what the strip and the topic choice narrow by.
  assert.match(html, /<tr[^>]*data-status="phase_2"[^>]*data-topic="gum-disease"/);
});

test("Scenario: Anniversaries on the home page", () => {
  const html = page("index.html");
  const block = html.slice(html.indexOf("data-on-this-day"), html.indexOf('id="topics"'));
  // Out of sight until the reader's date picks a day; every day with a report is there.
  assert.match(html, /<section class="on-this-day"[^>]*hidden/);
  for (const day of ["05-01", "05-03", "05-04"]) assert.ok(block.includes(`data-day="${day}"`), day);
  assert.match(block, /data-year="2019"/);
  assert.match(block, /href="\/anniversaries"/);
});

test("Scenario: A returning reader's home page", () => {
  const html = page("index.html");
  // Filled in by the reader's browser: nothing about a visit is in the built page.
  assert.match(html, /<p class="since"[^>]*hidden/);
  assert.match(html, /<section class="following"[^>]*hidden/);
  assert.match(html, /Kept in this browser only\./);
  // Each dated row carries its day, so the browser can count what is dated since a visit.
  assert.match(html, /<tr[^>]*data-on="2019-05-03"/);
  const moved = html.slice(html.indexOf('id="feed-moved"'), html.indexOf('id="feed-promised"'));
  assert.match(moved, /data-on="2023-02-01"/);
  // How to keep up is said in the open, under the lists: the feed by a plain name, and,
  // for a reader who follows nothing yet, what following is (shown by their browser).
  const keep = html.slice(html.indexOf('class="keep-up"'), html.indexOf("data-on-this-day"));
  assert.match(keep, /<a class="share" href="\/changes\.xml">/);
  assert.match(keep, /Subscribe to status changes/);
  assert.match(keep, /<p class="keep-hint" hidden data-follow-hint>/);
  // The counts and the topic choice are part of the lists they narrow.
  const feed = html.slice(html.indexOf("data-feed"));
  assert.ok(feed.indexOf("data-scoreboard") < feed.indexOf('role="tablist"'));
  // A step that leads nowhere is passed over by the Tab key.
  assert.match(html, /<button type="button" data-step="-1" aria-disabled="true" tabindex="-1">Previous<\/button>/);
  // The head of the day-by-day list says when the registries were last checked.
  assert.match(html, /Registries last checked\s+<span class="unbroken/);
  // The status and topic choices are fields, shown by the reader's browser.
  assert.match(html, /<label class="pick" hidden data-status-filter>/);
});

test("Scenario: Following from a claim page", () => {
  const html = page("phase-claim/index.html");
  // The pill carries what the browser keeps: the claim, its headline, its status in words.
  assert.match(
    html,
    /<button[^>]*data-follow[^>]*data-slug="phase-claim"[^>]*data-status="Phase 2 trial"[^>]*aria-pressed="false"[^>]*hidden/,
  );
  // Under the answer and again beside the reminders, Follow comes with its words: what
  // it does, and where the list is once followed.
  assert.equal(count(html, '<div class="follow-offer"'), 2);
  const offer = html.slice(html.indexOf("data-follow-offer"), html.indexOf('class="glance"'));
  assert.match(offer, /Lists this claim on the home page, with a note when its status changes\./);
  assert.match(offer, /<a href="\/#following">the home page<\/a>/);
  // A change since the reader last looked is said on the page they land on.
  assert.match(html, /<p class="was-note" hidden data-follow-was/);
  assert.ok(html.indexOf('class="digest"') < html.indexOf('class="was-note"'));
  // A way back beside the answer, and a next step at the end of the page.
  const digest = html.slice(html.indexOf('class="digest"'), html.indexOf('class="glance"'));
  assert.match(digest, /<a href="#check-again">Check again later<\/a>/);
  assert.match(html, /<a class="share" href="\/#search">/);
  // The networks open on request; copying the link does not wait behind them.
  assert.match(html, /<details class="post-to">/);
  const actions = html.slice(html.indexOf('class="take-actions"'), html.indexOf('class="post-to"'));
  assert.match(actions, /data-copy="page-address"/);
});

test("Scenario: A topic's status changes as a feed", () => {
  const html = page("topic/gum-disease/index.html");
  assert.match(html, /href="\/changes\/topic\/gum-disease\.xml"/);
  assert.match(html, /data-share/);
  // A topic page ends on a next step too, and its rows carry the day first reported,
  // so a reader's browser can mark those reported since their last visit.
  assert.match(html, /Another headline\?/);
  assert.match(html, /<tr[^>]*data-first="2019-05-03"/);
  const feed = page("changes/topic/gum-disease.xml");
  assert.match(feed, /<feed xmlns="http:\/\/www\.w3\.org\/2005\/Atom">/);
  // The fixture's one moving claim changed twice after its first status.
  assert.equal(count(feed, "<entry>"), 3);
});

test("Scenario: Ways to keep up", () => {
  const html = page("how-it-works/index.html");
  assert.match(html, /<a href="#ways-to-keep-up">Ways to keep up<\/a>/);
  const section = html.slice(html.indexOf('id="ways-to-keep-up"'), html.indexOf('id="what-is-counted"'));
  for (const way of ["Follow a claim.", "Since your last visit.", "Check again later.", "Feeds.", "On your own page."]) {
    assert.ok(section.includes(way), way);
  }
  // Said plainly: none of them needs an account.
  assert.match(section, /None of these needs an account/);
});

test("Scenario: One topic", () => {
  // With a single listed topic there is nothing to choose between.
  assert.doesNotMatch(page("index.html"), /data-topic-filter/);
});

test("Scenario: Article of a published claim", () => {
  const lookup = JSON.parse(page("lookup.json"));
  // Each article address, in comparison form, names its claim.
  assert.deepEqual(lookup.articles["uk.news.example.org/3"], ["phase-claim"]);
  assert.deepEqual(lookup.articles["news.example.org/1"], ["quiet-claim"]);
  assert.deepEqual(lookup.articles["news.example.org/2"], ["quiet-claim"]);
  // Only published claims, each with the site's own wording and its page address.
  assert.deepEqual(Object.keys(lookup.claims).sort(), ["approved-claim", "phase-claim", "quiet-claim"]);
  const claim = lookup.claims["phase-claim"];
  assert.equal(claim.status, "Phase 2 trial");
  assert.equal(claim.headline, "Synthetic claim with a started trial");
  assert.equal(claim.page, "/phase-claim");
  assert.equal(claim.indication, "example condition");
  assert.match(claim.meaning, /Phase 2/);
  // The notices and the check date travel with the statuses.
  assert.equal(lookup.notices.length, 2);
  assert.match(lookup.notices[1], /not a treatment option/);
  assert.match(lookup.last_checked, /11\s+Nov\s+2026/);
  // The footer shows the same notices, from the same source.
  for (const notice of lookup.notices) assert.ok(page("index.html").includes(notice.split(". ")[0]));
});

test("Scenario: No approved claims", () => {
  // With an approved claim the page lists it; with none it says so.
  assert.ok(page("it-happened/index.html").includes('href="/approved-claim"'));
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-site-empty-"));
  const result = build("data/seed-export.json", empty);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const html = fs.readFileSync(path.join(empty, "it-happened/index.html"), "utf8");
  assert.match(html, /No tracked claim has an approval on record/);
});

test("Scenario: Preview build", () => {
  // A normal build carries no preview wording and may be indexed.
  for (const file of ["index.html", "phase-claim/index.html"]) {
    assert.doesNotMatch(page(file), /class="preview-note"|not yet been checked by a person|noindex/);
  }
  assert.equal(JSON.parse(page("lookup.json")).claims["phase-claim"].unchecked, null);

  // A preview export marks every page, and the claim no person has checked.
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  fixture.preview = true;
  fixture.claims.find((claim) => claim.slug === "phase-claim").checked_by_person = false;
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-site-preview-"));
  const exportFile = path.join(directory, "export.json");
  fs.writeFileSync(exportFile, JSON.stringify(fixture));
  const result = build(exportFile, path.join(directory, "dist"));
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const built = (file) => fs.readFileSync(path.join(directory, "dist", file), "utf8");

  for (const file of ["index.html", "quiet-claim/index.html", "topic/gum-disease/index.html"]) {
    assert.match(built(file), /class="preview-note"/, file);
    assert.match(built(file), /<meta name="robots" content="noindex"/, file);
  }
  assert.match(built("phase-claim/index.html"), /has not yet been checked by a person/);
  // The answer comes first: the notice sits under the status panel, not above it.
  const claimPage = built("phase-claim/index.html");
  assert.ok(claimPage.indexOf('class="digest"') < claimPage.indexOf('class="unchecked"'));
  assert.doesNotMatch(built("quiet-claim/index.html"), /has not yet been checked by a person/);
  const lookup = JSON.parse(built("lookup.json"));
  assert.equal(lookup.preview, true);
  assert.match(lookup.claims["phase-claim"].unchecked, /not yet been checked by a person/);
  assert.equal(lookup.claims["quiet-claim"].unchecked, null);
});

test("Scenario: Claim promised for 2025", () => {
  const html = page("quiet-claim/index.html");
  const alt = html.match(/property="og:image:alt" content="([^"]+)"/)?.[1] ?? "";
  assert.match(alt, /Promised by 2025/);
  assert.doesNotMatch(alt, /\bdays?\b/);
  assert.ok(fs.statSync(path.join(dist, "og/quiet-claim.png")).size > 10_000);
  assert.ok(html.includes("/og/quiet-claim.png"));
});

test("Scenario: Claim with no promise", () => {
  const html = page("approved-claim/index.html");
  const alt = html.match(/property="og:image:alt" content="([^"]+)"/)?.[1] ?? "";
  assert.match(alt, /Status now Approved/);
  assert.doesNotMatch(alt, /Promised by/);
});

test("Scenario: Any page", () => {
  const pages = htmlFiles(dist);
  assert.ok(pages.length >= 7);
  for (const file of pages) {
    const html = fs.readFileSync(file, "utf8");
    assert.match(html, /This site gives no medical advice/, file);
    assert.match(html, /A registered clinical trial is not a treatment option/, file);
    assert.match(html, /Data sources:/, file);
    assert.match(html, /Registries last checked 11\s+Nov\s+2026/, file);
  }
});

test("Scenario: Long-quiet claim", () => {
  const html = page("quiet-claim/index.html");
  assert.match(html, /No signal for 6 years/);
  assert.doesNotMatch(html, /\b(dead|abandoned|scam|hoax|debunked)\b/i);
});

test("Scenario: Outlet with a stored icon", () => {
  // The icon is a file of this site, written from the export; the page names no other host.
  const html = page("quiet-claim/index.html");
  const source = html.match(/<img class="tile" src="(\/outlet-icons\/news\.example\.org\.[a-f0-9]{12}\.png)" alt=""/)?.[1];
  assert.ok(source, "publisher icons carry a content revision to refresh corrected artwork");
  const icon = fs.readFileSync(path.join(dist, source));
  assert.deepEqual([...icon.subarray(0, 4)], [0x89, 0x50, 0x4e, 0x47]);
});

test("Scenario: Outlet on a subdomain", () => {
  // uk.news.example.org has no icon of its own in the export; its parent domain has.
  const html = page("phase-claim/index.html");
  assert.match(html, /<img class="tile" src="\/outlet-icons\/news\.example\.org\.[a-f0-9]{12}\.png" alt=""[^>]*>\s*<\/span>\s*<span>Example Outlet 3<\/span>\s*<\/span>\s*<span class="domain">uk\.news\.example\.org<\/span>/);
});

test("Scenario: Outlet with no stored icon", () => {
  // The fourth report's outlet has no icon in the export, so its letter tile is drawn.
  const html = page("approved-claim/index.html");
  assert.match(html, /<span class="outlet-icon" aria-hidden="true">\s*<span class="tile">O<\/span>/);
  assert.doesNotMatch(html, /<img class="tile"/);
  assert.ok(!fs.existsSync(path.join(dist, "outlet-icons/other.example.net.png")));
});

test("browser and launcher icons resolve to the current brand assets", () => {
  const html = page("index.html");
  for (const file of ["favicon.ico", "favicon.svg", "favicon-48.png", "apple-touch-icon.png", "manifest.webmanifest"]) {
    assert.match(html, new RegExp(`href="/${file.replaceAll(".", "\\.")}\\?v=[a-f0-9]{12}"`));
    assert.ok(fs.existsSync(path.join(dist, file)));
  }
  const manifest = JSON.parse(page("manifest.webmanifest"));
  for (const icon of manifest.icons) {
    const url = new URL(icon.src, "https://whatcameofit.com");
    assert.match(url.searchParams.get("v"), /^[a-f0-9]{12}$/);
    assert.ok(fs.existsSync(path.join(dist, url.pathname)));
  }
  const ico = fs.readFileSync(path.join(dist, "favicon.ico"));
  assert.equal(ico.readUInt16LE(2), 1);
  assert.equal(ico.readUInt16LE(4), 3);
  for (const [i, size] of [16, 32, 48].entries()) {
    const entry = 6 + i * 16;
    assert.equal(ico[entry], size);
    assert.equal(ico[entry + 1], size);
    const start = ico.readUInt32LE(entry + 12);
    const length = ico.readUInt32LE(entry + 8);
    assert.ok(start + length <= ico.length);
    assert.equal(ico.readUInt32BE(start + 16), size, "PNG width matches the ICO frame");
    assert.equal(ico.readUInt32BE(start + 20), size, "PNG height matches the ICO frame");
  }
});

test("Scenario: Offline build", () => {
  // The build above read one local file. The pages must also ask the network for
  // nothing but the links a reader chooses to follow.
  for (const file of htmlFiles(dist)) {
    const html = fs.readFileSync(file, "utf8");
    // A page's own canonical address and its alternates (the oEmbed description, which
    // another site fetches, not the reader's browser) are the absolute addresses it may state.
    assert.doesNotMatch(
      html,
      /<(script|link|img)(?![^>]*\brel="(canonical|alternate)")[^>]+(src|href)="https?:\/\//,
      file,
    );
  }
});

test("an export that does not match the schema stops the build", () => {
  const broken = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bad-")), "export.json");
  fs.writeFileSync(broken, JSON.stringify({ schema_version: 2, claims: "not a list" }));
  const result = build(broken, fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-site-bad-")));
  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /does not match export\.schema\.json/);
});

test("an export from pipeline code older than the audit hold stops the build", () => {
  // Version 1 exporters do not know which claims await audit, so they would publish them.
  const fixture = JSON.parse(fs.readFileSync(new URL("./fixture-export.json", import.meta.url), "utf8"));
  const old = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-old-")), "export.json");
  fs.writeFileSync(old, JSON.stringify({ ...fixture, schema_version: 1 }));
  const result = build(old, fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-site-old-")));
  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /has schema version 1; this site reads version 2/);
});

test("Scenario: Claim with an approach", () => {
  const html = page("phase-claim/index.html");
  assert.match(html, /<span class="approach"><span class="visually-hidden">Approach: <\/span>Gene therapy<\/span>/);
});

test("Scenario: Claim without an approach", () => {
  assert.ok(!page("quiet-claim/index.html").includes('class="approach"'));
});

test("Scenario: Approach code without site wording", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  fixture.claims[1].approach = "miracle";
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-approach-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));

  const result = build(file, path.join(directory, "dist"));

  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /approaches the site has no words for: miracle/);
});

test("Scenario: Empty group", () => {
  const html = page("topics/index.html");
  assert.ok(html.includes("Mouth and teeth"));
  assert.ok(!html.includes("Empty topic"));
});

// Change plain-claim-lists: name-led rows, a plain gloss per status, a topic summary.
const { STATUS_GLOSSES, assertNeutral, topicSummary } = await import("../src/lib/status.ts");

test("Scenario: Row for a named intervention", () => {
  const html = page("topic/gum-disease/index.html");
  assert.match(html, /<a class="claim-name" href="\/phase-claim"[^>]*>phase-claim agent<\/a>/);
  assert.match(html, /<span class="claim-headline"[^>]*>Synthetic claim with a started trial<\/span>/);
  // The home page's list of claims is led by the name too.
  assert.match(page("index.html"), /<a class="claim-name" href="\/[^"]+"[^>]*>[^<]+ agent<\/a>/);
});

test("Scenario: Two claims for one intervention", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  for (const claim of fixture.claims) claim.intervention.name = "Shared agent";
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-shared-")), "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-site-shared-"));
  const result = build(file, out);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const html = fs.readFileSync(path.join(out, "topic/gum-disease/index.html"), "utf8");
  assert.equal(count(html, ">Shared agent</a>"), 3);
  for (const headline of ["that went quiet", "with a started trial", "that was approved"]) {
    assert.ok(html.includes(`>Synthetic claim ${headline}</span>`), headline);
  }
});

test("Scenario: Gloss in a list", () => {
  const html = page("topic/gum-disease/index.html");
  assert.match(html, /Phase 2 trial<\/strong>\s*<\/span>\s*<span class="gloss"[^>]*>Mid-stage trial in people</);
});

test("Scenario: Gloss on the claim page", () => {
  const html = page("quiet-claim/index.html");
  assert.match(html, /Preclinical only/);
  assert.match(html, /<p class="gloss"[^>]*>No trial in people on record<\/p>/);
  assert.match(html, /No clinical trial was found in the registries checked/);
});

test("Scenario: Status code without a gloss", () => {
  const schema = JSON.parse(fs.readFileSync("export.schema.json", "utf8"));
  for (const code of schema.$defs.ClaimStatus.enum) {
    assert.ok(STATUS_GLOSSES[code], `${code} has no gloss`);
    // A gloss is for a reader who does not know the phases, so it does not name one.
    assert.doesNotMatch(STATUS_GLOSSES[code], /phase|preclinical|endpoint/i, code);
  }
});

test("Scenario: Gloss with verdict wording", () => {
  assert.throws(() => assertNeutral(["Its trials were abandoned"]), /"Its trials were abandoned"/);
});

const tally = (pairs) => new Map(Object.entries(pairs));

test("Scenario: Topic with two statuses", () => {
  assert.equal(
    topicSummary(tally({ phase_3: 2, preclinical_only: 5 })),
    "Of 7 reported breakthroughs tracked, 5 have no trial in people on record and 2 have reached large late-stage trials in people.",
  );
  // The built page opens with the sentence for its own three claims.
  assert.match(
    page("topic/gum-disease/index.html"),
    /Of 3 reported breakthroughs tracked, 1 has no trial in people on record, 1 has reached a mid-stage trial in people and 1 has been approved by a regulator\./,
  );
});

test("Scenario: Topic with one claim", () => {
  assert.equal(
    topicSummary(tally({ phase_1: 1 })),
    "1 reported breakthrough tracked: it has reached an early trial in people.",
  );
});

test("Scenario: Topic with more than four statuses", () => {
  const said = topicSummary(
    tally({ retracted: 1, approved: 2, phase_3: 3, phase_1: 1, trial_registered: 4, preclinical_only: 6 }),
  );
  assert.equal(
    said,
    "Of 17 reported breakthroughs tracked, 6 have no trial in people on record, 4 have a trial in people registered, 3 have reached large late-stage trials in people, 2 have been approved by a regulator and 2 are at other statuses.",
  );
});

test("Scenario: Summary of a topic with ended trials", () => {
  const said = topicSummary(tally({ terminated: 1, preclinical_only: 2 }));
  assert.match(said, /1 had its trials stopped early\.$/);
  assert.doesNotThrow(() => assertNeutral([said]));
  assert.equal(topicSummary(new Map()), null);
});

test("Scenario: Reader follows a headline from the home page", () => {
  const home = page("index.html");
  // Each headline on the home page is named, and its claim page gives the same name
  // to the same headline, shown before the status.
  const named = [...home.matchAll(/class="followed" href="\/([^"]+)" style="view-transition-name: ([^";]+)/g)];
  assert.ok(named.length > 0, "no headline on the home page is named");
  assert.equal(new Set(named.map(([, , name]) => name)).size, named.length, "a name is used twice");
  for (const [, slug, name] of named) {
    const html = page(`${slug}/index.html`);
    const at = html.indexOf(`view-transition-name: ${name}`);
    assert.ok(at > 0, `${slug} does not name its report ${name}`);
    assert.ok(at < html.indexOf('class="digest"'), `${slug} names its report after the status`);
  }
});

// Openspec trial-facts: each trial once, with what its registry record states.
// A section runs from its heading to the next section heading.
function sectionOf(html, id) {
  const start = html.indexOf(`id="${id}"`);
  assert.ok(start > 0, `no section with id ${id}`);
  const next = html.indexOf('<h2 class="bar"', start);
  return html.slice(start, next > 0 ? next : undefined);
}

// What a reader reads of a section: no markup, so a drawing's attributes are not words.
const wordsOf = (html) => html.replace(/<[^>]*>/g, " ").replace(/&#39;/g, "'").replace(/\s+/g, " ");

test("Scenario: Claim with one completed Phase 2 trial", () => {
  const html = page("phase-claim/index.html");
  assert.equal(count(html, 'id="trial-NCT00000002"'), 1);
  const trials = sectionOf(html, "trials");
  const entry = wordsOf(trials.slice(trials.indexOf('id="trial-NCT00000002"'))).replace(/\u00a0|&nbsp;/g, " ");
  // A row to read across: how many people and the phase, then what it was compared
  // with, its design, its state and its results, each under its column's name.
  assert.match(entry, /83 people\s+Phase 2 · /);
  assert.match(
    entry,
    /Compared with\s*A placebo\s+Design\s*Assigned at random · Blinded\s+State\s*Finished\s+Results\s*Posted 1 Sep 2025/,
  );
  // The row opens to what it measured.
  assert.match(entry, /It measured the change in a symptom score over 12 weeks\./);
  assert.match(entry, /What it measured was read by a model and checked against the record/);
  // The registry's own terms are inside the fold.
  assert.match(entry, /Design, in the registry's terms\s+Randomised, double-blind, compared with placebo/);
  assert.match(trials, /Change in synthetic score/);
  // Posted results are a table: a row for each group, the registry's numbers.
  const table = trials.match(/<table class="result-table"[\s\S]*?<\/table>/)[0];
  assert.match(wordsOf(table), /Group\s+Mean\s+Standard Deviation\s+People analysed/);
  assert.match(wordsOf(table), /3\.4\s+Standard Deviation 1\.1\s+1\.1\s+41/);
  assert.match(trials, /The registry record says what this measure runs from and to/);
  assert.match(trials, /High match · 94%/);
  // Three of five planned measures are shown, and the page says where the rest are.
  assert.match(trials, /2 more in the ClinicalTrials\.gov record/);
});

test("Scenario: Record read on 3 October 2026", () => {
  const trials = wordsOf(sectionOf(page("phase-claim/index.html"), "trials"));
  assert.match(trials, /record read[\s\S]{0,80}3\s+Oct\s+2026/);
  assert.match(trials, /a selection, unaltered, from the trial's registry record/);
});

test("Scenario: Reader follows a timetable entry", () => {
  const html = page("phase-claim/index.html");
  const timetable = sectionOf(html, "timetable");
  assert.ok(timetable.includes('href="#trial-NCT00000002"'), "no timetable entry leads to its trial");
});

test("Scenario: Claim with no trial", () => {
  const html = page("quiet-claim/index.html");
  assert.ok(!html.includes('id="trials"'));
  assert.ok(!html.includes("Trials in people"));
});

test("Scenario: Claim with thirty-three trials", () => {
  // Seven here: five shown, furthest phase first, the other two one press away.
  const trials = sectionOf(page("phase-claim/index.html"), "trials");
  const [shown, rest] = trials.split('class="trials-rest"');
  assert.equal(count(shown, 'class="trial-group"'), 5);
  assert.equal(count(rest, 'class="trial-group"'), 2);
  assert.ok(shown.indexOf("NCT00000030") < shown.indexOf("NCT00000002"), "Phase 3 is not first");
  assert.match(rest, /The other 2 of 7 trials/);
});

// Openspec site-publishing (change claim-at-a-glance): "The record in brief". The rules
// are tested in record-brief.test.mjs; these read the built page.
const briefOf = (slug) => wordsOf(sectionOf(page(`${slug}/index.html`), "brief")).replace(/\u00a0|&nbsp;/g, " ");

test("Scenario: Three trials, the largest of 1,200", () => {
  const html = page("phase-claim/index.html");
  // Said once, in the section: the facts under the digest no longer count the trials.
  assert.match(briefOf("phase-claim"), /Tested in people\? In 7 trials\. 1,200 people in the largest/);
  assert.match(briefOf("phase-claim"), /The largest number is a planned size, not people who took part\./);
  assert.doesNotMatch(html, /Trials in people/);
  assert.doesNotMatch(html, /7 on record/);
});

test("Scenario: Claim with trials", () => {
  const brief = briefOf("phase-claim");
  assert.match(brief, /The record in brief/);
  assert.match(brief, /describe the records, not the treatment, and are not advice/);
  assert.ok(brief.indexOf("How it was tested") < brief.indexOf("Where the records stand now"));
  assert.match(brief, /Compared with a placebo\? One record names a placebo/);
  assert.match(brief, /Results posted to the registry\? By 1 of 7 trials\. Posted on 1 Sep 2025/);
  assert.match(brief, /A trial under way\? One under way/);
  assert.match(brief, /Approved by a regulator\? None on record/);
  // The largest trial states no main measure, so that question has nothing to ask.
  assert.doesNotMatch(brief, /What did the largest trial measure/);
});

test("Scenario: Every answer opens to something", () => {
  for (const slug of ["phase-claim", "quiet-claim", "approved-claim"]) {
    const section = sectionOf(page(`${slug}/index.html`), "brief");
    const answers = count(section, "<details");
    assert.ok(answers >= 3, `${slug} has ${answers} answers`);
    assert.equal(count(section, 'class="brief-source"'), answers);
    // Closed until opened, and opened by the browser alone.
    assert.equal(count(section, "<details open"), 0);
    // The heading folds the section with a button; the answers themselves need none.
    const answersOnly = section.slice(section.indexOf("</h2>"));
    assert.doesNotMatch(answersOnly, /<script|<button/);
  }
});

test("Scenario: Results posted", () => {
  const section = sectionOf(page("phase-claim/index.html"), "brief");
  // Outside the disclosure, so it shows without opening the answer.
  assert.match(section, /<\/details>\s*<p class="brief-link brief-shown">\s*<a href="#trials">\s*See the posted results/);
});

test("Scenario: Largest trial with posted values", () => {
  const brief = briefOf("phase-claim");
  // The trial entries below carry "p = 0.03"; the section carries no result value.
  assert.doesNotMatch(brief, /p\s*[=<]|\d\.\d/);
});

test("Scenario: Claim with no trial on record", () => {
  const brief = briefOf("quiet-claim");
  assert.match(brief, /Tested in people\? None on record/);
  assert.match(brief, /What was the first report about\? A study in animals/);
  assert.match(brief, /Approved by a regulator\? None on record/);
  assert.doesNotMatch(brief, /Compared with|Results posted|A trial under way/);
  assert.match(brief, /Three answers read from the records on this page/);
});

test("Scenario: Approved claim", () => {
  const brief = briefOf("approved-claim");
  assert.match(brief, /Approved by a regulator\? On 1 Apr 2024\. An approval is not advice to take a treatment/);
});

test("Scenario: Status with a phase", () => {
  assert.doesNotMatch(page("phase-claim/index.html"), /class="bridge"/);
});

test("Scenario: Narrow screen", () => {
  const styles = fs
    .readdirSync(path.join(dist, "_astro"))
    .filter((name) => name.endsWith(".css"))
    .map((name) => fs.readFileSync(path.join(dist, "_astro", name), "utf8"))
    .join("");
  // Under 40rem a row, and a link on a line of its own, is 44 pixels tall at least.
  assert.match(styles, /\.brief summary\{[^}]*min-height:2\.75rem/);
  assert.match(styles, /\.brief-link a\{[^}]*min-height:2\.75rem/);
});

test("Scenario: Narrow screen, a trial's results", () => {
  const styles = fs
    .readdirSync(path.join(dist, "_astro"))
    .filter((name) => name.endsWith(".css"))
    .map((name) => fs.readFileSync(path.join(dist, "_astro", name), "utf8"))
    .join("");
  // Under 40rem the spread leaves its column and sits under its value, so the table
  // keeps three columns; the links on lines of their own are 44 pixels tall.
  assert.match(styles, /\.result-table \.spread\{display:none\}/);
  assert.match(styles, /\.result-table \.spread-inline\{[^}]*display:block/);
  assert.match(styles, /\.trial-name a\{[^}]*min-height:2\.75rem/);
  assert.match(styles, /\.result-scale a\{[^}]*min-height:2\.75rem/);
});

test("Scenario: Posted comparison with a p value", () => {
  const trials = wordsOf(sectionOf(page("phase-claim/index.html"), "trials"));
  assert.match(trials, /p = 0\.03, t-test, 2 sided \(superiority test\)/);
  assert.match(trials, /numbers the trial's sponsor posted to the registry/);
  // The numbers are shown; nothing says what they mean for the treatment.
  assert.doesNotMatch(trials, /\b(met|missed|significan\w*|success\w*|fail\w*|worked|proven)\b/i);
});

test("Scenario: Outcome reported at four time points", () => {
  const trials = sectionOf(page("phase-claim/index.html"), "trials");
  assert.match(trials, /Posted in 4 rows of values/);
});

test("Scenario: Trial the registry shows as recruiting", () => {
  const trials = wordsOf(sectionOf(page("phase-claim/index.html"), "trials"));
  assert.match(trials, /1,200 people planned\s+Phase 3 · /);
  assert.match(trials, /State\s*Under way/);
  assert.doesNotMatch(trials, /recruit|eligib|contact|location|take part|join/i);
});

test("Scenario: Sponsor who is a person", () => {
  const trials = sectionOf(page("phase-claim/index.html"), "trials");
  assert.match(trials, /An individual researcher/);
});

test("Scenario: Claim with one matched paper and no trial", () => {
  const html = page("quiet-claim/index.html");
  const papers = sectionOf(html, "papers");
  assert.match(papers, /Matched papers/);
  assert.ok(papers.includes("10.5555/synthetic.1"));
  assert.match(papers, /A paper is not a trial\s+record/);
  assert.match(html, /No registry record matched/);
  const registry = sectionOf(html, "matched");
  assert.match(registry, /No record matched/);
  assert.ok(!registry.includes("10.5555/synthetic.1"), "a paper is listed as a registry record");
});

// Openspec paper-facts: each paper once, with what its index record states.
test("Scenario: Claim with an origin paper and two results papers", () => {
  const html = page("phase-claim/index.html");
  const papers = sectionOf(html, "papers");
  assert.match(papers, /Papers on record/);
  assert.equal(count(papers, 'class="paper"'), 5);
  for (const heading of ["The paper first reported", "Papers named by a trial&#39;s registry record", "Follow-up papers", "Related research"]) {
    assert.ok(papers.includes(heading), `no group "${heading}"`);
  }
  assert.ok(papers.indexOf("The paper first reported") < papers.indexOf("Follow-up papers"));
  const words = wordsOf(papers);
  assert.match(words, /Report of a randomised trial · Journal of Synthetic Trials · 2023/);
  assert.match(words, /A paper is not a trial record and does not set the status/);
  assert.ok(!html.includes("Matched papers"));
});

test("Scenario: Paper with two roles", () => {
  const html = page("phase-claim/index.html");
  assert.equal(count(html, 'id="paper-10-5555-synthetic-origin"'), 1);
  const [origin] = sectionOf(html, "papers").split("Papers named by a trial");
  assert.ok(origin.includes('id="paper-10-5555-synthetic-origin"'), "not in the origin paper's group");
  assert.match(wordsOf(origin), /Linked by the registry from PubMed to NCT00000002/);
});

test("Scenario: Reader goes from a trial to its paper", () => {
  const html = page("phase-claim/index.html");
  const trials = sectionOf(html, "trials");
  assert.ok(trials.includes('href="#paper-10-5555-synthetic-origin"'), "the trial does not lead to its papers");
  assert.match(wordsOf(trials), /2 papers named by its record/);
  const papers = sectionOf(html, "papers");
  assert.ok(papers.includes('href="#trial-NCT00000002"'), "the paper does not lead back to its trial");
  assert.match(wordsOf(papers), /Listed by the sponsor as reporting results of NCT00000002/);
  assert.match(wordsOf(papers), /may or may not be about the study/);
});

test("Scenario: Paper of a study in mice, retracted follow-up paper, record read on 3 October 2026", () => {
  const papers = wordsOf(sectionOf(page("phase-claim/index.html"), "papers"));
  assert.match(papers, /Europe PMC subject headings: animals\./);
  assert.match(papers, /This paper has been retracted/);
  assert.match(papers, /Europe PMC record\s+read\s+3\s+Oct\s+2026/);
  // A paper the index does not hold is listed by its number, with no facts.
  assert.match(papers, /PubMed 90000003/);
  assert.match(papers, /No Europe PMC details are available here/);
  assert.doesNotMatch(papers, /holds no record of it/);
  // The preprint's record states neither people nor animals, so its entry says neither.
  const preprint = papers.slice(papers.indexOf("A synthetic preprint on the compound"));
  assert.doesNotMatch(preprint, /subject headings:/);
});

test("related papers are shown as a group of the papers on record, with score and reasons", () => {
  const papers = wordsOf(sectionOf(page("phase-claim/index.html"), "papers"));
  const related = papers.slice(papers.indexOf("Related research"));
  assert.match(related, /Match to this claim: high, 86%/);
  assert.match(related, /Names the treatment in its title · Names the condition/);
  assert.match(related, /A score is about the match, not about the treatment/);
  assert.doesNotMatch(papers, /\b(supports?|confirms?|proves?|refutes?)\b/i);
});

test("Scenario: Claim with three trials and one mouse paper", () => {
  // Subject headings do not turn papers into additional trial records.
  const html = wordsOf(page("phase-claim/index.html"));
  assert.match(html, /Records listed\s+7 trial records · 5 papers/);
});

test("Scenario: Claim with no paper", () => {
  const html = page("approved-claim/index.html");
  assert.ok(!html.includes('id="papers"'));
  assert.ok(!html.includes("Papers on record"));
  assert.ok(!html.includes("Records listed"));
});

test("Scenario: Kind code without site wording", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  fixture.claims[1].papers[0].facts.kinds = ["hologram"];
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-paper-code-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));

  const result = build(file, path.join(directory, "dist"));

  assert.notEqual(result.status, 0);
});

test("the build fails on a related paper's reason the site has no wording for", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  fixture.claims[1].papers.at(-1).roles[0].reasons = ["liked_it"];
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-paper-reason-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));

  const result = build(file, path.join(directory, "dist"));

  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /paper reason: liked_it/);
});

test("an export made before paper facts still builds, with the matched papers as before", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  for (const claim of fixture.claims) {
    delete claim.papers;
    for (const trial of claim.trials ?? []) delete trial.papers;
  }
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-no-papers-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));
  const out = path.join(directory, "dist");

  const result = build(file, out);

  assert.equal(result.status, 0, result.stdout + result.stderr);
  const quiet = fs.readFileSync(path.join(out, "quiet-claim/index.html"), "utf8");
  assert.match(sectionOf(quiet, "papers"), /Matched papers/);
  const phase = fs.readFileSync(path.join(out, "phase-claim/index.html"), "utf8");
  assert.ok(!phase.includes("Papers on record"));
  assert.ok(!phase.includes("Records listed"));
});

test("Scenario: Follow-up paper scored 0.6", () => {
  const timetable = sectionOf(page("phase-claim/index.html"), "timetable");
  assert.match(timetable, /Medium match · 60%/);
});

test("Scenario: Trial event read from a registry record", () => {
  const timetable = sectionOf(page("phase-claim/index.html"), "timetable");
  assert.doesNotMatch(timetable, /match · 100%/);
});

test("Scenario: Fact code without site wording", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  fixture.claims[1].trials[0].facts.masking = "sextuple";
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-trial-code-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));

  const result = build(file, path.join(directory, "dist"));

  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /masking/);
});

test("an export made before trial facts still builds, with the matched records as before", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  for (const claim of fixture.claims) {
    delete claim.trials;
    for (const event of claim.events) delete event.confidence;
  }
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-no-trials-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));
  const out = path.join(directory, "dist");

  const result = build(file, out);

  assert.equal(result.status, 0, result.stdout + result.stderr);
  const html = fs.readFileSync(path.join(out, "phase-claim/index.html"), "utf8");
  assert.ok(!html.includes('id="trials"'));
  const registry = sectionOf(html, "matched");
  assert.match(registry, /Matched registry records/);
  assert.ok(registry.includes("NCT00000002"));
  assert.match(registry, /Match to this claim: high, 94%/);
});

// --- registry record rows (openspec registry-record-rows) ---

test("Scenario: Possible record laid out field by field under its reading", () => {
  const html = page("phase-claim/index.html");
  const registry = sectionOf(html, "matched");
  const words = wordsOf(registry);
  // Said once, with the rule that would have counted it and where scoring is explained.
  assert.equal(count(words, "None of these is counted in the status"), 1);
  assert.match(words, /None of these is counted in the status, and no person has checked them\. A record counts only when it is read as this treatment for this condition and its match is 80% or more\./);
  assert.match(registry, /<a href="\/guide\/match-and-confidence">How a match is scored<\/a>/);
  assert.match(registry, /<h3 class="record-group-head">\s*Read as this treatment for another condition, patient group or setting/);
  assert.match(registry, /<p class="record-title">Synthetic trial of phase-claim agent in another condition<\/p>/);
  // The line leads with the match, then the trials table's words; then the record and its
  // page here, as a trial entry names them.
  assert.match(words, /Possible match: low, 31% Phase 1 120 people planned Under way NCT00000077 at ClinicalTrials\.gov View trial details here/);
  assert.match(words, /For Another Condition Named in the record Phase-claim agent; Placebo/);
  assert.doesNotMatch(words, /Recruiting|Tests|Match to this claim/);
  // The folded heading and the digest give the count; the digest's links to the section.
  assert.match(html, /<span class="fold-note">1 possible<\/span>/);
  assert.match(html, /, <a href="#matched">1 possible<\/a>/);
});

test("Scenario: Trial on ClinicalTrials.gov", () => {
  const trials = wordsOf(sectionOf(page("phase-claim/index.html"), "trials"));
  assert.match(trials, /NCT00000002 at ClinicalTrials\.gov/);
});

test("Scenario: Possible records when only a person approves a match", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  fixture.match_accept_above = null;
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-record-person-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));
  const out = path.join(directory, "dist");

  const result = build(file, out);

  assert.equal(result.status, 0, result.stdout + result.stderr);
  const words = wordsOf(sectionOf(fs.readFileSync(path.join(out, "phase-claim/index.html"), "utf8"), "matched"));
  assert.match(words, /A record counts only once a person confirms it\./);
  assert.doesNotMatch(words, /% or more/);
});

test("Scenario: Group of more than three records", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  const claim = fixture.claims.find((each) => each.slug === "phase-claim");
  const candidate = claim.matches[1];
  for (let n = 0; n < 4; n += 1) {
    claim.matches.push({ ...candidate, external_id: `NCT0000009${n}`, url: `https://clinicaltrials.gov/study/NCT0000009${n}`, score: 0.3 - n / 100 });
  }
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-record-rest-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));
  const out = path.join(directory, "dist");

  const result = build(file, out);

  assert.equal(result.status, 0, result.stdout + result.stderr);
  const registry = sectionOf(fs.readFileSync(path.join(out, "phase-claim/index.html"), "utf8"), "matched");
  const [shown, rest] = registry.split('<details class="papers-rest record-rest">');
  assert.equal(count(shown, 'class="record-row"'), 3);
  assert.equal(count(rest, 'class="record-row"'), 2);
  assert.match(wordsOf(rest), /The other 2 of 5 records/);
});

test("Scenario: Possible record not yet read into fields", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  const claim = fixture.claims.find((each) => each.slug === "phase-claim");
  claim.matches[1].record = null;
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-record-unread-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));
  const out = path.join(directory, "dist");

  const result = build(file, out);

  assert.equal(result.status, 0, result.stdout + result.stderr);
  const words = wordsOf(sectionOf(fs.readFileSync(path.join(out, "phase-claim/index.html"), "utf8"), "matched"));
  assert.match(words, /Registry record NCT00000077 Possible match: low, 31% Details not read from the registry yet NCT00000077 at ClinicalTrials\.gov/);
  assert.doesNotMatch(words, /Synthetic trial of phase-claim agent in another condition/);
});

// --- background cards (openspec knowledge-cards, site-publishing) ---

const backgroundOf = (html) => html.match(/<section class="glance"[\s\S]*?<\/section>/)?.[0];
const bandRowOf = (html) => html.match(/<nav class="glance-band"[\s\S]*?<\/nav>/)?.[0];

test("Scenario: Claim with a condition card only", () => {
  const html = page("approved-claim/index.html");
  const section = backgroundOf(html);
  assert.ok(section, "no glance section");
  assert.equal(count(section, 'class="card-kind"'), 1);
  assert.match(section, /The condition/);
  assert.match(section, /href="https:\/\/vocabulary\.example\/D900003"[^>]*>\s*Example Condition\s*</);
  // The card is one press away in its row, its score in sight on the summary; inside,
  // the definition is marked as the source's words and unchanged.
  assert.match(section, /<details class="glance-more">\s*<summary>\s*<span class="glance-more-label">\s*<span class="glance-more-words">Source and definition<\/span>\s*<span class="visually-hidden"> for example condition<\/span>[\s\S]*?<span class="glance-score">Term match: high, \d+%<\/span>/);
  assert.match(section, /<div class="card-words">[\s\S]*Definition, in the source’s words/);
  assert.match(section, /<blockquote[^>]*>A synthetic definition of the example condition\.<\/blockquote>/);
  assert.match(section, /When this term was gathered, the trial registry filed the claim’s one trial under it\./);
  // In its row, under the condition's own words.
  assert.match(section, /<div id="glance-condition" tabindex="-1">\s*<dt>Claimed for<\/dt>/);
  // At the top of the sheet, before the record in brief, and not inside the status panel.
  assert.ok(html.indexOf('id="glance"') < html.indexOf('id="brief"'));
  assert.ok(html.indexOf('id="glance"') < html.indexOf('id="timetable"'));
  const digest = html.slice(html.indexOf('class="digest"'), html.indexOf('class="glance"'));
  assert.ok(!digest.includes("card-kind") && !digest.includes("glance-"));
  // A condition card alone adds nothing the headline does not say: no row in the band.
  assert.ok(!bandRowOf(html));
});

test("Scenario: Claim with no card", () => {
  const html = page("quiet-claim/index.html");
  // The claim's own facts still open the sheet, with no card, no note on cards and no
  // row in the band.
  assert.ok(backgroundOf(html), "no glance section");
  assert.ok(!html.includes('class="term-card"'));
  assert.ok(!html.includes('class="glance-note"'));
  assert.ok(!bandRowOf(html));
});

test("Scenario: Broader term, and Reason shown on request", () => {
  const section = backgroundOf(page("phase-claim/index.html"));
  assert.equal(count(section, 'class="card-kind"'), 2);
  assert.match(section, /A broader term than this claim’s condition/);
  assert.match(section, /Match to this claim: high, 90%/);
  assert.match(section, /When this term was gathered, the trial registry filed 5 of the claim’s 6 trials under it\./);
  assert.match(section, /The term’s label is the same as “examplumab”, a name this claim uses\./);
  // A term its source gives no definition says so in place of the source's words.
  assert.equal(count(section, '<div class="card-words">'), 1);
  assert.match(section, /The source gives this term no definition\./);
});

test("Scenario: Definition in the vocabulary's style, and Vocabulary that asks for its version to be stated", () => {
  const section = backgroundOf(page("phase-claim/index.html"));
  assert.match(section, /A synthetic definition with CAPITALISED CROSS-REFERENCES, as the vocabulary writes them\./);
  assert.match(
    section,
    /Medical Subject Headings \(MeSH\), U\.S\. National Library of Medicine, 2026 edition\s*<\/a>\s*\. Record read 14 November 2026\./,
  );
  // The section's note: terms, not evidence, not advice, no endorsement, with the method.
  assert.match(section, /They are not about this claim’s evidence and they are not medical advice/);
  assert.match(section, /naming a source does not mean it endorses this site/);
  assert.match(section, /href="\/how-it-works#background-on-a-claims-terms">How these terms are chosen</);
});

test("Scenario: Card for a drug class with approved uses", () => {
  // The background section is never inside or beside the status.
  const html = page("phase-claim/index.html");
  const digest = html.match(/<section class="reported[^"]*"[\s\S]*?<\/section>/)[0];
  assert.ok(!digest.includes("card-kind") && !digest.includes("Background"));
});

test("the footer's data sources include each source a card comes from", () => {
  for (const file of ["index.html", "quiet-claim/index.html"]) {
    const footer = page(file).split("Data sources:")[1].split("</p>")[0];
    assert.match(footer, /href="https:\/\/www\.nlm\.nih\.gov\/mesh\/meshhome\.html"[^>]*>Medical Subject Headings \(MeSH\)</);
  }
});

test("the method page explains background cards", () => {
  const html = page("how-it-works/index.html");
  const part = html.split('id="background-on-a-claims-terms"')[1].split('id="what-this-site-never-says"')[0];
  assert.match(part, /vocabulary publisher’s, shown unchanged/);
  assert.match(part, /at least half of the\s+claim’s trials/);
  assert.match(part, /An AI model then\s+reads each candidate/);
  assert.match(part, /it never changes a status, and it\s+is not medical advice/);
});

test("Scenario: Code without site wording", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  fixture.claims.find((claim) => claim.slug === "phase-claim").background[0].reasons[0].code = "sounds_right";
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-card-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));

  const result = build(file, path.join(directory, "dist"));

  assert.notEqual(result.status, 0);
  assert.match(
    result.stdout + result.stderr,
    /background card codes the site has no words for: card reason: sounds_right/,
  );
});

test("Scenarios: Kind card, and Registry type as a reason", () => {
  // The same site, built from the fixture with a kind link's card added to one claim.
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  const claim = fixture.claims.find((claim) => claim.slug === "approved-claim");
  claim.background.push({
    kind: "intervention",
    fit: "kind",
    label: "Example Stimulation Therapy",
    definition: "A synthetic definition of a KIND OF TREATMENT, as the vocabulary writes it.",
    url: "https://vocabulary.example/D900009",
    source: "mesh",
    external_id: "D900009",
    version: "2026",
    score: 0.9,
    reasons: [
      { code: "kind_chosen", kind: "electrical_stimulation" },
      { code: "registry_lists_type", type: "DEVICE", trials: 3 },
    ],
    decided_by: "rule",
    read_at: "2026-11-14T09:00:00Z",
  });
  // And a target card from a gene named in the treatment's name, with its two sources.
  claim.background.push({
    kind: "target",
    fit: "exact",
    label: "EXG1",
    name: "example gene 1 receptor",
    definition: "[Isoform 1]: A synthetic description of what the product does (PubMed:1).",
    definition_source: "uniprot",
    url: "https://targets.example/target/ENSG00000000001",
    source: "opentargets",
    external_id: "ENSG00000000001",
    version: null,
    score: 0.95,
    reasons: [{ code: "word_equals_synonym", word: "EX-1", sources: ["uniprot", "HGNC"] }],
    decided_by: "rule",
    read_at: "2026-11-14T09:00:00Z",
  });
  const source = (name, title, credit, licence, url) => ({
    name,
    title,
    credit,
    licence,
    url,
    terms_url: `${url}terms`,
    in_data_file: true,
  });
  const cited = "Example Targets: Author, A. et al. (2025), “A synthetic citation”, A Journal";
  fixture.card_sources.push(
    source("opentargets", "Example Targets", cited, "CC0 1.0", "https://targets.example/"),
    source("uniprot", "Example Proteins", "Example Proteins Consortium", "CC BY 4.0", "https://proteins.example/"),
  );
  fixture.sources.push(
    { name: "Example Targets", url: "https://targets.example/" },
    { name: "Example Proteins", url: "https://proteins.example/" },
  );
  // And, on another claim, a drug card with the target its record names.
  const named = fixture.claims.find((claim) => claim.slug === "phase-claim");
  // With a kind card too, which goes inside the drug's row and not in a row of its own.
  named.background.push({ ...claim.background.find((card) => card.fit === "kind") });
  named.background.push(
    {
      kind: "drug",
      fit: "exact",
      label: "EXAMPLUMAB",
      definition: null,
      url: "https://targets.example/drug/CHEMBL0000001",
      source: "opentargets",
      external_id: "CHEMBL0000001",
      version: null,
      score: null,
      molecule_kind: "antibody",
      mechanisms: [{ action: "inhibitor", target: "Example receptor 1" }],
      facts_source: "chembl",
      reasons: [{ code: "drug_name_equals_name", name: "examplumab" }],
      decided_by: "rule",
      read_at: "2026-11-14T09:00:00Z",
    },
    {
      kind: "target",
      fit: "exact",
      label: "EXR1",
      name: "example receptor 1",
      definition: "A synthetic description of the receptor.",
      definition_source: "uniprot",
      url: "https://targets.example/target/ENSG00000000002",
      source: "opentargets",
      external_id: "ENSG00000000002",
      version: null,
      score: null,
      facts_source: "chembl",
      reasons: [{ code: "drug_record_names_target", name: "EXAMPLUMAB" }],
      decided_by: "rule",
      read_at: "2026-11-14T09:00:00Z",
    },
  );
  fixture.card_sources.push({
    ...source("chembl", "Example Drugs", "Example Drugs, An Institute", "CC BY-SA 3.0 Unported", "https://drugs.example/"),
    in_data_file: false,
  });
  fixture.sources.push({ name: "Example Drugs", url: "https://drugs.example/" });
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-kind-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));
  const dist = path.join(directory, "dist");

  const result = build(file, dist);

  assert.equal(result.status, 0, result.stdout + result.stderr);
  const built = fs.readFileSync(path.join(dist, "approved-claim/index.html"), "utf8");
  const section = backgroundOf(built);
  assert.equal(count(section, 'class="card-kind"'), 3);
  // Scenario: Device with a kind card. The band names the kind and the gene, each a link
  // down to its row, with no score beside the status; the rows carry the scores.
  const row = bandRowOf(built);
  assert.match(row, /href="#glance-kind">\s*<span class="glance-band-label">Kind of treatment<\/span>\s*<span class="glance-band-value">\s*Example stimulation therapy/);
  assert.match(row, /href="#glance-target">\s*<span class="glance-band-label">Gene named<\/span>\s*<span class="glance-band-value">\s*EXG1/);
  assert.doesNotMatch(row, /\d+%|Treatment<|Claimed for/);
  assert.match(section, /<div id="glance-kind" tabindex="-1">\s*<dt>Kind of treatment<\/dt>\s*<dd>\s*<span class="glance-value">Example stimulation therapy<\/span>/);
  assert.match(section, /<div id="glance-target" tabindex="-1">\s*<dt>Gene named<\/dt>/);
  // Scenario: Target the report names.
  assert.match(section, /A gene named in the treatment’s name/);
  assert.match(section, /href="https:\/\/targets\.example\/target\/ENSG00000000001"[^>]*>\s*EXG1\s*</);
  assert.match(section, /example gene 1 receptor/);
  assert.match(section, /Match to this claim: high, 95%/);
  assert.match(
    section,
    /“EX-1”, a word in the treatment’s name, is another name for this gene, listed by UniProt and the HUGO Gene Nomenclature Committee\. It is not the gene’s symbol\./,
  );
  assert.match(section, /What this gene’s product does, in the source’s words/);
  assert.match(section, /<blockquote[^>]*>\[Isoform 1\]: A synthetic description of what the product does \(PubMed:1\)\.<\/blockquote>/);
  // Both sources are credited on the card: the citation asked for, and whose words.
  assert.match(section, /Author, A\. et al\. \(2025\), “A synthetic citation”, A Journal/);
  assert.match(section, /href="https:\/\/proteins\.example\/"[^>]*>\s*Description by Example Proteins Consortium, CC BY 4\.0\s*</);
  assert.match(section, /That does not say the treatment is known to work through that gene\./);
  // And in the footer's data sources.
  const footer = built.split("Data sources:")[1].split("</p>")[0];
  assert.match(footer, /href="https:\/\/targets\.example\/"[^>]*>Example Targets</);
  assert.match(footer, /href="https:\/\/proteins\.example\/"[^>]*>Example Proteins</);
  // A page with no target card does not carry the sentence about genes.
  assert.ok(!page("phase-claim/index.html").includes("known to work through that gene"));

  // The drug card and the target its record names (openspec knowledge-cards, group 6).
  const drugPage = fs.readFileSync(path.join(dist, "phase-claim/index.html"), "utf8");
  const drugs = backgroundOf(drugPage);
  assert.equal(count(drugs, 'class="card-kind"'), 5);
  // A drug's record says what kind of molecule it is: no kind of treatment row beside it,
  // and the kind card is inside the drug's row.
  assert.ok(!drugs.includes('id="glance-kind"'));
  const drugRowHtml = drugs.split('id="glance-drug"')[1].split('id="glance-target"')[0];
  assert.match(drugRowHtml, />\s*Example Stimulation Therapy\s*</);
  // A drug record's kind of molecule is the band's kind, labelled as its row is, and its
  // target is what it acts on.
  const drugRow = bandRowOf(drugPage);
  assert.match(drugRow, /href="#glance-drug">\s*<span class="glance-band-label">Kind of molecule<\/span>\s*<span class="glance-band-value">\s*Antibody/);
  assert.match(drugRow, /<span class="glance-band-label">Acts on<\/span>/);
  // Its row: the kind of molecule, what the record says it acts on, and the rule in sight.
  assert.match(drugs, /<div id="glance-drug" tabindex="-1">\s*<dt>Kind of molecule<\/dt>\s*<dd>\s*<span class="glance-value">Antibody<\/span>\s*<span class="aka">Inhibitor of Example receptor 1<\/span>/);
  assert.match(drugs, /<span class="glance-score">Term match: by exact name<\/span>/);
  assert.match(drugs, /The drug, as a drug database records it/);
  assert.match(drugs, /href="https:\/\/targets\.example\/drug\/CHEMBL0000001"[^>]*>\s*examplumab\s*</);
  assert.match(drugs, /<div class="card-facts">\s*<p>Antibody<\/p>\s*<ul>\s*<li>Inhibitor of Example receptor 1<\/li>\s*<\/ul>/);
  // No percentage: the rule stands where a score would, and opens to its sentence.
  assert.match(drugs, /<p class="match-why-head">Matched by exact name<\/p>/);
  assert.match(drugs, /is the same as “examplumab”, a name this claim uses\. Matched by that rule, so there is no percentage\./);
  assert.match(drugs, /href="https:\/\/drugs\.example\/"[^>]*>\s*Kind of molecule and what it acts on: Example Drugs, An Institute, CC BY-SA 3\.0 Unported\s*</);
  // Its record's one target, worded as the record's and not as a gene the name mentions.
  assert.match(drugs, /What the drug acts on, as its record says/);
  assert.match(drugs, /<p class="match-why-head">From the drug’s record<\/p>/);
  assert.match(drugs, /That the drug acts on it: Example Drugs, An Institute, CC BY-SA 3\.0 Unported/);
  assert.match(drugs, /nothing here is a reason to start or stop a medicine\./);
  assert.ok(!drugs.includes("known to work through that gene"));
  // Nothing about how far the drug has got.
  assert.doesNotMatch(drugs.split('class="card-facts"')[1].split("</div>")[0], /phase|approved|indication/i);
  assert.match(drugPage.split("Data sources:")[1].split("</p>")[0], />Example Drugs</);
  assert.match(section, /The kind of treatment this is, not the treatment itself/);
  assert.match(section, /href="https:\/\/vocabulary\.example\/D900009"[^>]*>\s*Example Stimulation Therapy\s*</);
  assert.match(section, /Match to this claim: high, 90%/);
  assert.match(section, /Its kind was chosen from this site’s fixed list of kinds\./);
  assert.match(section, /The trial registry lists it as a device in 3 of this claim’s trials\./);
  assert.match(section, /<blockquote[^>]*>A synthetic definition of a KIND OF TREATMENT, as the vocabulary writes it\.<\/blockquote>/);
  assert.match(section, /The kind of treatment this is, not the treatment itself/);
  // The open data file carries the kind card with its reasons.
  const data = JSON.parse(fs.readFileSync(path.join(dist, "data/claims.json"), "utf8"));
  const cards = data.claims.find((claim) => claim.slug === "approved-claim").background;
  assert.deepEqual(cards.map((card) => [card.kind, card.fit]), [
    ["condition", "exact"],
    ["intervention", "kind"],
    ["target", "exact"],
  ]);
  assert.equal(cards[2].definition_source, "uniprot");
  assert.ok(data.card_sources.some((held) => held.name === "uniprot" && held.licence === "CC BY 4.0"));
  // The share-alike drug facts are not in the file, and the file names the source left out.
  const kept = data.claims.find((claim) => claim.slug === "phase-claim").background;
  // The condition and treatment cards and the kind card added above stay; the drug and
  // its target do not.
  assert.deepEqual(kept.map((card) => card.kind), ["condition", "intervention", "intervention"]);
  assert.ok(!JSON.stringify(data.claims).includes("EXAMPLUMAB"));
  assert.ok(!JSON.stringify(data.claims).includes("Example receptor 1"));
  assert.deepEqual(data.left_out.map((left) => [left.source, left.licence]), [
    ["Example Drugs", "CC BY-SA 3.0 Unported"],
  ]);

  // Scenario: Code without site wording. An unworded molecule kind fails the build.
  const unworded = structuredClone(fixture);
  unworded.claims.find((claim) => claim.slug === "phase-claim").background[2].molecule_kind = "nanobot";
  fs.writeFileSync(file, JSON.stringify(unworded));
  const stopped = build(file, path.join(directory, "unworded"));
  assert.notEqual(stopped.status, 0);
  assert.match(stopped.stdout + stopped.stderr, /card molecule kind: nanobot/);
  assert.deepEqual(cards[1].reasons[1], { code: "registry_lists_type", type: "DEVICE", trials: 3 });

  // An unknown fit, reason or registry type fails the build and is named.
  for (const [change, named] of [
    // The export's schema lists the fits, so an unknown one is refused before wording.
    [(card) => (card.fit = "narrower"), /background\/1\/fit must be equal to one of the allowed values \(it is "narrower"\)/],
    [(card) => (card.reasons[0].code = "sounds_right"), /card reason: sounds_right/],
    [(card) => (card.reasons[1].type = "HOLOGRAM"), /card registry type: HOLOGRAM/],
  ]) {
    const broken = structuredClone(fixture);
    change(broken.claims.find((claim) => claim.slug === "approved-claim").background[1]);
    fs.writeFileSync(file, JSON.stringify(broken));
    const refused = build(file, path.join(directory, "refused"));
    assert.notEqual(refused.status, 0);
    assert.match(refused.stdout + refused.stderr, named);
  }
});

test("the method page explains kind cards", () => {
  const html = page("how-it-works/index.html");
  const part = html.split('id="background-on-a-claims-terms"')[1].split('id="who-a-claim-names"')[0];
  assert.match(part, /the card is for the kind of\s+treatment it is/);
  assert.match(part, /from a fixed list of kinds that this site keeps, or none of them/);
  assert.match(part, /about the kind of treatment and not the treatment itself/);
  assert.match(part, /registry’s type never decides the kind/);
  // And what a card for a named gene means.
  assert.match(part, /The card\s+means the report names the gene\. It does not mean the treatment is known to work through it,\s+and the site states no mechanism\./);
  assert.match(part, /in UniProt’s words as Open Targets Platform gives them/);
  // And what a drug card is, where it comes from and what it leaves out.
  assert.match(part, /the card shows the rule and no percentage/);
  assert.match(part, /The card never says how far a drug has\s+got, what it is approved for or what it is used for/);
  assert.match(part, /left out of the data download, which says so/);
});

// --- organisations (openspec site-publishing: "Organisations on the claim page") ---

const organisationsSection = (html) =>
  html.match(/<section class="matched organisations"[\s\S]*?<\/section>/)?.[0] ?? null;

test("Scenario: Claim with a university and a company", () => {
  const section = organisationsSection(page("phase-claim/index.html"));
  assert.ok(section, "the claim names organisations, so the page lists them");
  assert.match(section, /<h2 class="bar" id="organisations">[\s\S]*?Organisations named\s*<\/span><\/button><\/h2>/);
  // Named in the report first, then sponsors; each group by name.
  const names = [...section.matchAll(/class="organisation-name"[^>]*>([^<]+)</g)].map(([, name]) => name);
  assert.deepEqual(names, ["Example University", "Zed Start-up", "Synthetic Institute"]);
  // A sponsor's role links to the trial it sponsors on this page.
  const institute = section.split("Synthetic Institute")[1];
  assert.match(institute, /Sponsor of 1 trial: <a href="#trial-NCT00000002">NCT00000002<\/a>/);
  // An identified organisation shows the registry's facts, its record and the score.
  const university = section.split("Example University")[1].split("Zed Start-up")[0];
  assert.match(university, /Education, Funder · United Kingdom · <a href="https:\/\/www\.example\.ac\.uk\/"[^>]*>example\.ac\.uk<\/a>/);
  // One report on the page: "the report" needs no title.
  assert.match(university, /Named in the report\s*<\/li>/);
  assert.match(university, /which scores the name match 97%/);
  assert.match(university, /href="https:\/\/ror\.org\/00example1"[^>]*>\s*Its registry record/);
  assert.match(section, /it does not verify the organisation’s part in this claim/);
});

test("Scenario: Start-up the registry does not know", () => {
  const section = organisationsSection(page("phase-claim/index.html"));
  const startUp = section.split("Zed Start-up")[1].split("Synthetic Institute")[0];
  assert.match(startUp, /Named in the report/);
  assert.match(startUp, /Not matched to a registry record/);
  assert.doesNotMatch(startUp, /organisation-facts|ror\.org/);
});

test("Scenario: Claim with no organisation", () => {
  const html = page("quiet-claim/index.html");
  assert.equal(organisationsSection(html), null);
  assert.doesNotMatch(html, /Organisations named|id="organisations"/);
});

test("Scenario: Trial sponsored by a person", () => {
  // NCT00000030's sponsor is a person: the export names no one and the section lists nothing for it.
  const section = organisationsSection(page("phase-claim/index.html"));
  assert.doesNotMatch(section, /NCT00000030/);
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  const sponsors = fixture.claims.flatMap((claim) => (claim.trials ?? []).map((trial) => trial.facts?.sponsor));
  assert.ok(sponsors.some((sponsor) => sponsor?.kind === "individual" && sponsor.name === null));
});

test("Scenario: University press release on the claim page", () => {
  const html = page("approved-claim/index.html");
  const reported = html.match(/<section class="reported[^"]*"[\s\S]*?<\/section>/)[0];
  assert.match(reported, /This report is on Other Example Hospital’s website\./);
  // The timetable names the report too, with the same note beside it.
  assert.equal(count(html, "This report is on Other Example Hospital’s website."), 2);
});

test("Scenario: Newspaper report on the claim page", () => {
  for (const slug of ["phase-claim", "quiet-claim"]) {
    assert.doesNotMatch(page(`${slug}/index.html`), /This report is on/);
  }
});

test("the method page explains organisations and the publisher note", () => {
  const html = page("how-it-works/index.html");
  const part = html.split('id="who-a-claim-names"')[1].split('id="what-this-site-never-says"')[0];
  assert.match(part, /a news report named it, or a trial's registry record names it as\s+the trial's lead sponsor/);
  assert.match(part, /A trial sponsor that is a person is never listed/);
  assert.match(part, /chosen answer for the name and the name, ignoring capitals and punctuation,\s+is exactly one of that record's own names/);
  assert.match(part, /no looser match is tried/);
  assert.match(part, /it does not verify the organisation's part in a\s+claim/);
  assert.match(part, /The note says where a report is published\. It is not a\s+judgement on the report/);
});

test("Scenario: Kind code without site wording fails the build", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  fixture.claims.find((claim) => claim.slug === "phase-claim").organisations[0].record.kinds = ["think_tank"];
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-organisation-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));

  const result = build(file, path.join(directory, "dist"));

  assert.notEqual(result.status, 0);
  assert.match(
    result.stdout + result.stderr,
    /organisation codes the site has no words for: organisation kind: think_tank/,
  );
});

// --- reported statements (openspec reported-statements, site-publishing) ---

const statementsOf = (html) => html.match(/<section class="matched statements"[\s\S]*?<\/section>/)?.[0];
const plainText = (html) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

test("Scenario: Claim with three statements from one report", () => {
  const html = page("phase-claim/index.html");
  const section = statementsOf(html);
  assert.ok(section, "no statements section");
  assert.match(section, /<h2 class="bar" id="reported-statements">[\s\S]*?What the report said\s*<\/span><\/button><\/h2>/);
  // One report, named by its title, outlet and date, with the three statements under it.
  assert.equal(count(section, 'class="matched-group statement-report"'), 1);
  assert.match(section, /href="https:\/\/uk\.news\.example\.org\/3"[^>]*>\s*“Example report 3”/);
  assert.match(plainText(section), /Example Outlet 3 uk\.news\.example\.org 3 May 2019/);
  assert.equal(count(section, 'class="statement"'), 3);
  // Each with its kind and how sure the check is, as a word and a percentage.
  assert.match(plainText(section), /Effect The report said: Synthetic statement: examplumab eased/);
  for (const label of ["Very likely in the report · 93%", "Very likely in the report · 88%", "Very likely in the report · 81%"]) {
    assert.ok(section.includes(label), `no "${label}"`);
  }
  // A report's statement is not a record, and the records follow it.
  assert.match(section, /A report’s statement is not a record: the records follow\./);
  assert.match(section, /href="\/how-it-works#what-a-report-said"/);
  assert.ok(html.indexOf('id="reported-statements"') > html.indexOf('class="lede"'));
  assert.ok(html.indexOf('id="reported-statements"') < html.indexOf('id="timetable"'));
  // Not inside the status panel.
  // The panel is the band's last element, so it ends where the band does.
  const digest = html.match(/<div class="digest">[\s\S]*?<\/section>/)[0];
  assert.ok(!digest.includes("statement"));
});

test("Scenario: Possibility voiced by a researcher, and the basis as the report gave it", () => {
  const text = plainText(statementsOf(page("phase-claim/index.html")));
  assert.match(text, /The report had a researcher saying this could be so: Synthetic statement: examplumab could one day/);
  assert.match(text, /The report had the company saying: Synthetic statement: examplumab blocks/);
  assert.match(text, /The report gave a study in people as its basis\./);
  assert.match(text, /The report did not say what this rests on\./);
  assert.match(text, /The report gave laboratory work as its basis\./);
});

test("Scenario: Effect reported from a mouse study, on a claim with several reports", () => {
  const section = statementsOf(page("quiet-claim/index.html"));
  assert.match(section, /What the reports said/);
  assert.match(section, /What the news reports said about the treatment/);
  assert.equal(count(section, 'class="matched-group statement-report"'), 2);
  assert.match(plainText(section), /“Example report 1”.*regrew tissue in mice.*“Example report 2”.*no harm was seen/);
  assert.match(plainText(section), /The report gave a study in animals as its basis\./);
});

test("Scenario: Claim with no statement", () => {
  const html = page("approved-claim/index.html");
  assert.ok(!html.includes('id="reported-statements"'));
  assert.ok(!html.includes("statement-list"));
  assert.ok(!html.includes("What the report said"));
});

test("Scenario: Statement beside a trial result", () => {
  // phase-claim has a statement of an effect and a trial with posted results. Both are
  // shown, in their own sections, and no word compares them.
  const html = page("phase-claim/index.html");
  const statements = statementsOf(html);
  const trials = html.match(/<section class="trials"[\s\S]*?<\/section>/)[0];
  assert.match(plainText(trials), /results posted|Results posted/i);
  const comparing =
    /\b(confirm\w*|contradict\w*|consistent|inconsistent|held up|borne out|refut\w*|disprove\w*|verif\w*|accurate|inaccurate|true|false|correct|wrong|support(s|ed)?|as reported|matches the report)\b/i;
  assert.doesNotMatch(plainText(statements), comparing);
  assert.doesNotMatch(plainText(trials), /report said|statement/i);
  // Neither section points at the other.
  assert.ok(!statements.includes('href="#trials"') && !statements.includes("NCT0"));
  assert.ok(!trials.includes("reported-statements"));
});

test("Scenario: Kind code without site wording", () => {
  const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
  fixture.claims.find((claim) => claim.slug === "phase-claim").reported_statements[0].kind = "miracle";
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-statement-"));
  const file = path.join(directory, "export.json");
  fs.writeFileSync(file, JSON.stringify(fixture));

  const result = build(file, path.join(directory, "dist"));

  // The export's schema lists the kinds the pipeline knows, so an unknown one stops the
  // build there, named. A kind the schema gains before the site words it is named by the
  // site's own check (tests/statements.test.mjs).
  assert.notEqual(result.status, 0);
  assert.match(
    result.stdout + result.stderr,
    /\/claims\/1\/reported_statements\/0\/kind must be equal to one of the allowed values \(it is "miracle"\)/,
  );
});

test("Scenario: Reader doubts a statement", () => {
  const html = page("how-it-works/index.html");
  assert.match(html, /<a href="#what-a-report-said">What a report said<\/a>/);
  const part = plainText(html.split('id="what-a-report-said"')[1].split('id="what-a-trial-entry-shows"')[0]);
  assert.match(part, /An AI model reads each report/);
  assert.match(part, /written in this site’s own words/);
  assert.match(part, /checks each statement against its report/);
  assert.match(part, /how sure that check was that the report says it/);
  assert.match(part, /is what a report said, not what is on record/);
  assert.match(part, /statements never change a status/);
  assert.match(part, /removed by a person/);
});

// Openspec site-publishing (change page-frame): the band, the section list, folding
// sections, the newest-first timetable, counts kept apart and the trials table. These
// read the built pages; what a script does on a press is checked in the browser.
const bandOf = (html) =>
  html.slice(html.indexOf('<section class="band record"'), html.indexOf('<div class="frame'));
const foldOf = (html, id) => {
  const at = html.indexOf(`id="${id}"`);
  return html.slice(html.lastIndexOf('<div class="fold-head"', at), html.indexOf("</h2>", at));
};

test("Scenario: Claim page on a wide screen", () => {
  const band = bandOf(page("phase-claim/index.html"));
  // The title, the report followed and the status panel are all in the band.
  assert.match(band, /<h1 class="title/);
  assert.match(band, /class="label"[^>]*>Phase 2 trial</);
  assert.match(band, /class="reported band-reported"/);
  // The summary is the content's first words, not the band's.
  assert.ok(!band.includes('class="lede"'));
});

test("Scenario: Topic with one claim at each of two statuses", () => {
  const band = bandOf(page("topic/gum-disease/index.html"));
  assert.match(band, /<h1 class="title">Gum disease<\/h1>/);
  // Each status the topic's claims hold is counted in words, in the summary sentence.
  assert.match(wordsOf(band), /Of 3 reported breakthroughs tracked, 1 has/);
});

test("Scenario: Claim that follows three reports", () => {
  // Two here: the newest under the band on a phone, and one link to the other.
  const html = page("quiet-claim/index.html");
  const under = html.match(/<div class="reported phone-reported"[\s\S]*?<\/div>/)[0];
  assert.equal(count(under, 'class="reported-title"'), 1);
  assert.match(wordsOf(under), /1 more report, on the timetable/);
  assert.match(under, /href="#timetable"/);
});

test("Scenario: Claim with no papers", () => {
  // Here: a claim with no trial, so the list has no entry for trials.
  const list = (slug) => page(`${slug}/index.html`).match(/<nav class="onpage"[\s\S]*?<\/nav>/)[0];
  const withTrials = list("phase-claim");
  assert.match(withTrials, /href="#trials"[\s\S]*?Trials on record[\s\S]*?class="n">7</);
  assert.match(withTrials, /href="#papers"[\s\S]*?class="n">5</);
  // A section the page does not have is not listed.
  const without = list("quiet-claim");
  assert.ok(!without.includes('href="#trials"'));
  assert.ok(without.includes('href="#timetable"'));
});

test("Scenario: Wide screen, first view", () => {
  const html = page("phase-claim/index.html");
  // Papers start folded, with their count on the heading line.
  assert.match(foldOf(html, "papers"), /data-fold="folded"/);
  assert.match(html.slice(html.indexOf('id="papers"')), /^[\s\S]{0,700}class="fold-note">5 papers</);
  // The timetable and the trials start open.
  assert.match(foldOf(html, "timetable"), /data-fold="open"/);
  assert.match(foldOf(html, "trials"), /data-fold="open"/);
  // The heading stays a heading and holds the control, which says whether it is open.
  assert.match(foldOf(html, "trials"), /<h2 class="bar" id="trials"><button type="button" class="fold" aria-expanded="true">/);
});

test("Scenario: Phone, first view", () => {
  const html = page("phase-claim/index.html");
  for (const id of ["brief", "timetable"]) assert.match(foldOf(html, id), /data-fold-phone="open"/);
  for (const id of ["reported-statements", "trials", "papers", "others", "pass-on"]) {
    assert.match(foldOf(html, id), /data-fold-phone="folded"/, `${id} starts open on a phone`);
  }
});

test("Scenario: Scripting off", () => {
  // A fold is closed by the stylesheet only where a script has marked the page, and
  // only on a screen: with no script, and on paper, every section is open.
  const styles = fs
    .readdirSync(path.join(dist, "_astro"))
    .filter((name) => name.endsWith(".css"))
    .map((name) => fs.readFileSync(path.join(dist, "_astro", name), "utf8"))
    .join("");
  assert.match(styles, /@media screen\{\.js \.fold-head\[data-fold=folded\]:not\(\[data-state\]\)~\*/);
  assert.ok(!page("phase-claim/index.html").includes(" hidden data-fold"));
});

test("Scenario: Records from 2021 to 2026 with none in 2024 and 2025", () => {
  // Here: records in 2018 to 2020, a promise for 2025, and nothing from 2021 to 2024.
  const timetable = sectionOf(page("quiet-claim/index.html"), "timetable");
  const years = [...timetable.matchAll(/id="year-(\d{4})"/g)].map(([, year]) => Number(year));
  assert.deepEqual(years, [...years].sort((a, b) => b - a), "years are not newest first");
  assert.equal(years[0], 2026);
  assert.equal(years.at(-1), 2018);
  // The run of years with nothing in them is one row that names them, in its place.
  assert.match(wordsOf(timetable), /2021 to 2024\s+No promise, no record/);
  assert.ok(timetable.indexOf('id="year-2025"') < timetable.indexOf("2021 to 2024"));
  assert.ok(timetable.indexOf("2021 to 2024") < timetable.indexOf('id="year-2020"'));
});

test("Scenario: Four promises and seventeen records", () => {
  // Here: one promise and three records, given as two numbers wherever they are given.
  const html = page("quiet-claim/index.html");
  assert.match(html, /class="fold-note">1 promise · 3 records · newest first</);
  assert.match(html, /href="#timetable"[\s\S]{0,200}class="n">1 and 3</);
  const controls = html.match(/<div class="kind-tabs"[\s\S]*?<\/div>/)[0];
  assert.match(wordsOf(controls), /All\s+Promises 1\s+News reports 2\s+/);
  assert.ok(!/\b4\b/.test(wordsOf(controls)), "promises and records are added together");
});

test("Scenario: Registry records only", () => {
  // The controls are shown by the script; every entry carries the kind it is narrowed by.
  const html = page("phase-claim/index.html");
  assert.match(html, /<div class="kind-tabs" role="group" aria-label="Show entries of one kind" hidden data-kinds>/);
  const timetable = sectionOf(html, "timetable");
  assert.equal(count(timetable, 'data-kind="report"'), 2, "the control and one entry");
  assert.ok(count(timetable, 'data-kind="trial"') >= 2);
  assert.match(html, /role="status" data-kinds-said/);
});

test("Scenario: Three finished trials", () => {
  const trials = sectionOf(page("phase-claim/index.html"), "trials");
  const table = trials.slice(trials.indexOf('role="table"'));
  for (const name of ["Trial", "Compared with", "Design", "State", "Results"]) {
    assert.ok(table.includes(`<span role="columnheader">${name}</span>`), `no column named ${name}`);
  }
  // A row is a row; the control that opens it says whether it is open and names what it opens.
  assert.match(table, /class="trial-group" role="rowgroup" id="trial-NCT00000002"/);
  assert.match(table, /class="trial-open" aria-expanded="true" aria-controls="trial-detail-NCT00000002"/);
  assert.match(table, /class="trial-detail" role="row" id="trial-detail-NCT00000002"/);
});

test("Scenario: Trial registered with three trials", () => {
  // Here: a Phase 2 status that rests on two records, and the page marks those two.
  const html = page("phase-claim/index.html");
  const why = html.match(/<ul class="pop-list">[\s\S]*?<\/ul>/)[0];
  assert.equal(count(why, "<li"), 2);
});

test("Scenario: Tabbing into a claim page", () => {
  const html = page("phase-claim/index.html");
  // The skip link is the page's first link, and the actions come before the content.
  assert.ok(html.indexOf('<a class="skip"') < html.indexOf('class="masthead"'));
  assert.ok(html.indexOf("data-follow") < html.indexOf('<article class="sheet"'));
  assert.ok(html.indexOf("data-follow") < html.indexOf('<nav class="onpage"'));
});

test("Scenario: Topic among ten", () => {
  // Here: one topic with published claims, listed with its count and marked as this one.
  const list = page("topic/gum-disease/index.html").match(/<nav class="onpage"[\s\S]*?<\/nav>/)[0];
  assert.equal(count(list, "<li"), 1);
  assert.match(list, /href="\/topic\/gum-disease" aria-current="page"[\s\S]*?Gum disease[\s\S]*?class="n">3</);
  assert.ok(!list.includes("empty-topic"));
});
