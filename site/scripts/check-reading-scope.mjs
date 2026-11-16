// Optional live acceptance check; never run in CI. Uses four synthetic reports,
// the configured model and one reading request per case. No source pages or storage.
// Run with the normal private model environment, e.g. uv run --env-file .env node ...
import assert from "node:assert/strict";
import { makeModel } from "../worker/model.mjs";

assert.ok(process.env.OPENAI_API_KEY && process.env.LLM_MODEL, "Configure the private model environment first.");
let requests = 0;
const model = makeModel({
  fetch: (...args) => {
    assert.ok(++requests <= 4, "Reading check exceeded its request bound.");
    return fetch(...args);
  },
  apiKey: process.env.OPENAI_API_KEY,
  model: process.env.LLM_MODEL,
  baseUrl: process.env.LLM_BASE_URL || undefined,
});
const cases = [
  {
    name: "genuine-combination",
    text: "Synthetic report: The main experiment adds RX-17 to RX-28 to treat metastatic lung cancer. Both are experimental anticancer medicines. The trial compares RX-17 plus RX-28 with RX-17 alone.",
    check: r => r.about_a_treatment && /RX-17/.test(r.intervention) && /RX-28/.test(r.intervention),
  },
  {
    name: "explicit-activation",
    text: "Synthetic report: GX-17 gene therapy is being tested for open-angle glaucoma. Participants receive it by intravitreal injection and take AX-28 solely to activate expression of the delivered genes. AX-28 is not being investigated as a glaucoma treatment. The report describes the first three adults' safety results.",
    check: r => r.about_a_treatment && r.intervention === "GX-17" && /AX-28/.test(r.gist) && /activat/.test(r.gist),
  },
  {
    name: "biomarker-population",
    text: "Synthetic report: In 42 adults with confirmed idiopathic pulmonary fibrosis, TX-17 reduced proteomic aging-clock estimates after twelve weeks. These were surrogate measurements. The investigators did not test healthy adults or establish longer lifespan.",
    check: r => r.about_a_treatment && /fibrosis|IPF/i.test(r.indication) && /aging|ageing|age|clock/i.test(r.indication),
  },
  {
    name: "separate-claims",
    text: "Synthetic roundup: Three equally prominent independent studies are covered. RX-17 is being tested for lung cancer. TX-28 is being tested for hair growth. GX-39 is being tested for glaucoma. None is the main subject, and these are not a combined regimen.",
    check: r => !r.about_a_treatment && !r.intervention,
  },
];
for (const test of cases) {
  const reading = await model.read(test.text);
  const passed = test.check(reading);
  console.log(JSON.stringify({ case: test.name, passed, intervention: reading.intervention, indication: reading.indication }));
  assert.ok(passed, `${test.name} failed; inspect before making more model calls.`);
}
console.log(JSON.stringify({ passed: cases.length, requests }));
