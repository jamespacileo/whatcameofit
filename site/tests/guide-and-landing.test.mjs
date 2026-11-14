// The guide, the about page, the audience pages and the sharpened topic page (openspec
// landing-pages-and-guide). The checks on entry files are pure functions, tried with
// one passing and one refused case each; the pages are checked in one build of
// tests/fixture-export.json.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";
import { yearStrip } from "../src/lib/about.ts";
import { AUDIENCES, CLAIM_FIELDS, pickClaims } from "../src/lib/audiences.ts";
import {
  APPLIES,
  METHOD_SECTIONS,
  assertNoAdvice,
  claimsAtWork,
  guideProblems,
  readEntry,
  shelfEntries,
  statusSlug,
} from "../src/lib/guide.ts";
import { DATA_LICENCE, openData } from "../src/lib/open-data.ts";
import { topicSentence } from "../src/lib/share.ts";
import { STAGE_PATH, STATUS_LABELS, STATUS_MEANINGS, topicSummary } from "../src/lib/status.ts";

const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
const codes = Object.keys(STATUS_LABELS);
const files = fs.readdirSync("src/guide").filter((file) => file.endsWith(".md"));

const TEXT = `## In the records\n\n${"A registry holds a record of the trial. ".repeat(12)}\n\n## What it does not tell you\n\n${"It does not say what the trial found. ".repeat(12)}`;

/** An entry that passes every check; a test changes one thing about it. */
const entry = (slug, front = {}, text = TEXT) =>
  readEntry(
    slug,
    {
      shelf: "site",
      title: "Record",
      answer: "A record is a dated fact held by a public source.",
      rule: "where-the-data-comes-from",
      on_site: "Every record links to its source.",
      ...front,
    },
    text,
  );
const statusEntries = () =>
  codes.map((code) => entry(statusSlug(code), { shelf: "status", status: code }));
const problemsWith = (...extra) => guideProblems([...statusEntries(), ...extra]);

test("a complete set of entries passes, and a status without an entry is named", () => {
  assert.deepEqual(problemsWith(entry("record")), []);
  const missing = guideProblems(statusEntries().filter((held) => held.status !== "retracted"));
  assert.equal(missing.length, 1);
  assert.match(missing[0], /Origin paper retracted.*has no guide entry/);
});

test("an entry on how research is recorded needs a source with the day it was checked", () => {
  const source = { name: "A registry", url: "https://example.org/a", checked: "2026-11-14" };
  assert.deepEqual(problemsWith(entry("trial-registry", { shelf: "research", sources: [source] })), []);
  assert.match(problemsWith(entry("trial-registry", { shelf: "research" })).join("\n"), /lists at least one source/);
  const undated = entry("trial-registry", { shelf: "research", sources: [{ ...source, checked: "" }] });
  assert.match(problemsWith(undated).join("\n"), /no day it was checked/);
});

test("a related entry must exist", () => {
  assert.deepEqual(problemsWith(entry("record", { related: ["approved"] })), []);
  assert.match(problemsWith(entry("record", { related: ["nowhere"] })).join("\n"), /"nowhere" does not exist/);
});

test("verdict wording and advice wording are each refused, with the entry named", () => {
  const verdict = entry("record", {}, TEXT.replace("It does not say", "The work was abandoned. It does not say"));
  assert.match(problemsWith(verdict).join("\n"), /Guide entry "record".*Verdict wording "abandoned"/);
  const advice = entry("record", {}, TEXT.replace("It does not say", "You should ask for it. It does not say"));
  assert.match(problemsWith(advice).join("\n"), /Guide entry "record".*Advice wording "You should"/);
  assert.doesNotThrow(() => assertNoAdvice(["This site gives no medical advice."]));
  assert.throws(() => assertNoAdvice(["It is worth joining a trial."]), /Advice wording/);
});

test("an entry's text keeps its two parts, its length and a rule on the method page", () => {
  assert.match(problemsWith(entry("record", {}, "## In the records\n\nShort.")).join("\n"), /What it does not tell you/);
  assert.match(problemsWith(entry("record", {}, TEXT + " word".repeat(500))).join("\n"), /runs to \d+ words/);
  assert.match(problemsWith(entry("record", { rule: "nowhere" })).join("\n"), /not a section of the method page/);
  const method = fs.readFileSync("src/pages/how-it-works.astro", "utf8");
  for (const section of Object.keys(METHOD_SECTIONS)) {
    assert.ok(method.includes(`id="${section}"`), `the method page has no section ${section}`);
  }
});

test("a status entry takes its words from the status wording, and statuses run along the path", () => {
  const held = entry("phase-3-trial", { shelf: "status", status: "phase_3", title: "Typed again" });
  assert.equal(held.title, STATUS_LABELS.phase_3);
  assert.equal(held.answer, STATUS_MEANINGS.phase_3);
  const order = shelfEntries(statusEntries().reverse(), "status").map((item) => item.status);
  assert.deepEqual(order.slice(0, STAGE_PATH.length), STAGE_PATH);
});

test("an entry lists up to three claims its word applies to, newest report first", () => {
  const claims = fixture.claims;
  const work = claimsAtWork(entry("claim", { applies: "claims" }), claims);
  assert.equal(work.total, claims.length);
  assert.ok(work.shown.length <= 3);
  const dates = work.shown.map((claim) => claim.first_reported_date ?? "");
  assert.deepEqual(dates, [...dates].sort().reverse());
  assert.equal(claimsAtWork(entry("origin-paper"), claims), null);
  for (const code of codes) assert.ok(APPLIES[code], `no set of claims for ${code}`);
});

test("the entry files: one per status, 27 in all, each research entry sourced", () => {
  assert.equal(files.length, 27);
  for (const code of codes) assert.ok(files.includes(`${statusSlug(code)}.md`), `${code} has no file`);
  const research = files.filter((file) => /^shelf: research$/m.test(fs.readFileSync(`src/guide/${file}`, "utf8")));
  assert.equal(research.length, 9);
  for (const file of research) {
    assert.match(fs.readFileSync(`src/guide/${file}`, "utf8"), /checked: "\d{4}-\d{2}-\d{2}"/, file);
  }
});

test("the journalists' search finds a claim by every word typed, and nothing for a blank", () => {
  const claims = [{ words: "aspirin dentine repair" }, { words: "usag-1 tooth regrowth" }];
  assert.deepEqual(pickClaims(claims, "Tooth  regrowth"), [claims[1]]);
  assert.deepEqual(pickClaims(claims, "tooth aspirin"), []);
  assert.deepEqual(pickClaims(claims, "  "), []);
});

test("the copied topic sentence is the summary, the checked month and the address", () => {
  assert.equal(
    topicSentence("1 reported breakthrough tracked: it has no trial in people on record.", "2026-11-13T19:17:20Z", "https://example.org/topic/x"),
    "1 reported breakthrough tracked: it has no trial in people on record. Checked November 2026. https://example.org/topic/x",
  );
});

test("the about page's years join the empty ones and mark the promised and checked years", () => {
  const claim = {
    first_reported_date: "2019-05-01",
    articles: [{ url: "https://example.org/a", published_date: "2019-05-01" }],
    events: [{ event_date: "2022-03-01" }, { event_date: "2022-09-01" }],
    promises: [{ description: "Trials by 2027", parsed_date: "2027-01-01", article_url: "https://example.org/a" }],
  };
  const strip = yearStrip(claim, "2026-11-13");
  assert.deepEqual(
    strip.map((cell) => (cell.kind === "gap" ? `${cell.from}-${cell.to}` : cell.year)),
    [2019, "2020-2021", 2022, "2023-2025", 2026, 2027],
  );
  assert.equal(strip[2].records, 2);
  assert.equal(strip[0].reports, 1);
  assert.ok(strip[4].checked && strip[5].promised);
});

test("every field of a claim in the data file has words on the researchers' page", () => {
  const file = openData(fixture, DATA_LICENCE, "credit", "https://example.org/how-it-works");
  for (const field of Object.keys(file.claims[0])) {
    assert.ok(CLAIM_FIELDS[field], `the data file's field ${field} is not described`);
  }
});

// --- the built pages ---------------------------------------------------------------

const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-guide-"));
const page = (relative) => fs.readFileSync(path.join(dist, relative), "utf8");
const exists = (relative) => fs.existsSync(path.join(dist, relative));
const SUGGEST = "mailto:suggest@example.org";

before(() => {
  const result = spawnSync("npx", ["astro", "build", "--outDir", dist], {
    env: {
      ...process.env,
      EXPORT_FILE: "tests/fixture-export.json",
      SUGGEST_URL: SUGGEST,
      CORRECTIONS_URL: "mailto:corrections@example.org",
      ASTRO_TELEMETRY_DISABLED: "1",
    },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

const text = (html) => html.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
const count = (code) => fixture.claims.filter((claim) => claim.status.code === code).length;

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
