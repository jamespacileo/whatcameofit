// The lookup box in a browser, on the site built and indexed from tests/bundle (real pair
// pages from the lab's recorded slice) and the synthetic trial listing.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtemp, readFile, rm, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { chromium, expect } from "@playwright/test";

const site = fileURLToPath(new URL("../", import.meta.url));
const origin = "http://localhost";
const lookup = "/api/lookup";
// A pair of the bundle with one trial, and a trial two pairs hold.
const PAIR = { address: "ambroxol--dementia", title: "Ambroxol for dementia", word: "ambroxol", status: "Trial registered" };
const SHARED_TRIAL = { id: "NCT05256017", pairs: ["acoziborole--infections", "acoziborole--trypanosomiasis-african"] };
let work;
let dist;
let browser;

before(async () => {
  work = await mkdtemp(path.join(os.tmpdir(), "thenwhat-built-search-"));
  dist = path.join(work, "dist");
  const env = {
    ...process.env,
    ASTRO_TELEMETRY_DISABLED: "1",
    PAIRS_BUNDLE: path.join(site, "tests/bundle"),
    LOOKUP_URL: lookup,
    LISTED_TRIAL_PAGES: "1",
    TRIALS_LISTING_FILE: path.join(site, "tests/fixture-trials-listing.json"),
  };
  execFileSync(process.execPath, ["node_modules/astro/bin/astro.mjs", "build", "--outDir", dist], { cwd: site, env });
  // The box searches the lookup file and the search detail: no index is built (design decision 2).
  browser = await chromium.launch();
});

after(async () => {
  try {
    await browser?.close();
  } finally {
    if (work) await rm(work, { recursive: true, force: true });
  }
});

// Serve the build's actual assets under a secure local origin. Any other request
// is blocked, including a visit to a provider or a source article.
async function openPage(t, options = {}) {
  const context = await browser.newContext({
    serviceWorkers: "block",
    permissions: ["clipboard-read", "clipboard-write"],
    ...options,
  });
  t.after(() => context.close());
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== origin) return route.abort();
    const candidate = path.join(dist, decodeURIComponent(url.pathname));
    if (path.relative(dist, candidate).startsWith("..")) return route.abort();
    for (const file of [candidate, path.join(candidate, "index.html")]) {
      if ((await stat(file).catch(() => undefined))?.isFile()) {
        return route.fulfill({ path: file });
      }
    }
    return route.fulfill({ status: 404 });
  });
  return context.newPage();
}

const field = (page) => page.locator("#query");
const searchHeading = (page, words) => page.getByRole("heading", { name: `Results for “${words}”`, exact: true });

async function submit(page, words) {
  await field(page).fill(words);
  await page.getByRole("button", { name: "Look up", exact: true }).click();
}

test("the home page's example leads to the pair it names, with its status and its trial", async (t) => {
  const page = await openPage(t);
  await page.goto(origin);
  // The example the box offers is a treatment the bundle holds.
  const placeholder = await field(page).getAttribute("placeholder");
  const example = placeholder.replace("https://… or ", "");
  assert.notEqual(example, placeholder);
  await submit(page, example);
  await expect(searchHeading(page, example)).toBeVisible();
  await expect(page.locator("#results a[href]").first()).toHaveAttribute("href", /^\/[a-z0-9-]+--[a-z0-9-]+$/);
});

test("a treatment's name finds its pair, counted in pages and never called a claim", async (t) => {
  const page = await openPage(t);
  await page.goto(origin);
  await submit(page, PAIR.word);
  await expect(searchHeading(page, PAIR.word)).toBeVisible();
  await expect(page.getByText("1 page", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: PAIR.title, exact: true }).getByRole("link")).toHaveAttribute("href", `/${PAIR.address}`);
  await expect(page.locator("#results").getByText(PAIR.status, { exact: true }).first()).toBeVisible();
  await expect(page.locator("#results")).not.toContainText(/claim/i);
  // The search is in the address, so it can be shared and reopened.
  await page.reload();
  await expect(page.getByRole("heading", { name: PAIR.title, exact: true })).toBeVisible();
});

test("a registry number leads to every pair that holds the trial", async (t) => {
  const page = await openPage(t);
  await page.goto(origin);
  await submit(page, SHARED_TRIAL.id);
  await expect(page.getByText("On record on 2 pages", { exact: true })).toBeVisible();
  for (const address of SHARED_TRIAL.pairs) {
    await expect(page.locator(`#results a[href="/${address}"]`).first()).toBeVisible();
  }
  await expect(page.locator("#results")).toContainText("A trial on record is not a treatment option.");
  await expect(page.locator("#results")).not.toContainText(/claim/i);
});

test("words nothing holds say so and lead to the topics", async (t) => {
  const page = await openPage(t);
  await page.goto(origin);
  await submit(page, "zzzzqq");
  await expect(page.getByText("Nothing tracked here matches “zzzzqq”.")).toBeVisible();
  await expect(page.locator('#results a[href="/topics"]')).toBeVisible();
  await expect(page.locator("#results")).not.toContainText(/claim/i);
});

// The search over the pairs reads the lookup file and the search detail (design decision 2):
// it answers as the index did.
test("a word no pair holds is named and left out, and the rest are still found", async (t) => {
  const page = await openPage(t);
  await page.goto(origin);
  await submit(page, "lung cancercancer");
  await expect(searchHeading(page, "lung cancercancer")).toBeVisible();
  await expect(page.locator("#results .search-unheld")).toContainText("cancercancer");
  await expect(page.locator('#results a[href="/tulisokibart--lung-diseases-interstitial"]').first()).toBeVisible();
});

test("the closest pair comes first: a word in a headline before one in a trial's title", async (t) => {
  // "overweight" is apitegromab--overweight's condition, and a word in a trial title of
  // apitegromab--obesity, which comes first in the bundle.
  const page = await openPage(t);
  await page.goto(origin);
  await submit(page, "overweight");
  await expect(searchHeading(page, "overweight")).toBeVisible();
  await expect(page.locator("#results h3 a[href]").first()).toHaveAttribute("href", "/apitegromab--overweight");
});

test("a search of no words finds nothing, and words in quotation marks must come in order", async (t) => {
  const page = await openPage(t);
  await page.goto(origin);
  await submit(page, "???");
  await expect(page.getByText("Nothing tracked here matches “???”.")).toBeVisible();
  await submit(page, '"diseases lung"');
  await expect(page.getByText("Nothing tracked here matches “\"diseases lung\"”.")).toBeVisible();
  await submit(page, '"lung diseases"');
  await expect(page.locator('#results a[href="/tulisokibart--lung-diseases-interstitial"]').first()).toBeVisible();
});

test("an article the site does not track is sent nowhere until the reader asks", async (t) => {
  const page = await openPage(t);
  const requests = [];
  await page.route(`${origin}${lookup}`, (route) => {
    requests.push(route.request().url());
    return route.abort();
  });
  await page.goto(`${origin}/for/clinicians`);
  await submit(page, "https://news.example.org/a-report-we-do-not-track");
  await expect(page.getByText(/This article is not one we track/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Search the trial registry" })).toBeVisible();
  assert.deepEqual(requests, []);
  // The address typed stays out of the page's own address and history.
  assert.doesNotMatch(page.url(), /news\.example\.org/);
  assert.doesNotMatch(await page.evaluate(() => JSON.stringify(history.state)), /news\.example\.org/);
});

test("live article search waits for consent and keeps independent results and confidence separate", async (t) => {
  const page = await openPage(t);
  const untracked = "https://news.example.org/synthetic-roundup";
  const requests = [];
  await page.route(`${origin}${lookup}`, (route) => {
    requests.push(route.request().postDataJSON());
    return route.fulfill({ json: { about_a_treatment: true, claims: [
      { about_a_treatment: true, treatment: "EX-1", condition: "Condition one", tracked: [], candidates: [
        { id: "NCT00000001", title: "Synthetic trial one", url: "https://clinicaltrials.gov/study/NCT00000001", score: .94, answer: "match", phases: ["PHASE2"], state: "RECRUITING" },
      ] },
      { about_a_treatment: true, treatment: "EX-2", condition: "Condition two", tracked: [], candidates: [
        { id: "NCT00000002", title: "Synthetic trial two", url: "https://clinicaltrials.gov/study/NCT00000002", score: null, agrees: ["stated"], phases: ["PHASE1"], state: "COMPLETED" },
      ] },
    ] } });
  });
  await page.goto(origin);
  await submit(page, untracked);
  const ask = page.getByRole("button", { name: "Search the trial registry" });
  await expect(ask).toBeVisible();
  assert.deepEqual(requests, []);
  await ask.click();
  await expect(page.getByRole("heading", { name: "EX-1", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "EX-2", exact: true })).toBeVisible();
  const scored = page.getByRole("listitem").filter({ has: page.getByRole("link", { name: "Synthetic trial one" }) });
  const unscored = page.getByRole("listitem").filter({ has: page.getByRole("link", { name: "Synthetic trial two" }) });
  await expect(scored.getByText("94% match confidence")).toBeVisible();
  await page.getByText(/^Other records mentioned in the report;/).click();
  await expect(unscored.getByText("Match confidence unavailable")).toBeVisible();
  const meaning = scored.getByText(/not a verified probability/);
  await expect(meaning).toBeHidden();
  await scored.getByText("94% match confidence").click();
  await expect(meaning).toBeVisible();
  assert.deepEqual(requests, [{ url: untracked, claimResults: true }]);
});

test("an identifier and ordinary words both find trials in the built listing", async (t) => {
  const page = await openPage(t);
  await page.goto(origin);
  const trial = page.getByRole("link", { name: /A synthetic study of zetamab in synthetic lung condition/ });
  await submit(page, "NCT09000001");
  await expect(trial).toBeVisible();
  await submit(page, "zetamab");
  await expect(page.getByText(/Nothing tracked here matches/)).toBeVisible();
  await expect(trial).toBeVisible();
  await expect(page.getByRole("link", { name: /Zetamab with standard care in synthetic kidney condition/ })).toBeVisible();
});

test("the shared stylesheet defines one scale and uses it for font declarations", async (t) => {
  const page = await openPage(t);
  const css = await readFile(new URL("../src/styles/global.css", import.meta.url), "utf8");
  const problems = await page.evaluate((css) => {
    // The browser's parser checks the shared declarations, including rules a fixture
    // page does not use.
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(css);
    const textRoles = ["micro", "xs", "s", "m", "body", "l", "xl", "wordmark", "heading", "status"];
    const sizes = new Set([...textRoles.map((role) => `--text-${role}`), "--label-size", "--note-size"]);
    const definitions = new Map([...sizes, "--radius-s", "--row-pad", "--row-rule", "--panel-pad", "--label-col"]
      .map((token) => [token, 0]));
    const problems = [];
    function check(rules) {
      for (const rule of rules) {
        if (rule.style) {
          for (const [token, count] of definitions) {
            if (rule.style.getPropertyValue(token).trim()) definitions.set(token, count + 1);
          }
          const size = rule.style.getPropertyValue("font-size").trim();
          const token = size.match(/^var\(\s*(--[\w-]+)\s*\)$/)?.[1];
          if (size && !sizes.has(token) && !size.startsWith("clamp(")
            && !["inherit", "0.85em", "106.25%"].includes(size)) {
            problems.push(`${rule.selectorText ?? rule.keyText}: ${size}`);
          }
        }
        if (rule.cssRules) check(rule.cssRules);
      }
    }
    check(sheet.cssRules);
    for (const [token, count] of definitions) {
      if (count !== 1) problems.push(`${token} has ${count} definitions`);
    }
    return problems;
  }, css);
  assert.deepEqual(problems, [], "shared style declarations outside the scale");
});

// The explore page (openspec pairs-site, task 6.2): picks from any tree, at any level, filtered
// in the browser from one built file. A broad node includes what is beneath it; picks in two
// trees must both match; the picks live in the address.
test("the explore page lists the pairs that match picks from two trees, a broad node including what is beneath it", async (t) => {
  const index = JSON.parse(await readFile(path.join(dist, "data/explore.json"), "utf8"));
  const inTree = (key, id) => index.pairs.filter((pair) => (pair.at[key] ?? []).includes(id)).map((pair) => pair.address).sort();
  const page = await openPage(t);
  await page.goto(`${origin}/explore`);
  await expect(page.locator("[data-explore-status]")).toHaveText(`${index.pairs.length} treatments and conditions match.`);

  // A broad MeSH node, found by name: every pair at or beneath it.
  await page.locator("[data-explore-search]").fill("nervous system");
  await page.locator('[data-pick="body-system:nervous-system-diseases"]').click();
  const nervous = inTree("body-system", "nervous-system-diseases");
  assert.ok(nervous.length > 1 && nervous.includes("ambroxol--dementia"), nervous.join(", "));
  const listed = async () => (await page.locator("[data-explore-results] [data-pair]").evaluateAll((rows) => rows.map((row) => row.dataset.pair))).sort();
  await expect(page.locator("[data-explore-results] [data-pair]")).toHaveCount(nervous.length);
  assert.deepEqual(await listed(), nervous);

  // And a kind of treatment: both must match.
  await page.locator('[data-tree="kind"] input[data-node="drug"]').check();
  const both = nervous.filter((address) => inTree("kind", "drug").includes(address));
  await expect(page.locator("[data-explore-results] [data-pair]")).toHaveCount(both.length);
  assert.deepEqual(await listed(), both);
  assert.equal(new URL(page.url()).search, "?body-system=nervous-system-diseases&kind=drug");

  // The address alone brings the same picks back, and a chip removes one.
  const again = await openPage(t);
  await again.goto(`${origin}/explore?body-system=nervous-system-diseases&kind=drug`);
  await expect(again.locator("[data-explore-results] [data-pair]")).toHaveCount(both.length);
  await again.locator('[data-explore-chips] [data-pick="kind:drug"]').click();
  await expect(again.locator("[data-explore-results] [data-pair]")).toHaveCount(nervous.length);
  // Its canonical address carries no picks.
  const canonical = new URL(await again.locator('link[rel="canonical"]').getAttribute("href"));
  assert.equal(canonical.search, "");
  assert.match(canonical.pathname, /^\/explore\/?$/);
});
