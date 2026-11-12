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
  assert.match(scripts + page("index.html"), /No record found for/);
});

test("Scenario: Home lists the newest reports", () => {
  const html = page("index.html");
  assert.match(html, /Headlines reported most recently/);
  // Newest first, across claims: reports 3, 2, 1, then 4.
  const order = [3, 2, 1, 4].map((number) => html.indexOf(`Example report ${number}`));
  assert.ok(order.every((position) => position > -1), "a report is missing from the home page");
  assert.deepEqual([...order].sort((a, b) => a - b), order);
  // The headline opens the claim; the outlet opens the report itself.
  assert.match(html, /<a href="\/phase-claim">“Example report 3”<\/a>/);
  assert.match(html, /<a href="https:\/\/news\.example\.org\/3">Example Outlet 3<\/a>/);
});

test("Scenario: Article of a published claim", () => {
  const lookup = JSON.parse(page("lookup.json"));
  // Each article address, in comparison form, names its claim.
  assert.deepEqual(lookup.articles["news.example.org/3"], ["phase-claim"]);
  assert.deepEqual(lookup.articles["news.example.org/1"], ["quiet-claim"]);
  assert.deepEqual(lookup.articles["news.example.org/2"], ["quiet-claim"]);
  // Only published claims, each with the site's own wording and its page address.
  assert.deepEqual(Object.keys(lookup.claims).sort(), ["approved-claim", "phase-claim", "quiet-claim"]);
  const claim = lookup.claims["phase-claim"];
  assert.equal(claim.status, "Phase 2 trial");
  assert.equal(claim.headline, "Synthetic claim with a started trial");
  assert.equal(claim.page, "/phase-claim");
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
  const html = page("phase-claim/index.html");
  assert.match(html, /<img class="tile" src="\/outlet-icons\/news\.example\.org\.png" alt=""/);
  const icon = fs.readFileSync(path.join(dist, "outlet-icons/news.example.org.png"));
  assert.deepEqual([...icon.subarray(0, 4)], [0x89, 0x50, 0x4e, 0x47]);
});

test("Scenario: Outlet with no stored icon", () => {
  // The fourth report's outlet has no icon in the export, so its letter tile is drawn.
  const html = page("approved-claim/index.html");
  assert.match(html, /<span class="tile" aria-hidden="true">\s*O\s*<\/span>/);
  assert.doesNotMatch(html, /<img class="tile"/);
  assert.ok(!fs.existsSync(path.join(dist, "outlet-icons/other.example.net.png")));
});

test("Scenario: Offline build", () => {
  // The build above read one local file. The pages must also ask the network for
  // nothing but the links a reader chooses to follow.
  for (const file of htmlFiles(dist)) {
    const html = fs.readFileSync(file, "utf8");
    // A page's own canonical address is the one absolute address it may state.
    assert.doesNotMatch(
      html,
      /<(script|link|img)(?![^>]*\brel="canonical")[^>]+(src|href)="https?:\/\//,
      file,
    );
  }
});

test("an export that does not match the schema stops the build", () => {
  const broken = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bad-")), "export.json");
  fs.writeFileSync(broken, JSON.stringify({ schema_version: 1, claims: "not a list" }));
  const result = build(broken, fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-site-bad-")));
  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /does not match export\.schema\.json/);
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
