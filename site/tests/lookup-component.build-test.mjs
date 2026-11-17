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

test("the home page carries the lookup and the script that answers", () => {
  const html = page("index.html");
  // The hooks the script needs are on the page, each once.
  for (const id of ["search", "query", "results", "remind-later"]) {
    assert.equal(html.split(`id="${id}"`).length - 1, 1, id);
  }
  // The script that answers is bundled with the page.
  const script = html.match(/<script type="module" src="(\/_astro\/Lookup[^"]+\.js)">/);
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

test("the website opts in and displays each independent claim with its own results", async () => {
  const { document, window } = parseHTML('<html><body><form id="search"><input id="query"></form><div id="results" data-live="/api/lookup"></div></body></html>');
  const sent = [];
  const found = { about_a_treatment: true, claims: [
    { about_a_treatment: true, treatment: "EX-1", condition: "condition one", candidates: [], tracked: [{ headline: "First card", page: "/first" }] },
    { about_a_treatment: true, treatment: "EX-2 plus EX-3", condition: "condition two", candidates: [], tracked: [], check_state: "unchecked", check_reason: "work_limit" },
  ] };
  document.querySelector("#results").scrollIntoView = () => {};
  vm.runInNewContext(script, {
    document, URL, crypto, navigator: {}, getSelection: () => null, setTimeout,
    BRAND: { name: "Example tracker" }, readAddress, closestClaims,
    LIVE, describeAnswer, refusalMessage, textWouldHelp, SUGGEST_SUBJECT, contactLink,
    location: { href: "https://example.test/" }, history: { replaceState() {}, pushState() {} }, addEventListener() {},
    fetch: async (_url, options) => {
      if (options?.method === "POST") { sent.push(JSON.parse(options.body)); return { status: 200, json: async () => found }; }
      return { json: async () => ({ articles: {}, claims: {}, places: 6 }) };
    },
  });
  document.querySelector("#query").value = "https://example.org/synthetic-roundup";
  document.querySelector("#search").dispatchEvent(new window.Event("submit", { cancelable: true }));
  await settle();
  document.querySelector(".live-offer").click();
  await settle();
  assert.equal(sent.length, 1);
  assert.equal(sent[0].claimResults, true);
  const claims = [...document.querySelectorAll(".independent-claim")];
  assert.equal(claims.length, 2);
  assert.match(claims[0].textContent, /EX-1.*condition one.*First card/);
  assert.doesNotMatch(claims[0].textContent, /condition two/);
  assert.match(claims[1].textContent, /EX-2 plus EX-3.*condition two.*remains unchecked/);
  assert.doesNotMatch(claims[1].textContent, /No matching trial|First card/);
  assert.equal(document.querySelectorAll(".unchecked").length, 1, "one page-level provenance notice");
});

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
    document, URL, crypto, navigator, getSelection: () => null, setTimeout: (run) => timers.push(run),
    BRAND: { name: "Example tracker" }, readAddress, closestClaims,
    LIVE, describeAnswer, refusalMessage, textWouldHelp, SUGGEST_SUBJECT, contactLink,
    location: { href: "https://example.test/" }, history: { replaceState() {}, pushState() {} }, addEventListener() {},
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
  // A screen reader hears which claim the records are for.
assert.equal(tail[0].querySelector("a").textContent, "See the records for Earlier report");
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
  assert.equal(about.lastElementChild.querySelector("a").textContent, "See the records for Earlier report");
});
