// The method page and the year pages, checked in a build of tests/fixture-export.json.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";
import { STATUS_LABELS } from "../src/lib/status.ts";

const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pages-"));
const page = (relative) => fs.readFileSync(path.join(dist, relative), "utf8");
const exists = (relative) => fs.existsSync(path.join(dist, relative));
const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));

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

test("the method page names every status and carries the footer notice", () => {
  const html = page("how-it-works/index.html");
  for (const label of Object.values(STATUS_LABELS)) {
    assert.ok(html.includes(label), `${label} is missing`);
  }
  assert.ok(html.includes("This site gives no medical advice"));
});

test("the method page's video waits to be played, is dated, and has its words beside it", () => {
  const html = page("how-it-works/index.html");
  const video = html.match(/<video[^>]*>/)?.[0] ?? "";
  assert.ok(video.includes("controls"), "the video has no controls");
  assert.ok(video.includes('preload="none"'), "the video is fetched before it is played");
  assert.ok(!video.includes("autoplay"), "the video plays on its own");
  assert.match(html, /<source src="\/video\/explainer\.mp4/, "the video is not a file of this site");
  assert.ok(exists("video/explainer.mp4") && exists("video/explainer-poster.jpg"));
  assert.ok(html.includes("as the registries showed them in November 2026"), "the video is not dated");
  assert.ok(html.includes("What the video says"), "the video's words are not on the page");
});

test("the method page says what is counted", () => {
  assert.ok(page("how-it-works/index.html").includes("counts requests and errors"));
});

test("a year page lists the claims first reported that year", () => {
  const years = new Set(fixture.claims.map((c) => c.first_reported_date?.slice(0, 4)).filter(Boolean));
  assert.ok(years.size > 0);
  for (const year of years) {
    const html = page(`year/${year}/index.html`);
    assert.match(html, new RegExp(`First reported in ${year}`));
    for (const claim of fixture.claims) {
      const listed = html.includes(`href="/${claim.slug}"`);
      assert.equal(listed, claim.first_reported_date?.startsWith(year) ?? false, `${claim.slug} in ${year}`);
    }
  }
});

test("a year with no claim has no page", () => {
  assert.ok(!exists("year/2020/index.html"));
  assert.ok(!exists("year/1999/index.html"));
});
