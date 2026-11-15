// A live check that the lookup finds the paper a report is about. Each case in
// tests/fixtures/research/cases names an article and the DOI of its paper. The article
// is read, the model says what it reports, and OpenAlex and ROR are asked, all for real:
// this costs a model call and up to five searches per case, so it is run by hand
// (`make smoke-research`) and is not part of `make check`.
//
// Two things are checked per case. Blind: with the page's links to papers left out, the
// paper is among the first results the site shows. Linked: when the page links to the
// paper, it is first.
//
// With --record the model's reading and the providers' answers are written into the
// case file, where tests/research-cases.test.mjs replays them with no network. Nothing
// of the article's text is written.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { readArticle } from "../worker/article.mjs";
import { makeModel } from "../worker/model.mjs";
import { makeResearch } from "../worker/research.mjs";

const site = path.resolve(import.meta.dirname, "..");
const casesDir = path.join(site, "tests/fixtures/research/cases");
const record = process.argv.includes("--record");

const varsFile = process.env.DEV_VARS || path.join(site, ".dev.vars");
if (!fs.existsSync(varsFile)) {
  console.error(`No ${varsFile}. Run \`node site/scripts/dev-vars.mjs\` first, or set DEV_VARS.`);
  process.exit(1);
}
const env = {};
for (const line of fs.readFileSync(varsFile, "utf8").split(/\r?\n/)) {
  const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
  if (match && match[2]) env[match[1]] = match[2].replace(/^(["'])(.*)\1$/, "$2");
}
const missing = ["OPENAI_API_KEY", "LLM_MODEL", "CONTACT_EMAIL", "OPENALEX_API_KEY"].filter((name) => !env[name]);
if (missing.length) {
  console.error(`Missing from ${varsFile}: ${missing.join(", ")}.`);
  process.exit(1);
}

/** What a provider answered, cut down to what the worker reads. */
function kept(url, body) {
  if (url.hostname === "api.ror.org") return { items: (body.items ?? []).filter((item) => item?.chosen === true) };
  const work = ({ id, title, doi, publication_year, type, primary_location }) =>
    ({ id, title, doi, publication_year, type, primary_location: { source: { display_name: primary_location?.source?.display_name ?? null } } });
  return Array.isArray(body.results) ? { results: body.results.map(work) } : work(body);
}

const rankOf = (papers, doi) => papers.findIndex((paper) => paper.url.toLowerCase() === `https://doi.org/${doi}`.toLowerCase());

let failed = 0;
for (const name of fs.readdirSync(casesDir).filter((file) => file.endsWith(".json")).sort()) {
  const file = path.join(casesDir, name);
  const one = JSON.parse(fs.readFileSync(file, "utf8"));
  const within = one.within ?? 5;
  try {
    const article = await readArticle(one.article, { fetch, contact: env.CONTACT_EMAIL });
    assert(!article.refused, `the article could not be read: ${article.refused}`);
    const model = makeModel({ fetch, apiKey: env.OPENAI_API_KEY, model: env.LLM_MODEL, baseUrl: env.LLM_BASE_URL || undefined });
    const read = await model.read(article.text);
    assert(read.about_a_treatment && read.intervention, "the model did not read the article as a report of a treatment");
    // What worker/lookup.mjs hands to the research search.
    const reading = {
      intervention: read.intervention,
      indication: read.indication,
      searchPhrases: read.search_phrases ?? [],
      organisations: [...(read.organisations ?? []), read.sponsor].filter(Boolean),
      published: article.page.published ?? null,
    };
    const linked = [
      ...(article.page.dois ?? []).map((doi) => ({ doi })),
      ...(article.page.pubmedIds ?? []).map((pubmedId) => ({ pubmedId })),
    ].slice(0, 3);

    const responses = {};
    const recording = async (url, init) => {
      const response = await fetch(url, init);
      const at = new URL(url);
      if (response.ok && at.pathname !== "/rate-limit") responses[at.href] = kept(at, await response.clone().json());
      return response;
    };
    const research = makeResearch({ fetch: recording, apiKey: env.OPENALEX_API_KEY, contact: env.CONTACT_EMAIL });

    const blind = await research.search(reading);
    assert.equal(blind.availability.openalex, "ok", `OpenAlex answered "${blind.availability.openalex}"`);
    const blindRank = rankOf(blind.papers, one.expected_doi);
    assert(blindRank >= 0 && blindRank < within,
      `blind: ${one.expected_doi} is ${blindRank < 0 ? "not among the results" : `result ${blindRank + 1}`}; wanted within the first ${within}`);

    let linkedRank = null;
    if (linked.length) {
      const withLinks = await research.search({ ...reading, linked });
      assert.equal(withLinks.availability.openalex, "ok", `OpenAlex answered "${withLinks.availability.openalex}"`);
      linkedRank = rankOf(withLinks.papers, one.expected_doi);
      assert.equal(linkedRank, 0, `linked: ${one.expected_doi} is not the first result`);
    }
    console.log(`OK ${name}: blind result ${blindRank + 1}${linkedRank === null ? ", the page links to no paper" : ", first when linked"}`);

    if (record) {
      one.recorded = { fetched_at: new Date().toISOString(), reading, linked, responses };
      fs.writeFileSync(file, `${JSON.stringify(one, null, 2)}\n`);
      console.log(`   recorded ${Object.keys(responses).length} answers into ${path.relative(site, file)}`);
    }
  } catch (error) {
    failed += 1;
    console.error(`FAILED ${name}: ${error.message}`);
  }
}
process.exit(failed ? 1 : 0);
