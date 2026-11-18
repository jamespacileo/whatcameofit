// Search and claim styling use the same built, indexed fixture.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtemp, readFile, rm, stat, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { chromium, expect } from "@playwright/test";

const site = fileURLToPath(new URL("../", import.meta.url));
const origin = "http://localhost";
const article = "https://uk.news.example.org/3";
const example = "Fixturamab was reported to start a trial";
const lookup = "/api/lookup";
let work;
let dist;
let browser;

async function fixture() {
  const data = JSON.parse(await readFile(new URL("./fixture-export.json", import.meta.url), "utf8"));
  const phase = data.claims.find(({ slug }) => slug === "phase-claim");
  phase.intervention.name = "Fixturamab";
  phase.headline = example;
  phase.background.push({
    kind: "drug",
    fit: "exact",
    label: "Fixturamab",
    definition: null,
    url: "https://targets.example/drug/synthetic",
    source: "opentargets",
    external_id: "synthetic",
    version: null,
    score: null,
    molecule_kind: "antibody",
    reasons: [{ code: "drug_name_equals_name", name: "fixturamab" }],
    decided_by: "rule",
    read_at: "2026-11-14T09:00:00Z",
  });
  data.card_sources.push({
    name: "opentargets",
    title: "Example Targets",
    credit: "Example Targets",
    licence: "CC0 1.0",
    url: "https://targets.example/",
    terms_url: "https://targets.example/terms",
    in_data_file: true,
  });

  data.verticals.push({ slug: "skin", title: "Skin conditions" });
  const quiet = data.claims.find(({ slug }) => slug === "quiet-claim");
  for (let number = 1; number <= 42; number++) {
    const slug = `coralpulse-${number}`;
    const headline = `Coralpulse report ${number}`;
    data.claims.push({
      ...quiet,
      slug,
      headline,
      intervention: { name: `Coralpulse compound ${number}`, synonyms: [] },
      vertical: number <= 22 ? "gum-disease" : "skin",
      articles: [{ ...quiet.articles[0], title: headline, url: `https://news.example.org/${slug}` }],
      events: [],
      promises: [],
      matches: [],
      reported_statements: [],
    });
  }
  return data;
}

before(async () => {
  work = await mkdtemp(path.join(os.tmpdir(), "thenwhat-built-search-"));
  dist = path.join(work, "dist");
  const exportFile = path.join(work, "export.json");
  await writeFile(exportFile, JSON.stringify(await fixture()));
  const env = {
    ...process.env,
    ASTRO_TELEMETRY_DISABLED: "1",
    EXPORT_FILE: exportFile,
    LOOKUP_URL: lookup,
    LISTED_TRIAL_PAGES: "1",
    TRIALS_LISTING_FILE: path.join(site, "tests/fixture-trials-listing.json"),
  };
  execFileSync(process.execPath, ["node_modules/astro/bin/astro.mjs", "build", "--outDir", dist], { cwd: site, env });
  execFileSync("node_modules/.bin/pagefind", ["--site", dist], { cwd: site, env });
  browser = await chromium.launch();
});

after(async () => {
  try {
    await browser?.close();
  } finally {
    if (work) await rm(work, { recursive: true, force: true });
  }
});

// Serve the fixture's actual assets under a secure local origin. Any other request
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

const field = (page) => page.getByRole("combobox");
const searchHeading = (page, words) => page.getByRole("heading", { name: `Results for “${words}”`, exact: true });
const reportLinks = (page) => page.locator("[data-search-answer]")
  .getByRole("heading", { name: /^Coralpulse report \d+$/ }).getByRole("link");

async function submit(page, words) {
  await field(page).fill(words);
  await page.getByRole("button", { name: "Look up", exact: true }).click();
}

test("the home page's example leads to the closest claim in the built index", async (t) => {
  const page = await openPage(t);
  await page.goto(origin);
  await expect(field(page)).toHaveAttribute("placeholder", "https://… or fixturamab");
  await submit(page, "fixturamab");
  await expect(searchHeading(page, "fixturamab")).toBeVisible();
  await expect(page.getByText("Closest match", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: example, exact: true }).getByRole("link")).toHaveAttribute("href", "/phase-claim");
  await expect(page.getByText(/No tracked claim holds/)).toHaveCount(0);
});

test("topic counts include later results, and browser history restores the loaded topic", async (t) => {
  const page = await openPage(t);
  await page.goto(origin);
  await submit(page, "coralpulse");
  await expect(page.getByText("First 20 of 42 tracked claims", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Gum disease 22" }).click();
  await expect(page.getByText("First 20 of 22 in Gum disease, of 42 tracked claims", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Show 2 more" }).click();
  await expect(reportLinks(page)).toHaveCount(22);
  const names = await reportLinks(page).allTextContents();
  assert.equal(new Set(names).size, 22);

  await page.getByRole("button", { name: "Clear search" }).click();
  await expect(page).toHaveURL(`${origin}/`);
  await page.goBack();
  await expect(page).toHaveURL(`${origin}/?q=coralpulse&topic=gum-disease`);
  await expect(page.getByRole("button", { name: "Gum disease 22" })).toHaveAttribute("aria-pressed", "true");
  await expect(reportLinks(page)).toHaveText(names);
  await page.goForward();
  await expect(searchHeading(page, "coralpulse")).toHaveCount(0);
  await expect(field(page)).toHaveValue("");
});

test("a failed page of results preserves the first page and can be retried", async (t) => {
  const page = await openPage(t);
  await page.goto(origin);
  await submit(page, "coralpulse");
  await expect(page.getByText("First 20 of 42 tracked claims", { exact: true })).toBeVisible();
  const first = await reportLinks(page).allTextContents();
  const fragments = "**/pagefind/fragment/*";
  const unavailable = (route) => route.abort();
  await page.route(fragments, unavailable);
  const more = page.getByRole("button", { name: "Show 20 more" });
  await more.click();
  await expect(page.getByRole("status").filter({ hasText: "The next claims could not be read right now." })).toBeVisible();
  await expect(reportLinks(page)).toHaveText(first);
  await page.unroute(fragments, unavailable);
  await more.click();
  await expect(page.getByText("First 40 of 42 tracked claims", { exact: true })).toBeVisible();
  const expanded = await reportLinks(page).allTextContents();
  assert.equal(new Set(expanded).size, 40);
  assert.deepEqual(expanded.slice(0, 20), first);
});

test("an older topic response cannot overwrite the newer selection", { timeout: 20_000 }, async (t) => {
  const page = await openPage(t);
  const started = Promise.withResolvers();
  const release = Promise.withResolvers();
  const delivered = Promise.withResolvers();
  await page.exposeFunction("holdGumDisease", () => {
    started.resolve();
    return release.promise;
  });
  await page.exposeFunction("gumDiseaseDelivered", () => delivered.resolve());
  // Keep real index results. Hold only the older topic at the index's public API.
  // Warm its fragments so that the next browser task runs after its possible redraw.
  await page.route(`${origin}/pagefind/pagefind.js`, (route) => route.fulfill({
    contentType: "text/javascript",
    body: `
      import * as index from "./built-index.js";
      export const filters = index.filters;
      export async function search(words, options) {
        const answer = await index.search(words, options);
        if (options?.filters?.topic !== "gum-disease") return answer;
        const results = await Promise.all(answer.results.map(hit => hit.data()));
        await holdGumDisease();
        setTimeout(() => void gumDiseaseDelivered(), 0);
        return { ...answer, results: results.map(result => ({ data: async () => result })) };
      }
    `,
  }));
  await page.route(`${origin}/pagefind/built-index.js`, (route) => route.fulfill({
    path: path.join(dist, "pagefind/pagefind.js"),
  }));

  await page.goto(origin);
  await submit(page, "coralpulse");
  await expect(searchHeading(page, "coralpulse")).toBeVisible();
  await page.getByRole("button", { name: "Gum disease 22" }).click();
  await started.promise;
  const skin = page.getByRole("button", { name: "Skin conditions 20" });
  await skin.click();
  const chosenCount = page.getByText("20 of 42 tracked claims, in Skin conditions", { exact: true });
  await expect(chosenCount).toBeVisible();
  release.resolve();
  await delivered.promise;

  assert.equal(new URL(page.url()).searchParams.get("topic"), "skin");
  await expect(skin).toHaveAttribute("aria-pressed", "true");
  await expect(chosenCount).toBeVisible();
});

test("a tracked article stays private through history and can be shared from the clinicians' page", async (t) => {
  const page = await openPage(t);
  const pathToPage = `${origin}/for/clinicians`;
  await page.goto(pathToPage);
  await submit(page, article);
  const claim = page.getByRole("heading", { name: example, exact: true });
  await expect(claim).toBeVisible();
  await expect(page.getByText("Phase 2 trial", { exact: true }).first()).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`${pathToPage}/?$`));
  assert.doesNotMatch(await page.evaluate(() => JSON.stringify(history.state)), /uk\.news\.example\.org/);
  await page.goBack();
  await expect(field(page)).toHaveValue("");
  await expect(claim).toHaveCount(0);
  await page.goForward();
  await expect(field(page)).toHaveValue(article);
  await expect(claim).toBeVisible();
  await expect(page.getByRole("link", { name: "Card to post" })).toHaveAttribute("href", "/og/phase-claim.png");
  await page.getByRole("button", { name: "Copy sentence" }).click();
  await expect(page.getByRole("button", { name: "Copied" })).toBeVisible();
  assert.match(await page.evaluate(() => navigator.clipboard.readText()), /Fixturamab.*Phase 2 trial/);
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

async function holdSearchDetail(page) {
  const requested = Promise.withResolvers();
  const released = Promise.withResolvers();
  await page.route("**/search-detail.json", async (route) => {
    requested.resolve();
    await released.promise;
    await route.fallback();
  });
  return { requested: requested.promise, release: released.resolve };
}

test("delayed search details respect the current query and dismissal", { timeout: 20_000 }, async (t) => {
  for (const action of ["keep", "replace", "dismiss"]) {
    const page = await openPage(t);
    const detail = await holdSearchDetail(page);
    try {
      await page.goto(origin);
      await field(page).fill("NCT00000002");
      await detail.requested;
      const trial = page.getByRole("option", { name: /^NCT00000002/ });
      await expect(trial).toBeHidden();
      if (action === "replace") await field(page).fill("Coralpulse");
      if (action === "dismiss") await field(page).press("Escape");
      const arriving = page.waitForResponse("**/search-detail.json");
      detail.release();
      await (await arriving).finished();
      if (action === "keep") {
        await expect(trial).toBeVisible();
      } else if (action === "replace") {
        await expect(page.getByRole("option", { name: /Coralpulse report/ }).first()).toBeVisible();
        await expect(trial).toBeHidden();
      } else {
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        await expect(field(page)).toHaveAttribute("aria-expanded", "false");
      }
    } finally {
      detail.release();
    }
  }
});

test("a selected keyboard suggestion stays selected when detail adds options", { timeout: 20_000 }, async (t) => {
  const page = await openPage(t);
  const detail = await holdSearchDetail(page);
  try {
    await page.goto(origin);
    await field(page).fill("Coralpulse");
    await detail.requested;
    const all = page.getByRole("option", { name: /Search everything for “Coralpulse”/ });
    await expect(all).toBeVisible();
    await field(page).press("ArrowUp");
    await expect(all).toHaveAttribute("aria-selected", "true");
    const previousId = await all.getAttribute("id");
    detail.release();
    await expect(page.getByRole("option", { name: /Coralpulse report/ }).first()).toBeVisible();
    await expect(all).not.toHaveAttribute("id", previousId);
    await expect(all).toHaveAttribute("aria-selected", "true");
    await expect(field(page)).toHaveAttribute("aria-activedescendant", await all.getAttribute("id"));
  } finally {
    detail.release();
  }
});

test("a listing search stays on one release when trial parts change", { timeout: 25_000 }, async (t) => {
  const { columns } = JSON.parse(await readFile(new URL("./fixture-trials-listing.json", import.meta.url), "utf8"));
  const first = "NCT09000001", target = "NCT09000003";
  const title = (name, id) => `Zetamab ${name} ${id}`;
  function listing(name, ids) {
    const bodies = new Map();
    const parts = ids.map((id, at) => {
      const file = `/trials-listing/${name}-${at}.json`;
      bodies.set(file, { columns, trials: [[id, title(name, id), null, [], "under_way", null, [], [], null]] });
      return { file, first: id, last: id, trials: 1 };
    });
    return { name, ids, bodies, manifest: { set: "active-since-2025", columns, total: ids.length, parts } };
  }
  const older = listing("older", [first, target]);
  const newer = listing("newer", ["NCT09000000", first, target]);

  for (const keep of [false, true]) {
    let current = older;
    const byId = await openPage(t);
    const byWords = await openPage(t);
    for (const page of [byId, byWords]) {
      await page.route(/\/trials-listing(?:\/[^/]+)?\.json$/, (route) => {
        const { pathname } = new URL(route.request().url());
        if (pathname === "/trials-listing.json") return route.fulfill({ json: current.manifest });
        const json = current.bodies.get(pathname) ?? (keep && older.bodies.get(pathname));
        return json ? route.fulfill({ json }) : route.fulfill({ status: 404 });
      });
      await page.goto(origin);
      await submit(page, first);
      await expect(page.getByRole("link", { name: title(older.name, first) })).toBeVisible();
    }

    current = newer;
    const expected = keep ? older : newer;
    await submit(byId, target);
    await expect(byId.getByRole("link", { name: title(expected.name, target) })).toBeVisible();

    await submit(byWords, "zetamab");
    if (!keep) {
      const searchAll = byWords.getByRole("button", { name: /search.*trials/i });
      await expect(searchAll).toBeVisible();
      await expect(byWords.locator(".listed-title")).toHaveCount(0);
      await searchAll.click();
    }
    await expect(byWords.locator(".listed-title")).toHaveCount(expected.ids.length);
    assert.deepEqual((await byWords.locator(".listed-title").allTextContents()).sort(),
      expected.ids.map((id) => title(expected.name, id)).sort());
  }
});

const rowSpace = { "padding-top": "var(--row-pad)", "padding-bottom": "var(--row-pad)" };
const divider = "1px solid var(--row-rule)";
const panel = { padding: "var(--panel-pad)", "border-radius": "var(--radius-s)" };
const label = { "font-size": "var(--label-size)" };
const note = { "font-size": "var(--note-size)" };
const tableHead = {
  ...label,
  "font-weight": "600",
  color: "var(--muted)",
  "background-color": "var(--table-head)",
};

// Resolve the shared values through the browser too, so a change to the entire scale
// can pass. Giving an individual row its own value is observable when the scale moves.
async function checkRenderedStyles(page, samples, scale = {}) {
  const readings = await page.evaluate(({ samples, scale }) => {
    for (const [token, value] of Object.entries(scale)) {
      document.documentElement.style.setProperty(token, value);
    }
    const reference = document.body.appendChild(document.createElement("div"));
    const readings = samples.flatMap(([name, selector, properties]) => {
      const target = [...document.querySelectorAll(selector)].find((node) => node.getClientRects().length);
      if (!target) throw new Error(`No rendered ${name} (${selector})`);
      const actual = getComputedStyle(target);
      return Object.entries(properties).map(([property, value]) => {
        reference.style.cssText = "position: absolute; visibility: hidden";
        reference.style.setProperty(property, value);
        return [
          `${name} ${property}`,
          actual.getPropertyValue(property),
          getComputedStyle(reference).getPropertyValue(property),
        ];
      });
    });
    reference.remove();
    return readings;
  }, { samples, scale });
  for (const [name, actual, expected] of readings) assert.equal(actual, expected, name);
}

test("rendered claim rows, labels and panels share their scale", async (t) => {
  // In the supported no-script view the reader sees the section and trial details
  // together. Open the native result disclosure to include its table divider.
  const page = await openPage(t, { javaScriptEnabled: false, viewport: { width: 1440, height: 900 } });
  await page.goto(`${origin}/phase-claim`);
  await page.evaluate(() => {
    document.querySelector("table.result-table").closest("details")?.setAttribute("open", "");
    document.querySelector("#about-glance").showPopover();
  });
  const samples = [
    ["Fact row", "#glance-drug", { ...rowSpace, "border-bottom": divider }],
    ["Entry row", ".entry-rows > li:not(:last-child)", { ...rowSpace, "border-bottom": divider }],
    ["Trial row", ".trial-group .trial-row", rowSpace],
    ["Timetable cell", ".timetable tbody td", { ...rowSpace, "border-top": divider }],
    ["Posted result cell", ".result-table tbody td", { "border-top": divider }],
    ["Fact label", ".fact-sheet dt", { "font-size": "var(--text-m)" }],
    ["Registry label", ".record-fields dt", label],
    ["Trial label", ".trial-facts dt", label],
    ["Match disclosure", ".fact-more .match-why-head", label],
    ["Entry note", ".trial-meta", note],
    ["Timetable source note", ".record .origin", note],
    ["Glance note", ".glance-note", note],
    ["Trial panel", ".trial-facts", panel],
    ["Drug facts panel", ".card-facts", panel],
  ];
  await checkRenderedStyles(page, samples);
  await checkRenderedStyles(page, samples, {
    "--row-pad": "21px",
    "--row-rule": "rgb(90, 100, 110)",
    "--panel-pad": "18px 23px",
    "--radius-s": "16px",
    "--text-m": "16px",
    "--label-size": "15px",
    "--note-size": "14px",
  });
  await page.evaluate(() => {
    document.documentElement.style.setProperty("--label-col", "164px");
  });
  await expect(page.locator("#glance-drug")).toHaveCSS("grid-template-columns", /^164px /);
});

test("timetable, trial and index headings use the same muted table treatment in both themes", async (t) => {
  const page = await openPage(t, { viewport: { width: 1440, height: 900 } });
  for (const colorScheme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme });
    await page.goto(`${origin}/phase-claim`);
    await checkRenderedStyles(page, [
      ["Timetable heading", ".timetable thead th", tableHead],
      ["Trial heading", ".trial-columns-top", tableHead],
    ]);
    await page.goto(`${origin}/topic/gum-disease`);
    await checkRenderedStyles(page, [["Index heading", ".index thead th", tableHead]]);
  }
});

test("rendered claim text stays on a compact type scale on desktop and mobile", async (t) => {
  const page = await openPage(t);
  for (const width of [1440, 375]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`${origin}/phase-claim`);
    const sizes = await page.locator("main").evaluate((main) => {
      const seen = {};
      const text = document.createTreeWalker(main, NodeFilter.SHOW_TEXT);
      const range = document.createRange();
      for (let node = text.nextNode(); node; node = text.nextNode()) {
        const element = node.parentElement;
        const words = node.textContent.trim();
        if (!words || element.closest("script, style, svg, .visually-hidden")) continue;
        range.selectNodeContents(node);
        const style = getComputedStyle(element);
        if (!range.getClientRects().length || style.visibility !== "visible") continue;
        seen[style.fontSize] ??= words.slice(0, 65);
      }
      return seen;
    });
    assert.ok(Object.keys(sizes).length > 1, `${width}px: no claim text was measured`);
    const tooSmall = Object.entries(sizes).filter(([size]) => parseFloat(size) < 12);
    assert.deepEqual(tooSmall, [], `${width}px: readable claim text is at least 12px`);
    assert.ok(Object.keys(sizes).length <= 10, `${width}px: ${JSON.stringify(sizes)}`);
  }
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
