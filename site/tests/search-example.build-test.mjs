// The example words in the lookup field lead to the claim they were chosen from
// (openspec search-answer-in-step). A site is built from a synthetic export and
// indexed; the home page's own script then answers its own example, with the built
// search index and the built files behind it. Nothing is asked of the network but
// this test's own server of the built site.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import { stripTypeScriptTypes } from "node:module";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import vm from "node:vm";
import { after, before, test } from "node:test";
import { parseHTML } from "linkedom";
import { SUGGEST_SUBJECT, contactLink } from "../src/lib/contact.mjs";
import { exampleClaims } from "../src/lib/extension-page.ts";
import { LIVE, describeAnswer, refusalMessage, textWouldHelp } from "../src/lib/live-lookup.mjs";
import { closestClaims, readAddress } from "../src/lib/lookup-match.mjs";
import { ranked, searchExample, searchWords, wordPattern, wordsIn } from "../src/lib/search-order.ts";
import { suggest, suggestParts, suggestWords } from "../src/lib/suggest.ts";
import {
  NOT_AN_OPTION, NO_REPORT, PHASE_WORDS, SEARCH_WORDS, STATE_WORDS, changedShort, findListed, listingWords, registryDate,
  searchListing, setNote,
} from "../src/lib/trial-page.mjs";
import { PARTS_SEARCHED_AT_ONCE, partFor } from "../src/lib/trial-listing-parts.mjs";

const work = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-example-"));
const dist = path.join(work, "dist");
const exportFile = path.join(work, "export.json");

// The fixture's claims are named so that none passes the example's rule. One is given
// a treatment with a plain name of its own, said in its headline.
const data = JSON.parse(fs.readFileSync(new URL("./fixture-export.json", import.meta.url), "utf8"));
const named = data.claims.find((claim) => claim.slug === "phase-claim");
named.intervention.name = "Fixturamab";
named.headline = "Fixturamab was reported to start a trial";
fs.writeFileSync(exportFile, JSON.stringify(data));

let server;
let origin;

before(async () => {
  const env = { ...process.env, EXPORT_FILE: exportFile, ASTRO_TELEMETRY_DISABLED: "1" };
  const built = spawnSync("npx", ["astro", "build", "--outDir", dist], { env, encoding: "utf8" });
  assert.equal(built.status, 0, built.stdout + built.stderr);
  const indexed = spawnSync("npx", ["pagefind", "--site", dist], { env, encoding: "utf8" });
  assert.equal(indexed.status, 0, indexed.stdout + indexed.stderr);
  server = http.createServer((request, response) => {
    const asked = decodeURIComponent(new URL(request.url, "http://built.test").pathname);
    fs.readFile(path.join(dist, asked), (error, body) => {
      response.writeHead(error ? 404 : 200);
      response.end(error ? undefined : body);
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
});

after(() => server?.close());

test("the field's example is the rule's choice, and searching for it leads with that claim", async () => {
  const chosen = searchExample(exampleClaims(data.claims));
  assert.deepEqual(chosen, { words: "fixturamab", slug: "phase-claim" });

  const { document, window } = parseHTML(fs.readFileSync(path.join(dist, "index.html"), "utf8"));
  const field = document.querySelector("#query");
  assert.equal(field.getAttribute("placeholder"), `https://… or ${chosen.words}`);

  // The page's own script, with the built index and the built files behind it.
  const pagefind = await import(pathToFileURL(path.join(dist, "pagefind/pagefind.js")).href);
  await pagefind.options({ basePath: `${origin}/pagefind/` });
  const source = fs.readFileSync(new URL("../src/components/Lookup.astro", import.meta.url), "utf8")
    .match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace(/^\s*import .*;\s*$/gm, "")
    .replace("await import(/* @vite-ignore */ indexUrl)", "await loadSearchIndex(indexUrl)");
  for (const node of document.querySelectorAll("*")) {
    node.getBoundingClientRect = () => ({ top: 0 });
    node.scrollIntoView = () => {};
  }
  vm.runInNewContext(stripTypeScriptTypes(source), {
    document, URL, setTimeout, BRAND: { name: "Example tracker" }, readAddress, closestClaims,
    suggest, suggestParts, suggestWords, ranked, searchWords, wordPattern, wordsIn,
    LIVE, describeAnswer, refusalMessage, textWouldHelp, SUGGEST_SUBJECT, contactLink,
    NOT_AN_OPTION, NO_REPORT, PHASE_WORDS, SEARCH_WORDS, STATE_WORDS, changedShort, findListed, listingWords, registryDate,
    searchListing, setNote, PARTS_SEARCHED_AT_ONCE, partFor,
    location: { href: `${origin}/`, origin }, history: { replaceState() {}, pushState() {} }, addEventListener() {},
    innerHeight: 800, matchMedia: () => ({ matches: false }),
    loadSearchIndex: async () => pagefind,
    fetch: (address, options) => fetch(new URL(address, origin), options),
  });

  field.value = chosen.words;
  document.querySelector("#search").dispatchEvent(new window.Event("submit", { cancelable: true }));
  const answer = document.querySelector("[data-search-answer]");
  for (let turn = 0; turn < 200 && !answer.querySelector(".hit-row"); turn++) await new Promise((resolve) => setTimeout(resolve, 25));

  const first = answer.querySelector(".hit-row");
  assert.ok(first, "the example words found no claim");
  assert.equal(first.querySelector(".row-label").textContent, "Closest match");
  assert.equal(first.querySelector("a.hit-title").getAttribute("href"), `/${chosen.slug}`);
  assert.equal(answer.querySelector(".search-unheld"), null);
});
