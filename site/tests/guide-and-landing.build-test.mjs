// The guide, method, about and audience pages share one build of tests/bundle (openspec
// landing-pages-and-guide).
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { parseHTML } from "linkedom";
import { AUDIENCES } from "../src/lib/audiences.ts";
import { METHOD_SECTIONS, statusSlug } from "../src/lib/guide.ts";
import { readBundle } from "../src/lib/bundle.ts";
import { builtAhead } from "../src/lib/pair-view.ts";
import { STAGE_PATH, STATUS_LABELS, STATUS_MEANINGS } from "../src/lib/status.ts";

const bundle = readBundle("tests/bundle");
const pairs = Object.values(bundle.pages.PairPage);
// A pair whose page the build makes ahead.
const built = pairs.find((file) => builtAhead(file));
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
      PAIRS_BUNDLE: "tests/bundle",
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
  for (const file of ["index.html", `${built.row.pair.address}/index.html`, "how-it-works/index.html"]) {
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

test("every status has a published entry with its label and meaning, and cites its rule", () => {
  for (const code of codes) {
    const html = page(`guide/${statusSlug(code)}/index.html`);
    const words = text(html);
    assert.ok(words.includes(STATUS_LABELS[code]) && words.includes(STATUS_MEANINGS[code]), code);
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

test("the guide is reached from the method page, the footer and the sitemap", () => {
  const method = page("how-it-works/index.html");
  for (const code of codes) assert.ok(method.includes(`href="/guide/${statusSlug(code)}"`), code);
  const html = page(`${built.row.pair.address}/index.html`);
  for (const href of ["/guide", "/about", ...AUDIENCES.map((audience) => `/for/${audience}`)]) {
    assert.ok(html.split("<footer")[1].includes(`href="${href}"`), `the footer does not link ${href}`);
  }
  const sitemap = page("sitemap.xml");
  for (const path of ["/guide", "/guide/no-signal", "/about", "/for/journalists"]) {
    assert.ok(sitemap.includes(`${path}</loc>`), `${path} is not in the sitemap`);
  }
});

test("the about page shows a pair beside its status, counts from the bundle and ends with the lookup", () => {
  const html = page("about/index.html");
  const words = text(html.split("<main")[1].split("</main>")[0]);
  // The topics whose own file lists a pair with a page, as the topics page counts them.
  const published = new Set(pairs.map((file) => file.row.pair.address));
  const topics = Object.values(bundle.pages.PairTopicPage).filter((file) => file.pairs.some((row) => published.has(row.pair.address))).length;
  assert.ok(words.includes(`${pairs.length} treatments and conditions are followed in ${topics} topics`), words.slice(-900));
  assert.ok(Object.values(STATUS_LABELS).some((label) => html.includes(`class="status"`) && words.includes(label)));
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
  const clinicians = page("for/clinicians/index.html");
  assert.ok(clinicians.includes('id="search"') && clinicians.includes('id="lookup-sentences"'));
  assert.ok(text(clinicians).includes("A registered clinical trial is not a treatment option."));
  const researchers = page("for/researchers/index.html");
  const first = researchers.split("</section>")[0];
  assert.ok(first.includes('href="/data/pairs.json"') && first.includes("Creative Commons") && first.includes("gathered"));
  assert.ok(!page("index.html").includes('id="lookup-sentences"'));
});
