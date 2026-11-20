// The extension page (openspec landing-pages-and-guide): which pair it shows, that its
// words match the extension's own, and that it is built only when a store lists the
// extension. Pages are checked in builds of tests/bundle.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import {
  HOSTS,
  LEDGER,
  PERMISSIONS,
  POPUP_LINES,
  POPUP_WORDS,
  examplePair,
  wasNow,
} from "../src/lib/extension-page.ts";
import { readBundle } from "../src/lib/bundle.ts";
import { STATUS_LABELS } from "../src/lib/status.ts";

const pairs = Object.values(readBundle("tests/bundle").pages.PairPage);
const view = fs.readFileSync("../extension/src/view.js", "utf8");

const CHROME = "https://chromewebstore.google.com/detail/example";
const SAFARI = "https://apps.apple.com/app/example";
const outputs = [];

function build(env) {
  const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-extension-"));
  outputs.push(dist);
  const result = spawnSync(process.execPath, ["node_modules/astro/bin/astro.mjs", "build", "--outDir", dist], {
    env: {
      ...process.env,
      CHROME_STORE_URL: "",
      SAFARI_STORE_URL: "",
      ...env,
      PAIRS_BUNDLE: "tests/bundle",
      ASTRO_TELEMETRY_DISABLED: "1",
    },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  return (relative) => fs.readFileSync(path.join(dist, relative), "utf8");
}

let chrome;
let both;
before(() => {
  chrome = build({ CHROME_STORE_URL: CHROME });
  both = build({ CHROME_STORE_URL: CHROME, SAFARI_STORE_URL: SAFARI });
});
after(() => {
  for (const dist of outputs) fs.rmSync(dist, { recursive: true, force: true });
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

test("Scenario: One store is configured", () => {
  const html = chrome("extension/index.html");
  assert.ok(html.includes(`href="${CHROME}"`), "the Chrome listing is not linked");
  assert.ok(!html.includes("apps.apple.com"));
  assert.match(html, /Safari[^<]*not yet available/, "the page does not say Safari is not yet available");
  const bothStores = both("extension/index.html");
  assert.ok(bothStores.includes(`href="${CHROME}"`));
  assert.ok(bothStores.includes(`href="${SAFARI}"`));
  assert.ok(!bothStores.includes("not yet available"));
});

test("Scenario: The extension is installable", () => {
  const example = examplePair(pairs);
  const topic = `topic/${example.row.filing.vertical}/index.html`;
  for (const file of ["index.html", `${example.row.pair.address}/index.html`, topic, "how-it-works/index.html"]) {
    assert.ok(chrome(file).includes('href="/extension"'), `${file} does not link the extension page`);
  }
});

test("the page shows the popup's answer for the example pair, dated", () => {
  const html = chrome("extension/index.html");
  const example = examplePair(pairs);
  assert.ok(html.includes(STATUS_LABELS[example.row.status.code]), "the example pair's status is missing");
  assert.ok(html.includes(POPUP_WORDS.standing));
  assert.match(html, /from records gathered on \d/i, "the popup's answer is not dated");
});

test("Scenario: A reader checks before installing", () => {
  const html = chrome("extension/index.html").replace(/&#39;|&#x27;/g, "'");
  for (const row of LEDGER) assert.ok(html.includes(row.when), `the table lacks "${row.when}"`);
  assert.ok(html.includes("OpenAI"), "OpenAI is not named");
  assert.ok(html.includes("Automatic search settings"), "the setting that turns it off is not named");
  assert.ok(html.includes('href="/privacy"'), "the privacy page is not linked");
});

test("Scenario: A reviewed match", () => {
  const html = chrome("extension/index.html").replace(/&#39;|&#x27;/g, "'");
  assert.ok(html.includes(LEDGER[0].sentNote));
  assert.match(html, /Nothing/);
});

test("Scenario: Permissions are listed", () => {
  const html = chrome("extension/index.html");
  for (const permission of PERMISSIONS) assert.ok(html.includes(permission.plain), permission.name);
  for (const entry of HOSTS) assert.ok(html.includes(entry.host), entry.host);
});

test("the extension page carries the two notices in its body and holds no endorsement", () => {
  const html = chrome("extension/index.html");
  const body = html.slice(html.indexOf("<main"), html.indexOf("</main>"));
  assert.ok(body.includes("This site gives no medical advice"));
  assert.ok(body.includes("A registered clinical trial is not a treatment option"));
  assert.doesNotMatch(body, /\btrusted by\b|\brated\b|\bstars?\b|\busers\b|\binstalls\b/i);
});
