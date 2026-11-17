import { createHash } from "node:crypto";
// The plain trial page and the trial listing, checked in a build of tests/fixture-export.json
// with tests/fixture-trials-listing.json beside it. Every record is synthetic; the registry
// is a stand-in and nothing is fetched. Scenario names are from openspec trial-pages.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";
import { parseHTML } from "linkedom";
import { NOTICES } from "../src/lib/notices.ts";
import {
  FIXED_WORDING, NO_REPORT, NO_RESULTS, STATE_PHRASES, assertPlainWording, findListed,
  forbiddenWord, registryDate, resultsPhrase, searchListing, statePhrase,
} from "../src/lib/trial-page.mjs";
import { handleTrial } from "../worker/trials.mjs";

const dist = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-trial-pages-"));
const off = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-trial-pages-off-"));
const listing = JSON.parse(fs.readFileSync("tests/fixture-trials-listing.json", "utf8"));
const now = Date.parse("2026-11-17T12:00:00Z");
const UNCITED = "NCT09000001";
const CITED = "NCT00000002";

function build(outDir, env = {}) {
  return spawnSync("npx", ["astro", "build", "--outDir", outDir], {
    env: { ...process.env, EXPORT_FILE: "tests/fixture-export.json", ASTRO_TELEMETRY_DISABLED: "1", ...env },
    encoding: "utf8",
  });
}

before(() => {
  const result = build(dist);
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

// A synthetic registry record. It holds what a real one does and the page must leave
// out: a summary, a location, a contact, who may take part and a planned outcome.
function record(id, changes = {}) {
  return {
    hasResults: false,
    protocolSection: {
      identificationModule: { nctId: id, briefTitle: "A synthetic study of zetamab in synthetic lung condition", acronym: "SYNTH-1" },
      statusModule: {
        overallStatus: "RECRUITING",
        startDateStruct: { date: "2025-02-10", type: "ACTUAL" },
        primaryCompletionDateStruct: { date: "2027-06", type: "ESTIMATED" },
        studyFirstPostDateStruct: { date: "2025-01-20" },
        lastUpdatePostDateStruct: { date: "2026-10-05" },
        ...changes.status,
      },
      descriptionModule: { briefSummary: "PLANTED-SUMMARY of a promising option." },
      conditionsModule: { conditions: ["Synthetic lung condition"] },
      armsInterventionsModule: { interventions: [{ name: "Zetamab", type: "BIOLOGICAL", description: "PLANTED-DOSE" }, { name: "Placebo", type: "DRUG" }] },
      designModule: { phases: ["PHASE3"], studyType: "INTERVENTIONAL", enrollmentInfo: { count: 420, type: "ESTIMATED" }, ...changes.design },
      sponsorCollaboratorsModule: { leadSponsor: { name: "Synthetic Sponsor Ltd", class: "INDUSTRY" }, ...changes.sponsor },
      outcomesModule: { primaryOutcomes: [{ measure: "PLANTED-OUTCOME", timeFrame: "12 months" }] },
      eligibilityModule: { eligibilityCriteria: "PLANTED-CRITERIA", healthyVolunteers: false },
      contactsLocationsModule: {
        centralContacts: [{ name: "PLANTED-CONTACT", email: "planted@example.test" }],
        locations: [{ facility: "PLANTED-SITE", city: "PLANTED-CITY", status: "RECRUITING" }],
      },
    },
    ...changes.top,
  };
}

// The built files, served as Cloudflare serves them, and a registry that answers with
// the synthetic record. The Worker's own code runs unchanged.
function site(directory, payload, bindings = {}) {
  const calls = [];
  const env = {
    CONTACT_EMAIL: "corrections@example.test",
    ASSETS: {
      fetch: async (request) => {
        const pathname = new URL(request.url).pathname;
        for (const file of [pathname, `${pathname}/index.html`, `${pathname}.html`]) {
          const full = path.join(directory, file);
          if (fs.existsSync(full) && fs.statSync(full).isFile()) return new Response(fs.readFileSync(full));
        }
        return new Response("missing", { status: 404 });
      },
    },
    TRIAL_RECORD_READS: { limit: async () => ({ success: true }) },
    ...bindings,
  };
  const fetch = async (url) => {
    calls.push(String(url));
    return payload ? Response.json(payload) : new Response("none", { status: 404 });
  };
  const open = (id, options) => handleTrial(new Request(`https://example.test/trials/${id}`, options), env, { fetch, now: () => now });
  return { calls, open };
}

// What a reader reads on a page: its text, without scripts, styles and the two footer
// notices, which must name advice and treatment options to disclaim them.
function readerText(html) {
  const { document } = parseHTML(html);
  for (const node of document.querySelectorAll("script, style, template")) node.remove();
  let text = document.body.textContent.replace(/\s+/g, " ");
  for (const notice of NOTICES) text = text.replaceAll(notice, " ");
  return text;
}

test("Scenario: An uncited trial", async () => {
  const served = site(dist, record(UNCITED));
  const response = await served.open(UNCITED);
  const html = await response.text();
  assert.equal(response.status, 200);
  assert.equal(served.calls.length, 1);
  assert.ok(served.calls[0].startsWith(`https://clinicaltrials.gov/api/v2/studies/${UNCITED}?fields=NCTId%2C`));
  for (const said of [
    "A synthetic study of zetamab in synthetic lung condition", UNCITED, "ClinicalTrials.gov",
    STATE_PHRASES.under_way, NO_REPORT, "Phase 3", "Synthetic lung condition", "Biological: Zetamab", "Drug: Placebo",
    "420 (planned)", "Synthetic Sponsor Ltd", NO_RESULTS, "10 Feb 2025", "Jun 2027</span> (estimated)", "5 Oct 2026", "17 Nov 2026",
    `href="https://clinicaltrials.gov/study/${UNCITED}"`, ...NOTICES,
  ]) assert.ok(html.includes(said), said);
  // Marked estimated, and no day invented for a month.
  assert.doesNotMatch(html, /\d+ Jun 2027/);
  // No status, no claim, and nothing about taking part.
  for (const kept of ["PLANTED", "planted@", "Claims citing", "status-name", "On record now"]) assert.ok(!html.includes(kept), kept);
});

test("Scenario: A recruiting trial", async () => {
  const html = await (await site(dist, record(UNCITED)).open(UNCITED)).text();
  assert.ok(html.includes("The registry lists this study as started and not yet finished."));
  assert.doesNotMatch(html, /recruit/i);
});

test("no verdict or advice word is on a plain trial page, in any state", async () => {
  const states = ["NOT_YET_RECRUITING", "RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING", "COMPLETED", "SUSPENDED", "TERMINATED", "WITHDRAWN", "UNKNOWN", "AVAILABLE", ""];
  for (const overallStatus of states) {
    const payload = record(UNCITED, {
      status: { overallStatus, whyStopped: overallStatus === "TERMINATED" ? "Sponsor decision" : undefined, resultsFirstPostDateStruct: overallStatus === "COMPLETED" ? { date: "2025-03-03" } : undefined },
      top: { hasResults: overallStatus === "COMPLETED" },
    });
    const response = await site(dist, payload).open(UNCITED);
    assert.equal(response.status, 200, overallStatus);
    const text = readerText(await response.text());
    assert.equal(forbiddenWord(text), null, `${overallStatus}: "${forbiddenWord(text)}" in: ${text}`);
    assert.ok(text.includes(statePhrase(overallStatus)), overallStatus);
    assert.ok(text.includes(NO_REPORT), overallStatus);
  }
});

test("the check on a page's words does find a planted one", () => {
  for (const planted of ["This study was successful.", "The trial failed.", "A promising treatment option.", "Results are overdue.", "Now recruiting: contact the site to take part.", "Available to eligible patients."]) {
    assert.notEqual(forbiddenWord(planted), null, planted);
    assert.throws(() => assertPlainWording([...FIXED_WORDING, planted]), /Verdict or advice wording/);
  }
  assert.doesNotThrow(() => assertPlainWording(FIXED_WORDING));
});

test("Scenario: A record with results posted; a terminated trial with a stated reason; a trial sponsored by a person", async () => {
  const payload = record(UNCITED, {
    status: { overallStatus: "TERMINATED", whyStopped: "Sponsor decision", resultsFirstPostDateStruct: { date: "2025-03-03" }, completionDateStruct: undefined },
    design: { phases: ["NA"], enrollmentInfo: { count: 12, type: "ACTUAL" } },
    sponsor: { leadSponsor: { name: "PLANTED-PERSON", class: "INDIVIDUAL" } },
    top: { hasResults: true },
  });
  const html = await (await site(dist, payload).open(UNCITED)).text();
  for (const said of [
    "Results were first posted on the registry record on 3 March 2025.", STATE_PHRASES.terminated,
    "The reason the registry record gives for stopping:", "<blockquote>Sponsor decision</blockquote>",
    "The registry gives no phase for this study.", "12 (actual)", "<dt>Study completion</dt><dd>Not stated</dd>",
  ]) assert.ok(html.includes(said), said);
  assert.ok(!html.includes("PLANTED-PERSON") && !html.includes("Lead sponsor"));
});

test("the day the registry last changed the record stands with the state", async () => {
  // Listed as under way, and not changed since 2019: the page says both.
  const old = record(UNCITED, { status: { overallStatus: "RECRUITING", lastUpdatePostDateStruct: { date: "2019-04-02" } } });
  const html = await (await site(dist, old).open(UNCITED)).text();
  const state = html.indexOf(STATE_PHRASES.under_way);
  const changed = html.indexOf("The registry last changed this record on 2 April 2019.");
  assert.ok(state > 0 && changed > state && changed < html.indexOf(NO_REPORT));
  const undated = record(UNCITED, { status: { lastUpdatePostDateStruct: undefined } });
  assert.ok((await (await site(dist, undated).open(UNCITED)).text()).includes("The registry does not state when it last changed this record."));
});

test("pages of uncited trials have a read allowance of their own, and a cited trial's page does not use it", async () => {
  const served = site(dist, record(UNCITED), { LISTED_TRIAL_READS: { limit: async () => ({ success: false }) } });
  const refused = await served.open(UNCITED);
  assert.equal(refused.status, 503);
  assert.equal(refused.headers.get("retry-after"), "60");
  assert.deepEqual(served.calls, [], "the registry is not asked");
  const cited = site(dist, record(CITED), { LISTED_TRIAL_READS: { limit: async () => ({ success: false }) } });
  assert.equal((await cited.open(CITED)).status, 200);
});

test("an uncited trial page is not to be indexed", async () => {
  const response = await site(dist, record(UNCITED)).open(UNCITED);
  assert.equal(response.headers.get("x-robots-tag"), "noindex, follow");
  const { document } = parseHTML(await response.text());
  assert.match(document.querySelector('meta[name="robots"]').getAttribute("content"), /noindex/);
  assert.ok(document.querySelector('link[rel="canonical"]').getAttribute("href").endsWith(`/trials/${UNCITED}`));
});

test("Scenario: The sitemap", () => {
  const sitemap = fs.readFileSync(path.join(dist, "sitemap.xml"), "utf8");
  assert.ok(sitemap.includes("/phase-claim"));
  assert.ok(!sitemap.includes("/trials/") && !sitemap.includes("NCT"), "a trial page is in the sitemap");
});

test("a trial a claim cites leads to the claim and has no no-report line", async () => {
  const payload = record(CITED);
  payload.protocolSection.descriptionModule.briefSummary = "A synthetic summary.";
  const html = await (await site(dist, payload).open(CITED)).text();
  assert.ok(html.includes("Claims citing this record") && html.includes('href="/phase-claim"'));
  assert.ok(html.indexOf('href="/phase-claim"') < html.indexOf('<dl class="trial-facts"'), "the claim comes after the facts");
  assert.ok(!html.includes(NO_REPORT));
  assert.ok(html.includes(STATE_PHRASES.under_way));
  assert.doesNotMatch(html.replace(/<footer[\s\S]*$/, ""), /recruiting/i);
});

test("a trial neither cited nor listed has no page, and the registry is not asked", async () => {
  const served = site(dist, record("NCT09999999"));
  const response = await served.open("NCT09999999");
  assert.equal(response.status, 404);
  assert.deepEqual(served.calls, []);
  assert.match(await response.text(), /not in the site’s list of trials/);
});

test("a listed trial the registry no longer has answers 404", async () => {
  assert.equal((await site(dist, null).open(UNCITED)).status, 404);
});

test("the built listing is the pipeline's file, and a claim page does not fetch it", () => {
  // The manifest says which part holds which numbers; the parts together are the file.
  const manifest = JSON.parse(fs.readFileSync(path.join(dist, "trials-listing.json"), "utf8"));
  assert.equal(manifest.total, listing.trials.length);
  assert.equal(manifest.set, listing.set);
  assert.equal(manifest.trials, undefined, "the manifest holds no trial");
  const built = manifest.parts.map((part) => JSON.parse(fs.readFileSync(path.join(dist, part.file), "utf8")));
  assert.deepEqual(built.flatMap((part) => part.trials), [...listing.trials].sort((a, b) => a[0].localeCompare(b[0])));
  for (const [at, part] of built.entries()) {
    assert.deepEqual({ ...part, trials: [] }, { ...listing, trials: [] }, "a part is a listing in itself");
    const hash = createHash("sha256").update(JSON.stringify(part)).digest("hex");
    assert.ok(manifest.parts[at].file.endsWith(`-${hash}.json`), "a changed part must have a new address");
    assert.equal(manifest.parts[at].first, part.trials[0][0]);
    assert.equal(manifest.parts[at].last, part.trials.at(-1)[0]);
    assert.equal(manifest.parts[at].trials, part.trials.length);
  }
  assert.deepEqual(fs.readFileSync(path.join(dist, "trial-listed.txt"), "utf8").trim().split("\n"), listing.trials.map((row) => row[0]));
  // Scenario: A page that needs no search
  const claim = fs.readFileSync(path.join(dist, "phase-claim/index.html"), "utf8");
  assert.ok(!claim.includes("trials-listing") && !claim.includes("trial-listed"));
});

test("with the setting off, a listed uncited trial has no page and search finds no listed trial", async () => {
  const result = build(off, { LISTED_TRIAL_PAGES: "0" });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(off, "trials-listing.json"), "utf8")).parts, []);
  const served = site(off, record(UNCITED));
  assert.equal((await served.open(UNCITED)).status, 404);
  assert.deepEqual(served.calls, []);
  assert.equal((await site(off, record(CITED)).open(CITED)).status, 200);
});

test("a listing that does not match its schema stops the build", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-trial-listing-bad-"));
  const file = path.join(directory, "listing.json");
  const bad = structuredClone(listing);
  bad.trials[0][4] = "recruiting";
  fs.writeFileSync(file, JSON.stringify(bad));
  const result = build(path.join(directory, "dist"), { TRIALS_LISTING_FILE: file });
  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /does not match trials-listing\.schema\.json/);
});

test("a listed trial is found by its registry number", () => {
  assert.equal(findListed(listing, "nct09000002").title, "Synthetic dose-finding study of EX-9");
  assert.equal(findListed(listing, "NCT09999999"), null);
});

test("listed trials are found by words of the title, acronym, intervention and condition", () => {
  const ids = (query) => searchListing(listing, query).trials.map((trial) => trial.id);
  assert.deepEqual(ids("dose-finding"), ["NCT09000002"]);
  // The acronym named exactly leads; "EX-2" also holds a word starting "synth" and a "2".
  assert.deepEqual(ids("synth-2"), ["NCT09000003", "NCT00000002"]);
  assert.deepEqual(ids("ex-9"), ["NCT09000002"]);
  // An intervention named exactly leads; then the record the registry changed last.
  assert.deepEqual(ids("zetamab"), ["NCT09000001", "NCT09000003"]);
  assert.deepEqual(ids("zetamab kidney"), ["NCT09000003"]);
  assert.deepEqual(ids("skin"), ["NCT09000002"]);
  assert.deepEqual(ids("zeta"), ["NCT09000001", "NCT09000003"]);
  assert.deepEqual(ids("nothing-here"), []);
  assert.deepEqual(ids(" "), []);
  assert.deepEqual(searchListing(listing, "synthetic", 2), { total: 4, trials: searchListing(listing, "synthetic", 2).trials });
  assert.equal(searchListing(listing, "synthetic", 2).trials.length, 2);
});

test("dates and results are worded from the record alone", () => {
  assert.equal(registryDate("2027-06"), "Jun 2027");
  assert.equal(registryDate("2027"), "2027");
  assert.equal(registryDate("2025-03-03", true), "3 March 2025");
  assert.equal(registryDate("soon"), null);
  assert.equal(resultsPhrase(true, "2025-03-03"), "Results were first posted on the registry record on 3 March 2025.");
  assert.equal(resultsPhrase(false, undefined), "The registry record holds no posted results.");
  assert.equal(resultsPhrase(true, undefined), "The registry record holds posted results.");
});

test("the method page says how a trial comes to have a page, only in a build with a listing", () => {
  const html = fs.readFileSync(path.join(dist, "how-it-works/index.html"), "utf8");
  assert.ok(html.includes('id="a-trial-with-no-report"') && html.includes(NO_REPORT));
  assert.match(html, /Most registered trials are never the subject of a news report/);
  assert.ok(!fs.readFileSync(path.join(off, "how-it-works/index.html"), "utf8").includes("a-trial-with-no-report"));
});

test("an export under a name of its own has no listing beside it, and still builds", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-trial-listing-named-"));
  const file = path.join(directory, "dated.json");
  fs.copyFileSync("tests/fixture-export.json", file);
  const out = path.join(directory, "dist");
  const result = build(out, { EXPORT_FILE: file });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(out, "trials-listing.json"), "utf8")).parts, []);
});

test("a sponsor who is a person is never named, on either kind of trial page", async () => {
  // The registry's API writes the class "INDIV"; a sponsor-investigator is a person
  // whatever the class, and the registry often classes one as "OTHER".
  const people = {
    "class INDIV": { leadSponsor: { name: "PLANTED-PERSON", class: "INDIV" } },
    "class INDIVIDUAL": { leadSponsor: { name: "PLANTED-PERSON", class: "INDIVIDUAL" } },
    "a sponsor-investigator classed OTHER": {
      leadSponsor: { name: "PLANTED-PERSON", class: "OTHER" },
      responsibleParty: { type: "SPONSOR_INVESTIGATOR", investigatorFullName: "PLANTED-PERSON", investigatorAffiliation: "PLANTED-AFFILIATION" },
    },
  };
  for (const [which, sponsor] of Object.entries(people)) {
    for (const id of [UNCITED, CITED]) {
      const response = await site(dist, record(id, { sponsor })).open(id);
      const html = await response.text();
      assert.equal(response.status, 200, which);
      assert.ok(!html.includes("PLANTED-PERSON") && !html.includes("PLANTED-AFFILIATION"), `${which}, ${id}: a person is named`);
      assert.ok(!html.includes("Lead sponsor"), `${which}, ${id}: a sponsor row is shown`);
    }
  }
  // An organisation is still named, with a principal investigator as responsible party.
  const named = { leadSponsor: { name: "Synthetic Sponsor Ltd", class: "OTHER" }, responsibleParty: { type: "PRINCIPAL_INVESTIGATOR" } };
  for (const id of [UNCITED, CITED]) {
    assert.ok((await (await site(dist, record(id, { sponsor: named })).open(id)).text()).includes("Synthetic Sponsor Ltd"), id);
  }
});

test("the listing files are served marked not to be indexed", () => {
  const headers = fs.readFileSync(path.join(dist, "_headers"), "utf8");
  for (const file of ["/trials-listing.json", "/trials-listing/*", "/trial-listed.txt"]) {
    assert.match(headers, new RegExp(`^${file.replace(/[.*]/g, "\\$&")}\\n  X-Robots-Tag: noindex$`, "m"), file);
  }
});
