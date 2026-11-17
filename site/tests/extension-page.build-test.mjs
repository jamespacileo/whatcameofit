// The extension page (openspec landing-pages-and-guide): which claim it shows, that its
// words match the extension's own, and that it is built only when a store lists the
// extension. Pages are checked in builds of tests/fixture-export.json.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";
import {
  HOSTS,
  LEDGER,
  PERMISSIONS,
  POPUP_LINES,
  POPUP_WORDS,
  exampleClaim,
  latestChange,
  registryRecords,
  wasNow,
} from "../src/lib/extension-page.ts";
import { STATUS_LABELS } from "../src/lib/status.ts";

const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
const view = fs.readFileSync("../extension/src/view.js", "utf8");
const manifest = fs.readFileSync("../extension/build.mjs", "utf8");
const shortLinks = fs.readFileSync("../extension/src/short-links.js", "utf8");

const CHROME = "https://chromewebstore.google.com/detail/example";
const SAFARI = "https://apps.apple.com/app/example";

function build(env) {
  const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-extension-"));
  const result = spawnSync("npx", ["astro", "build", "--outDir", dist], {
    env: {
      ...process.env,
      CHROME_STORE_URL: "",
      SAFARI_STORE_URL: "",
      ...env,
      EXPORT_FILE: "tests/fixture-export.json",
      ASTRO_TELEMETRY_DISABLED: "1",
    },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  return {
    page: (relative) => fs.readFileSync(path.join(dist, relative), "utf8"),
    exists: (relative) => fs.existsSync(path.join(dist, relative)),
  };
}

let none;
let chrome;
let both;
before(() => {
  none = build({});
  chrome = build({ CHROME_STORE_URL: CHROME });
  both = build({ CHROME_STORE_URL: CHROME, SAFARI_STORE_URL: SAFARI });
});

const claim = (slug, status, articles, promised) => ({
  slug,
  status: { code: status },
  articles: Array.from({ length: articles }, (_, index) => ({ published_date: `2020-01-0${index + 1}` })),
  promises: promised ? [{ description: "Trials by 2025", parsed_date: "2025-01-01" }] : [],
});

test("the example claim is on the path, then has a dated promise, then the most reports", () => {
  const claims = [
    claim("off-path", "retracted", 9, true),
    claim("no-promise", "phase_2", 9, false),
    claim("few-reports", "phase_1", 1, true),
    claim("chosen", "phase_3", 2, true),
    claim("also-two", "trial_registered", 2, true),
  ];
  // "also-two" ties on every count; the slug settles it, so a rebuild picks the same claim.
  assert.equal(exampleClaim(claims).slug, "also-two");
  assert.equal(exampleClaim(claims.filter((c) => c.slug !== "also-two")).slug, "chosen");
});

test("a claim whose three answers can all be drawn comes before one with more reports", () => {
  const drawable = {
    ...claim("drawable", "phase_3", 1, true),
    status: { code: "phase_3", history: [{ on: "2020-01-01", code: "phase_2" }, { on: "2024-01-01", code: "phase_3" }] },
    matches: [{ external_id: "NCT1", score: 0.9, url: "https://clinicaltrials.gov/study/NCT1" }],
    events: [{ trial_id: "NCT1", trial_phases: ["phase_3"], trial_state: "started", event_date: "2024-01-01" }],
  };
  assert.equal(exampleClaim([claim("many-reports", "phase_3", 9, true), drawable]).slug, "drawable");
});

test("a claim with no news report is never the example", () => {
  assert.equal(exampleClaim([claim("unreported", "phase_3", 0, true)]), null);
  assert.equal(exampleClaim([]), null);
});

test("the drawn popup's labels are the extension's own", () => {
  for (const [name, words] of Object.entries(POPUP_WORDS)) {
    assert.ok(view.includes(`${name}: ${JSON.stringify(words)}`), `view.js words "${name}" differently`);
  }
  for (const line of Object.values(POPUP_LINES)) assert.ok(view.includes(line), `view.js does not write "${line}"`);
  assert.ok(view.includes("wasNow: (was, now) => `Was: ${was}. Now: ${now}.`"));
  assert.ok(view.includes("lastChecked: (date) => `Registries last checked ${date}.`"));
  assert.equal(wasNow("Phase 1 trial", "Phase 2 trial"), "Was: Phase 1 trial. Now: Phase 2 trial.");
});

test("the permissions listed are the manifest's, and no other", () => {
  const listed = manifest.match(/permissions: \[([^\]]+)\]/)[1].match(/"([^"]+)"/g).map((name) => name.slice(1, -1));
  assert.deepEqual(PERMISSIONS.map((permission) => permission.name).sort(), listed.sort());
  const hosts = shortLinks.match(/RESOLVABLE = \[([^\]]+)\]/)[1].match(/"([^"]+)"/g).map((name) => name.slice(1, -1));
  assert.deepEqual(HOSTS.map((entry) => entry.host), hosts);
});

test("Scenario: No store is configured", () => {
  assert.ok(!none.exists("extension/index.html"), "the extension page was built with no store");
  for (const file of ["index.html", "quiet-claim/index.html", "how-it-works/index.html"]) {
    assert.ok(!none.page(file).includes('href="/extension"'), `${file} links a page that does not exist`);
  }
});

test("Scenario: One store is configured", () => {
  const html = chrome.page("extension/index.html");
  assert.ok(html.includes(`href="${CHROME}"`), "the Chrome listing is not linked");
  assert.ok(!html.includes("apps.apple.com"));
  assert.match(html, /Safari[^<]*not yet available/, "the page does not say Safari is not yet available");
  assert.ok(both.page("extension/index.html").includes(`href="${SAFARI}"`));
  assert.ok(!both.page("extension/index.html").includes("not yet available"));
});

test("Scenario: The extension is installable", () => {
  const topic = `topic/${fixture.claims[0].vertical}/index.html`;
  for (const file of ["index.html", "quiet-claim/index.html", topic, "how-it-works/index.html"]) {
    assert.ok(chrome.page(file).includes('href="/extension"'), `${file} does not link the extension page`);
  }
});

test("the page shows the popup's answer for the example claim, dated", () => {
  const html = chrome.page("extension/index.html");
  const example = exampleClaim(fixture.claims);
  assert.ok(html.includes(STATUS_LABELS[example.status.code]), "the example claim's status is missing");
  assert.ok(html.includes(POPUP_WORDS.standing));
  assert.match(html, /as the registries showed it on/i, "the popup's answer is not dated");
  // The report is named by outlet, title and date; a drawn article would need its text.
  assert.ok(html.includes(example.articles[0].outlet));
});

test("Scenario: A reader checks before installing", () => {
  const html = chrome.page("extension/index.html").replace(/&#39;|&#x27;/g, "'");
  for (const row of LEDGER) assert.ok(html.includes(row.when), `the table lacks "${row.when}"`);
  assert.ok(html.includes("OpenAI"), "OpenAI is not named");
  assert.ok(html.includes("Automatic search settings"), "the setting that turns it off is not named");
  assert.ok(html.includes('href="/privacy"'), "the privacy page is not linked");
});

test("Scenario: A reviewed match", () => {
  const html = chrome.page("extension/index.html").replace(/&#39;|&#x27;/g, "'");
  assert.ok(html.includes(LEDGER[0].sentNote));
  assert.match(html, /Nothing/);
});

test("Scenario: Permissions are listed", () => {
  const html = chrome.page("extension/index.html");
  for (const permission of PERMISSIONS) assert.ok(html.includes(permission.plain), permission.name);
  for (const entry of HOSTS) assert.ok(html.includes(entry.host), entry.host);
});

test("the extension page carries the two notices in its body and holds no endorsement", () => {
  const html = chrome.page("extension/index.html");
  const body = html.slice(html.indexOf("<main"), html.indexOf("</main>"));
  assert.ok(body.includes("This site gives no medical advice"));
  assert.ok(body.includes("A registered clinical trial is not a treatment option"));
  assert.doesNotMatch(body, /\btrusted by\b|\brated\b|\bstars?\b|\busers\b|\binstalls\b/i);
});

test("Scenario: A claim with matched trials and a change of status", () => {
  const moved = {
    status: { code: "phase_3", history: [{ on: "2019-12-02", code: "phase_2" }, { on: "2024-09-20", code: "phase_3" }] },
    matches: [
      { external_id: "NCT1", score: 0.99, url: "https://clinicaltrials.gov/study/NCT1" },
      { external_id: "NCT2", score: 0.62, url: null },
      { external_id: "NCT-unseen", score: 0.9, url: null },
    ],
    events: [
      { trial_id: "NCT1", trial_phases: ["phase_2"], trial_state: "completed", event_date: "2021-01-01" },
      { trial_id: "NCT2", trial_phases: ["phase_3"], trial_state: null, event_date: "2024-08-14" },
      { trial_id: "NCT2", trial_phases: ["phase_3"], trial_state: "started", event_date: "2024-09-20" },
    ],
  };
  assert.deepEqual(latestChange(moved), { was: "Phase 2 trial", now: "Phase 3 trial", on: "2024-09-20" });
  // Furthest phase first; a match with no record in the export is not drawn.
  assert.deepEqual(registryRecords(moved), [
    { id: "NCT2", url: null, phase: "Phase 3", state: "Started", confidence: "Medium match · 62%" },
    { id: "NCT1", url: "https://clinicaltrials.gov/study/NCT1", phase: "Phase 2", state: "Completed", confidence: "High match · 99%" },
  ]);
});

test("Scenario: A claim with neither", () => {
  const example = exampleClaim(fixture.claims);
  assert.equal(latestChange(example), null);
  assert.deepEqual(registryRecords(example), []);
  const html = chrome.page("extension/index.html");
  assert.equal(html.match(/class="pp-popup/g).length, 1, "an answer is drawn that the export does not hold");
});
