// The claims kept at their own addresses (scripts/kept-claims.mjs): what freezing copies out of
// an old build, and when a folder of them may be published from.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { KEPT_CLAIMS_COMMIT, KEPT_FORMAT, claimFiles, freeze, keptProblems, keptSlugs, placeKept } from "../scripts/kept-claims.mjs";

const retired = JSON.parse(fs.readFileSync("data/retired-addresses.json", "utf8"));

/** An old build in miniature: one claim's eight files, the style, font, scripts and icon it loads, and
 * a page of the site it links to. */
function oldBuild() {
  const from = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-old-build-"));
  const write = (file, body) => {
    fs.mkdirSync(path.dirname(path.join(from, file)), { recursive: true });
    fs.writeFileSync(path.join(from, file), body);
  };
  const [page, embed, ...rest] = claimFiles("a-claim");
  write(page, '<link rel="stylesheet" href="/_astro/global.css"><script type="module" src="/_astro/page.js"></script><a href="/topic/teeth">t</a><a href="/embed/a-claim">e</a><img src="/og/a-claim.png"><img src="/outlet-icons/news.example.abc.png">');
  write(embed, '<link rel="stylesheet" href="/_astro/global.css">');
  for (const file of rest) write(file, "kept");
  write("_astro/global.css", "@font-face{src:url(/_astro/font.woff2)}");
  write("_astro/font.woff2", "font");
  write("_astro/page.js", 'import{a}from"./chunk.js";');
  write("_astro/chunk.js", "export const a=1;");
  write("_astro/unused.js", "not loaded by the claim");
  write("outlet-icons/news.example.abc.png", "source icon");
  write("outlet-icons/unused.example.def.png", "not loaded by the claim");
  write("topic/teeth/index.html", "a page of the site");
  return from;
}

test("freezing copies a claim's eight files and what they load, and names the pages they link to", () => {
  const from = oldBuild();
  const to = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-kept-")), "kept");
  const frozen = freeze({ from, to, slugs: ["a-claim", "never-built"], commit: KEPT_CLAIMS_COMMIT });
  assert.deepEqual(frozen, { claims: 1, files: 13, missing: ["never-built"] });
  const manifest = JSON.parse(fs.readFileSync(path.join(to, "manifest.json"), "utf8"));
  assert.deepEqual(manifest.claims["a-claim"], claimFiles("a-claim"));
  assert.deepEqual(manifest.shared, ["_astro/chunk.js", "_astro/font.woff2", "_astro/global.css", "_astro/page.js", "outlet-icons/news.example.abc.png"]);
  assert.deepEqual(manifest.linked, ["/topic/teeth"]);
  for (const file of Object.keys(manifest.sha256)) assert.deepEqual(fs.readFileSync(path.join(to, "files", file)), fs.readFileSync(path.join(from, file)), file);
});

test("the claims kept are every claim the site served but those archived or merged", () => {
  const slugs = keptSlugs(retired);
  for (const { slug } of [...retired.archived, ...retired.moved]) assert.ok(!slugs.includes(slug), slug);
  assert.ok(slugs.includes("10-person-living-donor-kidney-exchange-chain-kidney-failure"));
});

test("a kept claim's year link still opens its original index", () => {
  const from = oldBuild();
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-kept-years-"));
  const kept = path.join(work, "kept");
  const dist = path.join(work, "dist");
  fs.appendFileSync(path.join(from, "a-claim/index.html"), '<a href="/year/2022">2022</a>');
  fs.mkdirSync(path.join(from, "year/2022"), { recursive: true });
  const year = '<link rel="stylesheet" href="/_astro/year.css"><a href="/a-claim">Claim</a>';
  fs.writeFileSync(path.join(from, "year/2022/index.html"), year);
  fs.writeFileSync(path.join(from, "_astro/year.css"), "body { color: black }");

  freeze({ from, to: kept, slugs: ["a-claim"], commit: KEPT_CLAIMS_COMMIT });
  placeKept({ folder: kept, dist, slugs: ["a-claim"] });

  assert.equal(fs.readFileSync(path.join(dist, "year/2022/index.html"), "utf8"), year);
  assert.ok(fs.existsSync(path.join(dist, "_astro/year.css")));
});

test("staging and production are published only from every kept claim, frozen from the pinned commit", () => {
  assert.match(keptProblems(null).join(), /names no folder of kept claims: run make kept-claims/);
  assert.match(keptProblems(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-kept-"))).join(), /holds no kept claims/);
  // The tests' two claims are never production's.
  assert.match(keptProblems("tests/kept-claims").join(), /holds the tests' kept claims, not production's/);
  const complete = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-kept-"));
  const claims = Object.fromEntries(keptSlugs(retired).map((slug) => [slug, claimFiles(slug)]));
  const write = (manifest) => fs.writeFileSync(path.join(complete, "manifest.json"), JSON.stringify(manifest));
  write({ format: KEPT_FORMAT, commit: KEPT_CLAIMS_COMMIT, claims, shared: [], needs: {}, sha256: {} });
  assert.deepEqual(keptProblems(complete), []);
  // A folder frozen before each claim named what it needs is refused, never read as this shape.
  write({ commit: KEPT_CLAIMS_COMMIT, claims, shared: [], sha256: {} });
  assert.match(keptProblems(complete).join(), /frozen in format 1, not 2: freeze it again into a new folder/);
  const [first, ...others] = Object.keys(claims);
  write({ format: KEPT_FORMAT, commit: KEPT_CLAIMS_COMMIT, claims: Object.fromEntries(others.map((slug) => [slug, claims[slug]])), shared: [], needs: {}, sha256: {} });
  assert.match(keptProblems(complete).join(), new RegExp(`lacks the pages of 1 claim, such as ${first}`));
  write({ format: KEPT_FORMAT, commit: "f".repeat(40), claims, shared: [], needs: {}, sha256: {} });
  assert.match(keptProblems(complete).join(), /was frozen from f{40}/);
});

test("a build places only the year indexes, icons and assets its kept claims reach", () => {
  // Two claims, each linking its first report to a year index of its own; the build keeps one.
  const from = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-old-build-"));
  const write = (file, body) => {
    fs.mkdirSync(path.dirname(path.join(from, file)), { recursive: true });
    fs.writeFileSync(path.join(from, file), body);
  };
  for (const [slug, year, icon] of [["kept-claim", "2022", "kept.example.png"], ["led-claim", "2023", "led.example.png"]]) {
    const [page, ...rest] = claimFiles(slug);
    write(page, `<a href="/year/${year}/">${year}</a><img src="/outlet-icons/${icon}">`);
    for (const file of rest) write(file, "kept");
    write(`year/${year}/index.html`, `<link rel="stylesheet" href="/_astro/year-${year}.css">`);
    write(`_astro/year-${year}.css`, "body{}");
    write(`outlet-icons/${icon}`, "icon");
  }
  const kept = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-kept-")), "kept");
  freeze({ from, to: kept, slugs: ["kept-claim", "led-claim"], commit: KEPT_CLAIMS_COMMIT });
  const manifest = JSON.parse(fs.readFileSync(path.join(kept, "manifest.json"), "utf8"));
  assert.equal(manifest.format, KEPT_FORMAT);
  assert.deepEqual(manifest.needs["kept-claim"], ["_astro/year-2022.css", "outlet-icons/kept.example.png", "year/2022/index.html"]);
  const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-dist-"));
  placeKept({ folder: kept, dist, slugs: ["kept-claim"] });
  assert.ok(fs.existsSync(path.join(dist, "year/2022/index.html")));
  assert.ok(fs.existsSync(path.join(dist, "_astro/year-2022.css")));
  assert.ok(fs.existsSync(path.join(dist, "outlet-icons/kept.example.png")));
  // The other claim leads to a pair now: its year index, its style and its icon stay unpublished.
  for (const file of ["year/2023/index.html", "_astro/year-2023.css", "outlet-icons/led.example.png", "led-claim/index.html"]) {
    assert.ok(!fs.existsSync(path.join(dist, file)), file);
  }
});
