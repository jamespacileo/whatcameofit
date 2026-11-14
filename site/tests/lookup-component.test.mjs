// The lookup box as a component. The home page draws it as before, checked in a build of
// tests/fixture-export.json; a page that carries the claims' sentences ends a tracked
// answer with one to pass on, checked by running the component's own script.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import os from "node:os";
import path from "node:path";
import vm from "node:vm";
import { before, test } from "node:test";
import { parseHTML } from "linkedom";
import { closestClaims, readAddress } from "../src/lib/lookup-match.mjs";
import { SUGGEST_SUBJECT, contactLink } from "../src/lib/contact.mjs";
import { LIVE, describeAnswer, refusalMessage, textWouldHelp } from "../src/lib/live-lookup.mjs";

const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-lookup-"));
const page = (relative) => fs.readFileSync(path.join(dist, relative), "utf8");

before(() => {
  const result = spawnSync("npx", ["astro", "build", "--outDir", dist], {
    env: { ...process.env, EXPORT_FILE: "tests/fixture-export.json", ASTRO_TELEMETRY_DISABLED: "1" },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

test("the home page draws the lookup in its band, in the same order", () => {
  const html = page("index.html");
  const band = html.slice(html.indexOf('<section class="band"'), html.indexOf('class="front"'));
  const parts = [
    '<h1 class="title" id="lookup-title">',
    '<form class="search lookup" role="search" id="search">',
    '<label for="query">Paste a link to an article, or search by treatment or condition</label>',
    '<input id="query" name="q" type="search"',
    "<noscript>",
    '<div class="results" id="results" aria-live="polite"',
    '<template id="unfound"><svg class="unfound"',
    '<template id="remind-later">',
  ];
  const at = parts.map((part) => band.indexOf(part));
  parts.forEach((part, index) => assert.ok(at[index] > -1, `${part} is not in the band`));
  assert.deepEqual([...at].sort((a, b) => a - b), at);
  assert.equal(html.split('id="remind-later"').length - 1, 1);
  // The script that answers is bundled with the page.
  const script = band.match(/<script type="module" src="(\/_astro\/[^"]+\.js)">/);
  assert.ok(script, "the lookup's script is not on the page");
  assert.match(page(script[1]), /This article is one we track\./);
  assert.doesNotMatch(html, /lookup-sentences/);
});

// The component's script, run against a small page with only its network boundary,
// clipboard and timers controlled. No real article text is used.
const script = stripTypeScriptTypes(
  fs
    .readFileSync(new URL("../src/components/Lookup.astro", import.meta.url), "utf8")
    .match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace(/^\s*import .*;\s*$/gm, ""),
);
const settle = () => new Promise((resolve) => setImmediate(resolve));
const SENTENCE = "Earlier report. Status: Trial registered. Not medical advice. https://example.test/old";

async function trackedAnswer({ navigator, carried = true }) {
  const sentences = { "/old": { sentence: SENTENCE, card: "/og/old.png" } };
  const { document, window } = parseHTML(
    `<html><body><form id="search"><input id="query"></form><div id="results"></div>${
      carried ? `<script type="application/json" id="lookup-sentences">${JSON.stringify(sentences)}</script>` : ""
    }</body></html>`,
  );
  const results = document.querySelector("#results");
  results.scrollIntoView = () => {};
  const timers = [];
  vm.runInNewContext(script, {
    document, URL, navigator, getSelection: () => null, setTimeout: (run) => timers.push(run),
    BRAND: { name: "Example tracker" }, readAddress, closestClaims,
    LIVE, describeAnswer, refusalMessage, textWouldHelp, SUGGEST_SUBJECT, contactLink,
    location: { href: "https://example.test/" }, history: { replaceState() {} },
    fetch: async () => ({ json: async () => ({
      articles: { "example.org/old-report": ["old"] },
      claims: { old: { headline: "Earlier report", page: "/old", status: "Trial registered", meaning: "A trial is registered." } },
      places: 6,
    }) }),
  });
  document.querySelector("#query").value = "https://example.org/old-report";
  document.querySelector("#search").dispatchEvent(new window.Event("submit", { cancelable: true }));
  await settle();
  return { about: results.querySelector(".found .about"), window, timers };
}

test("a tracked answer ends with the claim's sentence, a copy button and its card", async () => {
  let copied = null;
  const clipboard = { writeText: async (text) => { copied = text; } };
  const { about, window, timers } = await trackedAnswer({ navigator: { clipboard } });
  const tail = [...about.children].slice(-3);
  assert.equal(tail[0].querySelector("a").textContent, "See the records");
  assert.equal(tail[1].className, "sentence");
  assert.equal(tail[1].textContent, SENTENCE);
  const copy = tail[2].querySelector("button.share");
  const card = tail[2].querySelector("a.share");
  assert.equal(copy.textContent, "Copy sentence");
  assert.equal(card.textContent, "Card to post");
  assert.equal(card.getAttribute("href"), "/og/old.png");

  copy.dispatchEvent(new window.Event("click"));
  await settle();
  assert.equal(copied, SENTENCE);
  assert.equal(copy.textContent, "Copied");
  assert.ok(copy.classList.contains("done"));
  for (const run of timers) run();
  assert.equal(copy.textContent, "Copy sentence");
  assert.ok(!copy.classList.contains("done"));
});

test("with no clipboard the sentence is there to read and no button is drawn", async () => {
  const { about } = await trackedAnswer({ navigator: {} });
  assert.equal(about.querySelector(".sentence").textContent, SENTENCE);
  assert.equal(about.querySelector("button"), null);
  assert.equal(about.querySelector("a.share").textContent, "Card to post");
});

test("a page that carries no sentences answers as the home page does", async () => {
  const { about } = await trackedAnswer({ navigator: {}, carried: false });
  assert.equal(about.querySelector(".sentence"), null);
  assert.equal(about.lastElementChild.querySelector("a").textContent, "See the records");
});
