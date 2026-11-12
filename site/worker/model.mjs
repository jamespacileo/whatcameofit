// The two questions put to a language model: what a text reports, and whether each
// registry record is a trial of it. The provider, the model and the key come from the
// Worker's settings; no model is named here. Keep the wording in step with the
// pipeline's thenwhat.lookup.service and thenwhat.decide.

const READ_INSTRUCTIONS = `You read one news article or social media post and say which medical treatment it is about.
Report only what the text says. Do not add facts, and do not judge the claim.
The one exception is the field for names you know: there, and only there, use your own knowledge.
If the text is not about a specific treatment for a specific condition, say so and leave
the other fields empty.`;

const SCORE_INSTRUCTIONS = `You make the same bounded classification for each numbered item. Give one answer per
item, with the item's number. For each, choose exactly one of the options offered and
give your probability for every option, as numbers from 0 to 1 that sum to 1.
Judge each item on its own, only from the information given about it. Do not add
outside knowledge about the subject.`;

const ASKED = "Is this record a trial of the claim's intervention for the claim's indication?";
// Each answer and when it applies.
const CHOICES = [
  ["match", "it tests this intervention in the claim's indication, in a form of that condition, or in patients who have it."],
  ["other_indication", "it tests this intervention for a different condition, or only in healthy volunteers."],
  ["not_a_match", "it is not a trial of this intervention."],
];
const OPTIONS = CHOICES.map(([option]) => option);
const QUESTION = [ASKED, ...CHOICES.map(([option, when]) => `- ${option}: ${when}`)].join("\n");
// A general model is asked about this many records per call.
const BATCH_SIZE = 20;
// The Decisions API takes this many questions in one request.
const MAX_QUESTIONS = 400;
// Models often return probabilities that sum to 0.98 or 1.01; that much is rescaled.
const RESCALE_WITHIN = 0.1;
const SPEND_LIMIT_CODES = new Set(["project_spend_limit_exceeded", "organization_spend_limit_exceeded"]);

const text = (description) => ({ type: "string", description });
const names = (description) => ({ type: "array", items: { type: "string" }, description });
const READING = {
  type: "object",
  additionalProperties: false,
  required: [
    "about_a_treatment", "gist", "intervention", "other_names", "known_names", "search_phrases", "indication",
    "trial_name", "participants", "sponsor",
  ],
  properties: {
    about_a_treatment: { type: "boolean", description: "Whether the text reports a specific treatment for a specific condition." },
    gist: text("What was reported, in one neutral line of your own words."),
    intervention: { type: ["string", "null"], description: "The drug, device or method, by its name alone: no maker or mechanism." },
    other_names: names("Other names the text gives it: a brand name, a code such as ABC-123, or a generic name. Never a description such as 'the drug'. Empty if there is none."),
    known_names: names("From your own knowledge, not the text: other names this exact treatment goes by that the text does not give, such as a development code, a generic name or a brand name. For a combination, also the name of each part. Only names you are sure of. At most five. Empty if you know none."),
    search_phrases: names("Up to three short phrases a clinical trial registry would use for this treatment when it has no product name, most specific first, for example 'median nerve stimulation'. Empty when the names above are enough."),
    indication: { type: ["string", "null"], description: "The condition it is reported to treat, in medical words." },
    trial_name: { type: ["string", "null"], description: "The name the text gives the trial itself, such as SURMOUNT-5 or RECOVERY. Not the treatment's name. Null if the text gives none." },
    participants: { type: ["integer", "null"], description: "How many people took part in the trial the text reports, as the text says. Null if it does not say." },
    sponsor: { type: ["string", "null"], description: "The company, university or hospital the text says ran or paid for the trial, by its name alone. Null if the text names none." },
  },
};
const probability = { type: "number" };
const ANSWERS = {
  type: "object",
  additionalProperties: false,
  required: ["answers"],
  properties: {
    answers: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["item", "choice", "probabilities"],
        properties: {
          item: { type: "integer" },
          choice: { type: "string", enum: OPTIONS },
          probabilities: {
            type: "object",
            additionalProperties: false,
            required: OPTIONS,
            properties: Object.fromEntries(OPTIONS.map((option) => [option, probability])),
          },
        },
      },
    },
  },
};

/** One answer in usable form, or null when it cannot be used. */
function usable(given) {
  if (!given || !OPTIONS.includes(given.choice)) return null;
  const values = OPTIONS.map((option) => given.probabilities?.[option]);
  if (values.some((value) => typeof value !== "number" || value < 0 || value > 1)) return null;
  const total = values.reduce((sum, value) => sum + value, 0);
  if (total <= 0 || Math.abs(total - 1) > RESCALE_WITHIN) return null;
  return {
    answer: given.choice,
    probabilities: Object.fromEntries(OPTIONS.map((option, at) => [option, values[at] / total])),
  };
}

/** One answer of the Decisions API in the same form, or null for a refusal. */
function decided(given) {
  if (!given || given.type !== "choice" || !Array.isArray(given.probabilities)) return null;
  return usable({
    choice: given.choice,
    probabilities: Object.fromEntries(given.probabilities.map((one) => [one.value, one.probability])),
  });
}

/**
 * @param {{ decisions?: boolean, decisionsModel?: string }} options With `decisions`, records
 *   are scored by OpenAI's Decisions API: every record in one request and no text written
 *   out, which is several times faster. Without it, by the general model, twenty to a call.
 */
export function makeModel({ fetch, apiKey, model, baseUrl = "https://api.openai.com/v1", decisions = false, decisionsModel, timeoutMs = 30_000 }) {
  // The pipeline names a model with its provider in front ("openai:name"); the provider's
  // own API wants the name alone.
  const modelName = String(model).replace(/^openai:/, "");
  const base = baseUrl.replace(/\/$/, "");

  // Keep the deadline until the body has been read too. Never retry a paid call:
  // a timeout does not tell us whether the provider has already billed it.
  async function request(endpoint, body, label) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(`${base}/${endpoint}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const code = (await response.json().catch(() => null))?.error?.code;
        // The provider's message may quote the submitted text. Keep only a known code.
        const error = new Error(`${label} ${response.status}`);
        if (SPEND_LIMIT_CODES.has(code)) error.code = "budget_exhausted";
        throw error;
      }
      return await response.json();
    } finally {
      clearTimeout(timeout);
    }
  }

  async function decide(intro, items) {
    const body = await request("decisions", {
      model: decisionsModel || modelName,
      input: intro,
      questions: items.map((item, at) => ({
        type: "choice",
        name: `item-${at + 1}`,
        instructions: `${QUESTION}\n\n${item}`,
        choices: CHOICES.map(([value, description]) => ({ value, description })),
      })),
    }, "decisions");
    const given = new Map((body.answers ?? []).map((answer) => [answer.name, answer]));
    return items.map((_, at) => decided(given.get(`item-${at + 1}`)));
  }
  async function ask(name, schema, instructions, prompt) {
    const body = await request("chat/completions", {
      model: modelName,
      max_completion_tokens: name === "reading" ? 2048 : 4096,
      store: false,
      service_tier: "default",
      messages: [
        { role: "system", content: instructions },
        { role: "user", content: prompt },
      ],
      response_format: { type: "json_schema", json_schema: { name, strict: true, schema } },
    }, "model");
    return JSON.parse(body.choices[0].message.content);
  }

  return {
    /** What the text reports. */
    read: (articleText) => ask("reading", READING, READ_INSTRUCTIONS, articleText),

    /** For each record, in order: the answer and its probabilities, or null when unusable. */
    async score(intro, items) {
      const size = decisions ? MAX_QUESTIONS : BATCH_SIZE;
      const batches = [];
      for (let start = 0; start < items.length; start += size) batches.push(items.slice(start, start + size));
      // The calls do not depend on each other, so they are made at the same time.
      const scored = await Promise.all(
        batches.map(async (batch) => {
          if (decisions) return decide(intro, batch);
          const numbered = batch.map((item, at) => `[${at + 1}] ${item}`).join("\n\n");
          const prompt = `${intro}\n\n${QUESTION}\n\nOptions: ${OPTIONS.join(", ")}\n\nItems:\n\n${numbered}`;
          const reply = await ask("answers", ANSWERS, SCORE_INSTRUCTIONS, prompt);
          const given = new Map((reply.answers ?? []).map((answer) => [answer.item, answer]));
          return batch.map((_, at) => usable(given.get(at + 1)));
        }),
      );
      return scored.flat();
    },
  };
}
