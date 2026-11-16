// Manual live regression, outside CI: synthetic reports and registry records, no
// source requests. Uses the configured model; output is structured evidence only.
import assert from "node:assert/strict";
import { makeModel } from "../worker/model.mjs";
import { lookUp } from "../worker/lookup.mjs";

assert.ok(process.env.OPENAI_API_KEY && process.env.LLM_MODEL, "Configure the existing lookup reader first");
const usage = { requests: 0, reported_input_tokens: 0, reported_output_tokens: 0, requests_without_token_usage: 0 };
const model = makeModel({ apiKey: process.env.OPENAI_API_KEY, model: process.env.LLM_MODEL,
  baseUrl: process.env.LLM_BASE_URL || undefined,
  decisions: process.env.DECISION_BACKEND === "openai-decisions",
  decisionsModel: process.env.DECISIONS_MODEL || undefined,
  fetch: async (...args) => {
    usage.requests++;
    const response = await fetch(...args);
    const body = await response.clone().json();
    usage.reported_input_tokens += body.usage?.prompt_tokens ?? body.usage?.input_tokens ?? 0;
    usage.reported_output_tokens += body.usage?.completion_tokens ?? body.usage?.output_tokens ?? 0;
    if (!body.usage) usage.requests_without_token_usage++;
    return response;
  },
});
const cases = [
  { id: "two-independent", text: "Synthetic research roundup. One study reports EX-1 alone reduced tinnitus symptoms. Independently, another study reports EX-2 alone reduced migraine frequency. These are unrelated trials and neither treatment was combined with the other.", expected: [["EX-1"], ["EX-2"]] },
  { id: "combination-and-single", text: "Synthetic research roundup. A trial tested the combination of EX-3 plus EX-4 for tics, comparing it with EX-4 alone. Separately, EX-5 alone was tested for tinnitus. These are independent reports.", expected: [["EX-3", "EX-4"], ["EX-5"]] },
  { id: "combination-and-unspecified", text: "Synthetic research roundup. A study tested EX-6 plus EX-7 together for tinnitus, comparing the combination with EX-7 alone. Another item mentions a new drug for migraine but supplies no name, target, method, trial number or other identity.", expected: [["EX-6", "EX-7"]] },
  { id: "company-profile", text: "Synthetic company profile. Example Labs was founded in 1992 and has offices in London. Its product catalogue lists EX-8 for tinnitus and EX-9 for migraine. This profile contains no treatment research, therapeutic finding or trial report.", expected: [] },
];
let failed = false;
for (const { id, text, expected } of process.argv.includes("--matching-only") ? [] : cases) {
  const started = performance.now();
  const reading = await model.read(text);
  const claims = [reading, ...(reading.additional_claims ?? [])].filter(one => one.about_a_treatment && one.intervention);
  const pass = claims.length === expected.length && expected.every((parts, at) =>
    parts.every(part => claims[at].intervention.includes(part)) && claims[at].indication);
  failed ||= !pass;
  console.log(JSON.stringify({ id, pass, milliseconds: Math.round(performance.now() - started),
    claims: claims.map(one => ({ treatment: one.intervention, condition: one.indication })) }));
}
// A live reading and batch decision over synthetic registry records. Both matching
// and incompatible records are scored against each claim, never just their query.
const record = (id, treatment, condition) => ({ protocolSection: {
  identificationModule: { nctId: id, briefTitle: `Trial of ${treatment} for ${condition}` },
  conditionsModule: { conditions: [condition] },
  armsInterventionsModule: { interventions: [{ name: treatment }] },
} });
const records = [record("NCT00000001", "EX-1", "Tinnitus"), record("NCT00000002", "EX-2 plus EX-3", "Migraine"),
  record("NCT00000003", "EX-1", "Migraine"), record("NCT00000004", "EX-2", "Migraine")];
const index = { claims: {
  one: { names: ["EX-1"], indication: "Tinnitus", headline: "EX-1 for tinnitus", page: "/one" },
  two: { names: ["EX-2 plus EX-3"], indication: "Migraine", headline: "EX-2 plus EX-3 for migraine", page: "/two" },
  component: { names: ["EX-2"], indication: "Migraine", headline: "EX-2 for migraine", page: "/component" },
} };
const began = performance.now();
const found = await lookUp({
  text: "Synthetic research roundup. One trial tests EX-1 alone for tinnitus. Independently, a second trial tests the combination of EX-2 plus EX-3 together for migraine, not either component alone. These treatments were not combined with EX-1. Both trials are experimental.",
  model, index, registry: { fetch: async () => null, named: async () => [], search: async () => records },
});
const claims = (found.claims ?? []).map(one => ({ treatment: one.treatment, condition: one.condition,
  state: one.check_state, cards: one.tracked.map(card => card.slug),
  matches: one.candidates.filter(candidate => candidate.answer === "match" && candidate.score >= .5).map(candidate => candidate.id),
}));
const pass = claims.length === 2 && claims.every((one, at) => one.state === "complete" &&
  one.matches.length === 1 && one.matches[0] === records[at].protocolSection.identificationModule.nctId &&
  one.cards.length === 1 && one.cards[0] === ["one", "two"][at]);
failed ||= !pass;
console.log(JSON.stringify({ id: "independent-live-scores", pass, milliseconds: Math.round(performance.now() - began), claims }));
console.log(JSON.stringify({ usage }));
process.exitCode = failed ? 1 : 0;
