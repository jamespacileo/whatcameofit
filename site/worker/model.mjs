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

const OPTIONS = ["match", "other_indication", "not_a_match"];
const QUESTION = `Is this record a trial of the claim's intervention for the claim's indication?
- match: it tests this intervention in the claim's indication, in a form of that condition, or in patients who have it.
- other_indication: it tests this intervention for a different condition, or only in healthy volunteers.
- not_a_match: it is not a trial of this intervention.`;
const BATCH_SIZE = 20;
// Models often return probabilities that sum to 0.98 or 1.01; that much is rescaled.
const RESCALE_WITHIN = 0.1;

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

export function makeModel({ fetch, apiKey, model, baseUrl = "https://api.openai.com/v1" }) {
  // The pipeline names a model with its provider in front ("openai:name"); the provider's
  // own API wants the name alone.
  const modelName = String(model).replace(/^openai:/, "");
  async function ask(name, schema, instructions, prompt) {
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}/chat/completions`, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: modelName,
        messages: [
          { role: "system", content: instructions },
          { role: "user", content: prompt },
        ],
        response_format: { type: "json_schema", json_schema: { name, strict: true, schema } },
      }),
    });
    // The reply may quote what was sent, so nothing of it goes into the error.
    if (!response.ok) throw new Error(`model ${response.status}`);
    const body = await response.json();
    return JSON.parse(body.choices[0].message.content);
  }

  return {
    /** What the text reports. */
    read: (articleText) => ask("reading", READING, READ_INSTRUCTIONS, articleText),

    /** For each record, in order: the answer and its probabilities, or null when unusable. */
    async score(intro, items) {
      const scored = [];
      for (let start = 0; start < items.length; start += BATCH_SIZE) {
        const batch = items.slice(start, start + BATCH_SIZE);
        const numbered = batch.map((item, at) => `[${at + 1}] ${item}`).join("\n\n");
        const prompt = `${intro}\n\n${QUESTION}\n\nOptions: ${OPTIONS.join(", ")}\n\nItems:\n\n${numbered}`;
        const reply = await ask("answers", ANSWERS, SCORE_INSTRUCTIONS, prompt);
        const given = new Map((reply.answers ?? []).map((answer) => [answer.item, answer]));
        batch.forEach((_, at) => scored.push(usable(given.get(at + 1))));
      }
      return scored;
    },
  };
}
