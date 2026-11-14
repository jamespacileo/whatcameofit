// Opt-in live diagnostic; never part of offline tests/CI. Reads article text only
// in memory, withholds citations, and compares the expected ID only after retrieval.
// Run from repo root: node --env-file=.env site/scripts/check-paper-discovery.mjs
//   --url <article> --expected <OpenAlex or DOI URL> [--max-rank 5]
import { parseArgs } from "node:util";
import { readArticle } from "../worker/article.mjs";
import { lookUp } from "../worker/lookup.mjs";
import { makeModel } from "../worker/model.mjs";
import { makeResearch } from "../worker/research.mjs";

const { values } = parseArgs({ options: {
  url: { type: "string" }, expected: { type: "string" },
  "max-rank": { type: "string", default: "5" },
} });
const maxRank = Number(values["max-rank"]);
if (!values.url || !values.expected || !Number.isInteger(maxRank) || maxRank < 1 || maxRank > 20) {
  throw new Error("Supply --url <article> --expected <OpenAlex or DOI URL> and optionally --max-rank 1..20.");
}
for (const name of ["OPENAI_API_KEY", "OPENALEX_API_KEY", "LLM_MODEL", "CONTACT_EMAIL"]) {
  if (!process.env[name]) throw new Error(`Missing ${name}`);
}

try {
  const article = await readArticle(values.url, { fetch, contact: process.env.CONTACT_EMAIL });
  if (article.refused) throw new Error(`Article refused: ${article.refused}`);
  // Remove URLs even when they are visible anchor text, and bare DOI/PMID labels.
  // Preserve ordinary research details, including people, methods and journal names.
  let text = article.text
    .replace(/https?:\/\/\S+/gi, " ")
    .replace(/\b10\.\d{4,9}\/[^\s<>]+/gi, " ")
    .replace(/\bPMID\s*:?\s*\d+/gi, " ");
  for (const id of article.page.pubmedIds ?? []) text = text.replaceAll(id, " ");
  const model = makeModel({ fetch, apiKey: process.env.OPENAI_API_KEY,
    model: process.env.LLM_MODEL, baseUrl: process.env.LLM_BASE_URL || undefined });
  let reading;
  const queries = [];
  const research = makeResearch({
    apiKey: process.env.OPENALEX_API_KEY, contact: process.env.CONTACT_EMAIL,
    fetch: async (url, init) => {
      const target = new URL(url);
      if (target.hostname === "api.openalex.org" && target.pathname.startsWith("/works/")) {
        throw new Error("Citation-free diagnostic must not resolve a known paper identifier");
      }
      if (target.hostname === "api.openalex.org" && target.pathname === "/works") {
        queries.push({ search: target.searchParams.get("search"), filter: target.searchParams.get("filter") });
      }
      return fetch(url, init);
    },
  });
  const result = await lookUp({ text,
    page: { published: article.page.published, registryNumbers: [], dois: [], pubmedIds: [] },
    model: { read: async input => (reading = await model.read(input)) }, research,
    registry: { search: async () => [], named: async () => [], fetch: async () => null },
    index: { claims: {} },
  });
  // The expected identifier is an assertion, never a search input.
  const expected = values.expected.toLowerCase().replace(/\/$/, "");
  const papers = result.research?.papers ?? [];
  const rank = papers.findIndex(paper => [paper.id, paper.url]
    .some(value => value.toLowerCase().replace(/\/$/, "") === expected)) + 1;
  console.log(JSON.stringify({
    citationFree: true, paperQueries: reading?.paper_queries ?? [],
    researchers: reading?.researchers ?? [], queries,
    paperCount: papers.length, expectedRank: rank || null,
    expectedPaper: rank ? papers[rank - 1] : null,
    availability: result.research?.availability ?? null,
    passed: rank > 0 && rank <= maxRank,
  }, null, 2));
  if (!rank || rank > maxRank) process.exitCode = 1;
} catch (error) {
  // Never print provider errors or request payloads that might quote article text.
  console.error(error?.code === "budget_exhausted" ? "Model budget exhausted." : "Discovery diagnostic failed; check source availability and configured providers.");
  process.exitCode = 1;
}
