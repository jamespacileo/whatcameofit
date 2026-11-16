// Manual live regression, outside CI. Uses the configured reader for seven synthetic
// reports, with counted registry/research fakes: seven model calls, no source requests.
// Run with OPENAI_API_KEY, LLM_MODEL and optional LLM_BASE_URL in the environment.
import assert from "node:assert/strict";
import { lookUp } from "../worker/lookup.mjs";
import { makeModel } from "../worker/model.mjs";

assert.ok(process.env.OPENAI_API_KEY && process.env.LLM_MODEL, "Configure the existing lookup reader first");
const model = makeModel({ apiKey: process.env.OPENAI_API_KEY, model: process.env.LLM_MODEL,
  baseUrl: process.env.LLM_BASE_URL || undefined });
const cases = [
  ["disease-only", "Headline: A new pancreatic cancer drug could help people live longer. No medicine name, target, method or trial identifier is supplied.", false],
  ["headline-only", "Researchers report that a new pancreatic cancer drug may help people survive longer.", false],
  ["different-disease", "A promising new medicine might reduce the symptoms of asthma, according to researchers.", false],
  ["described", "Researchers report a wrist-worn device applying electrical stimulation to the median nerve to reduce tics in people with Tourette syndrome. They do not give a product name.", true],
  ["specific-target", "Researchers tested an unnamed antibody against the USAG-1 protein in mice with missing teeth. The experiments reported new tooth growth.", true],
  ["named", "Researchers report that EX-1 improved symptoms of example disease in a controlled trial.", true],
  ["identified-study", "Researchers report longer survival with the experimental medicine tested in NCT01234567 for pancreatic cancer. The post supplies this trial number but omits the medicine name.", true],
];
let failed = false;
for (const [id, text, expected] of cases) {
  const reading = await model.read(text);
  const calls = { search: 0, named: 0, fetch: 0, score: 0, research: 0 };
  const found = await lookUp({ text, index: { claims: {} },
    model: { read: async () => reading, score: async () => { calls.score++; return []; } },
    registry: {
      search: async () => { calls.search++; return []; },
      named: async () => { calls.named++; return []; },
      fetch: async () => { calls.fetch++; return null; },
    },
    research: { search: async () => { calls.research++; return { papers: [], organisations: [] }; } },
  });
  const pass = found.about_a_treatment === expected && (expected || Object.values(calls).every(n => n === 0));
  failed ||= !pass;
  console.log(JSON.stringify({ id, expected, about_a_treatment: found.about_a_treatment, calls, pass }));
}
process.exitCode = failed ? 1 : 0;
