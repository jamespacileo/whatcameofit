// The guide, method, year, about, audience and topic pages share one build of
// tests/fixture-export.json (openspec landing-pages-and-guide).
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { parseHTML } from "linkedom";
import { AUDIENCES } from "../src/lib/audiences.ts";
import { METHOD_SECTIONS, statusSlug } from "../src/lib/guide.ts";
import { STAGE_PATH, STATUS_LABELS, STATUS_MEANINGS, topicSummary } from "../src/lib/status.ts";

const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
const codes = Object.keys(STATUS_LABELS);
const files = fs.readdirSync("src/guide").filter((file) => file.endsWith(".md"));

const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-guide-"));
const page = (relative) => fs.readFileSync(path.join(dist, relative), "utf8");
const exists = (relative) => fs.existsSync(path.join(dist, relative));
const SUGGEST = "mailto:suggest@example.org";

before(() => {
  const result = spawnSync(process.execPath, ["node_modules/astro/bin/astro.mjs", "build", "--outDir", dist], {
    env: {
      ...process.env,
      EXPORT_FILE: "tests/fixture-export.json",
      SUGGEST_URL: SUGGEST,
      CORRECTIONS_URL: "mailto:corrections@example.org",
      CHROME_STORE_URL: "",
      SAFARI_STORE_URL: "",
      ASTRO_TELEMETRY_DISABLED: "1",
    },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
});
after(() => fs.rmSync(dist, { recursive: true, force: true }));

const text = (html) => html.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
const count = (code) => fixture.claims.filter((claim) => claim.status.code === code).length;

test("the method page explains the statuses and what is counted", () => {
  const html = page("how-it-works/index.html");
  const { document } = parseHTML(html);
  for (const section of Object.keys(METHOD_SECTIONS)) {
    assert.ok(document.getElementById(section), `the method page has no section ${section}`);
  }
  const words = text(html);
  for (const label of Object.values(STATUS_LABELS)) {
    assert.ok(words.includes(label), `${label} is missing`);
  }
  assert.match(words, /This site gives no medical advice/);
  assert.match(words, /counts requests and errors/);
});

test("a site with no configured store publishes no extension page or link", () => {
  assert.ok(!exists("extension/index.html"), "the extension page was built with no store");
  for (const file of ["index.html", "quiet-claim/index.html", "how-it-works/index.html"]) {
    const { document } = parseHTML(page(file));
    assert.equal(document.querySelector('a[href="/extension"]'), null, `${file} links a page that does not exist`);
  }
});

test("the method video waits to be played and carries a date and transcript", () => {
  const { document } = parseHTML(page("how-it-works/index.html"));
  const video = document.querySelector("main video");
  assert.ok(video, "the method video is missing");
  assert.ok(video.hasAttribute("controls"));
  assert.equal(video.getAttribute("preload"), "none");
  assert.ok(!video.hasAttribute("autoplay"));
  assert.match(video.querySelector("source")?.getAttribute("src") ?? "", /^\/video\/explainer\.mp4(?:\?|$)/);
  assert.ok(exists("video/explainer.mp4") && exists("video/explainer-poster.jpg"));
  assert.match(document.querySelector("main").textContent, /as the registries showed them in November 2026/);
  assert.match(document.querySelector("main").textContent, /What the video says/);
});

test("each year page lists the claims first reported that year", () => {
  const years = new Set(fixture.claims.map((claim) => claim.first_reported_date?.slice(0, 4)).filter(Boolean));
  assert.ok(years.size > 0);
  for (const year of years) {
    const { document } = parseHTML(page(`year/${year}/index.html`));
    assert.match(document.querySelector("h1").textContent, new RegExp(`First reported in ${year}`));
    const links = new Set([...document.querySelectorAll("main a[href]")].map((link) => link.getAttribute("href")));
    for (const claim of fixture.claims) {
      assert.equal(links.has(`/${claim.slug}`), claim.first_reported_date?.startsWith(year) ?? false, `${claim.slug} in ${year}`);
    }
  }
  assert.ok(!exists("year/2020/index.html"));
  assert.ok(!exists("year/1999/index.html"));
});

test("every status has a published entry with its label, meaning, count and list", () => {
  for (const code of codes) {
    const html = page(`guide/${statusSlug(code)}/index.html`);
    const words = text(html);
    assert.ok(words.includes(STATUS_LABELS[code]) && words.includes(STATUS_MEANINGS[code]), code);
    if (count(code) === 0) {
      assert.ok(words.includes("No tracked claim has this status now."), code);
    } else {
      assert.ok(words.includes(`${count(code)} of ${fixture.claims.length} tracked`), code);
      assert.ok(html.includes(code === "approved" ? 'href="/it-happened"' : `href="/?status=${code}"`), code);
    }
    assert.ok(html.includes('href="/how-it-works#how-a-status-is-set"'), `${code} cites no rule`);
  }
});

test("an unchecked entry says so after its answer, and offers only the corrections link", () => {
  const html = page("guide/trial-registry/index.html");
  const answer = html.indexOf("A trial registry is a public database");
  const notice = html.indexOf("This entry has not yet been checked by a person");
  assert.ok(answer > 0 && notice > answer, "the notice is not under the answer");
  assert.ok(html.includes("Report an error"));
  assert.ok(!/<form|<textarea/.test(html.split("<main")[1].split("</main>")[0]), "an entry offers a way to write into it");
  const sources = html.split('id="sources"')[1];
  assert.match(sources, /https:\/\/clinicaltrials\.gov\/about-site\/disclaimer[\s\S]*Checked 14\D{1,8}Nov\D{1,8}2026/);
  assert.match(html, /"@type":"DefinedTerm"/);
});

test("the index lists every entry under its shelf, statuses in path order", () => {
  const html = page("guide/index.html");
  for (const file of files) assert.ok(html.includes(`href="/guide/${file.replace(".md", "")}"`), file);
  const places = STAGE_PATH.map((code) => html.indexOf(`href="/guide/${statusSlug(code)}"`));
  assert.deepEqual(places, [...places].sort((a, b) => a - b));
  assert.ok(places.at(-1) < html.indexOf(`href="/guide/${statusSlug("retracted")}"`));
  assert.ok(html.includes('id="guide-filter"') && html.includes('"@type":"DefinedTermSet"'));
});

test("the guide is reached from the claim page, the method page, the footer and the sitemap", () => {
  const claim = fixture.claims[0];
  const html = page(`${claim.slug}/index.html`);
  assert.ok(html.includes(`href="/guide/${statusSlug(claim.status.code)}"`), "the status panel has no guide link");
  assert.ok(html.includes(STATUS_MEANINGS[claim.status.code]), "the meaning left the claim page");
  const quiet = fixture.claims.find((held) => held.status.overlay_years !== null);
  if (quiet) assert.ok(page(`${quiet.slug}/index.html`).includes('href="/guide/no-signal"'));
  const unchecked = fixture.claims.find((held) => !held.checked_by_person);
  if (unchecked) assert.ok(page(`${unchecked.slug}/index.html`).includes('href="/guide/checked-by-a-person"'));
  const method = page("how-it-works/index.html");
  for (const code of codes) assert.ok(method.includes(`href="/guide/${statusSlug(code)}"`), code);
  for (const href of ["/guide", "/about", ...AUDIENCES.map((audience) => `/for/${audience}`)]) {
    assert.ok(html.split("<footer")[1].includes(`href="${href}"`), `the footer does not link ${href}`);
  }
  const sitemap = page("sitemap.xml");
  for (const path of ["/guide", "/guide/no-signal", "/about", "/for/journalists"]) {
    assert.ok(sitemap.includes(`${path}</loc>`), `${path} is not in the sitemap`);
  }
});

test("a topic page opens with what it is, the summary and the ways to pass it on, before its claims", () => {
  const vertical = fixture.verticals.find((held) => fixture.claims.some((claim) => claim.vertical === held.slug));
  const html = page(`topic/${vertical.slug}/index.html`);
  const order = ['class="what-this-is"', 'class="lede"', "data-share", 'data-copy="topic-sentence"', `/changes/topic/${vertical.slug}.xml`, "<table"];
  const places = order.map((mark) => html.indexOf(mark));
  assert.ok(places.every((place) => place > 0), `missing: ${order.filter((_, index) => places[index] < 0)}`);
  assert.deepEqual(places, [...places].sort((a, b) => a - b));
  const counts = new Map();
  for (const claim of fixture.claims.filter((held) => held.vertical === vertical.slug)) {
    counts.set(claim.status.code, (counts.get(claim.status.code) ?? 0) + 1);
  }
  const copied = html.match(/<span id="topic-sentence" hidden[^>]*>([^<]*)</)[1];
  assert.ok(copied.replaceAll("&#39;", "'").startsWith(topicSummary(counts)), copied);
  assert.match(copied, /Checked [A-Z][a-z]+ \d{4}\. https?:\/\/\S+\/topic\//);
  assert.ok(html.includes(`/og/topic/${vertical.slug}.png`) && exists(`og/topic/${vertical.slug}.png`));
  assert.ok(html.includes("Suggest a headline"), "the page does not end on the suggestion");
});

test("the about page shows a headline beside its status, counts from the export and ends with the lookup", () => {
  const html = page("about/index.html");
  const words = text(html.split("<main")[1].split("</main>")[0]);
  const topics = fixture.verticals.filter((held) => fixture.claims.some((claim) => claim.vertical === held.slug)).length;
  const claims = fixture.claims.length;
  assert.ok(words.includes(`${claims} ${claims === 1 ? "claim is" : "claims are"} tracked in ${topics} ${topics === 1 ? "topic" : "topics"}`), words.slice(-900));
  assert.ok(Object.values(STATUS_LABELS).some((label) => html.includes(`class="status"`) && words.includes(label)));
  assert.match(words, /“[^”]+”/, "no outlet's title in quotation marks");
  assert.ok(html.includes("https://doi.org/10.1371/journal.pone.0172650"));
  for (const href of ["/how-it-works#how-a-status-is-set", "/data", "/privacy"]) assert.ok(html.includes(`href="${href}"`), href);
  assert.ok(html.lastIndexOf('id="search"') > html.indexOf('id="who"'), "the lookup is not the last section");
  assert.ok(!/\b(testimonial|trusted by|rated|rating)\b/i.test(words));
});

test("each audience page opens on its tool and states its limits", () => {
  const journalists = page("for/journalists/index.html");
  assert.match(journalists, /<iframe[^>]*src="\/embed\/[^"]+"[^>]*width="440"[^>]*height="420"/);
  assert.ok(journalists.includes("&lt;iframe src=") && journalists.includes('data-copy="picker-snippet"'));
  assert.ok(text(journalists).includes("Outlets are never ranked or compared."));
  assert.ok(journalists.includes("Suggest a headline"), "no result has nowhere to go");
  const clinicians = page("for/clinicians/index.html");
  assert.ok(clinicians.includes('id="search"') && clinicians.includes('id="lookup-sentences"'));
  assert.ok(text(clinicians).includes("A registered clinical trial is not a treatment option."));
  const researchers = page("for/researchers/index.html");
  const first = researchers.split("</section>")[0];
  assert.ok(first.includes('href="/data/claims.json"') && first.includes("Creative Commons") && first.includes("Built"));
  assert.ok(!page("index.html").includes('id="lookup-sentences"'));
});
