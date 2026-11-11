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
  // Four approved events, each with a footnote that links to its source.
  for (const id of [2, 3, 4, 5]) {
    assert.ok(html.includes(`https://registry.example/record/${id}"`), `event ${id} has no link`);
  }
  assert.equal(count(html, 'id="source-'), 4);
});

test("Scenario: Unknown slug", () => {
  assert.match(page("404.html"), /No page at this address/);
});

test("Scenario: Status produced by one trial", () => {
  const html = page("phase-claim/index.html");
  // The registered and started events produced the status; the paper and results did not.
  assert.equal(count(html, ">basis of status<"), 2);
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
  const html = page("topic/dental-regeneration/index.html");
  for (const slug of ["quiet-claim", "phase-claim", "approved-claim"]) {
    assert.ok(html.includes(`href="/${slug}"`), `${slug} is not listed`);
  }
  assert.match(html, /3 reported breakthroughs tracked/);
  assert.match(html, /Preclinical only/);
  assert.match(html, /Phase 2 trial/);
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
  assert.match(scripts + page("index.html"), /Nothing found for/);
});

test("Scenario: No approved claims", () => {
  // With an approved claim the page lists it; with none it says so.
  assert.ok(page("it-happened/index.html").includes('href="/approved-claim"'));
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-site-empty-"));
  const result = build("data/seed-export.json", empty);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const html = fs.readFileSync(path.join(empty, "it-happened/index.html"), "utf8");
  assert.match(html, /No tracked claim has reached approval yet/);
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
    assert.match(html, /Registries last checked 11 Nov 2026/, file);
  }
});

test("Scenario: Long-quiet claim", () => {
  const html = page("quiet-claim/index.html");
  assert.match(html, /No signal for 6 years/);
  assert.doesNotMatch(html, /\b(dead|abandoned|scam|hoax|debunked)\b/i);
});

test("Scenario: Offline build", () => {
  // The build above read one local file. The pages must also ask the network for
  // nothing but the links a reader chooses to follow.
  for (const file of htmlFiles(dist)) {
    const html = fs.readFileSync(file, "utf8");
    assert.doesNotMatch(html, /<(script|link|img)[^>]+(src|href)="https?:\/\//, file);
  }
});

test("an export that does not match the schema stops the build", () => {
  const broken = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bad-")), "export.json");
  fs.writeFileSync(broken, JSON.stringify({ schema_version: 1, claims: "not a list" }));
  const result = build(broken, fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-site-bad-")));
  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /does not match export\.schema\.json/);
});
