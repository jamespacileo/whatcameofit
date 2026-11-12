// The public lookup service, tested through its five modules with fakes for the model,
// the registry, the network and Cloudflare's bindings. No network and no account.
// Scenario names are from openspec live-lookup. All text is synthetic.
import assert from "node:assert/strict";
import { test } from "node:test";

import { readArticle } from "../worker/article.mjs";
import { agreeing } from "../worker/details.mjs";
import worker, { handle } from "../worker/index.mjs";
import { lookUp } from "../worker/lookup.mjs";
import { makeModel } from "../worker/model.mjs";
import { pageAsText, readPage } from "../worker/page.mjs";
import { makePapers } from "../worker/papers.mjs";
import { makeRegistry } from "../worker/registry.mjs";

const TEXT = "Scientists say EX-1, also called Toothgrow, regrew teeth in people born without them.";
const READING = {
  about_a_treatment: true,
  gist: "An antibody was reported to regrow missing teeth.",
  intervention: "EX-1",
  other_names: ["Toothgrow", "the drug"],
  known_names: [],
  search_phrases: [],
  indication: "tooth agenesis",
};

function study(id, title, condition = "Tooth Agenesis", { acronym, enrolled, sponsor, collaborators = [] } = {}) {
  return {
    protocolSection: {
      identificationModule: { nctId: id, briefTitle: title, acronym },
      conditionsModule: { conditions: [condition] },
      armsInterventionsModule: { interventions: [{ name: "EX-1" }] },
      designModule: { phases: ["PHASE2"], enrollmentInfo: { count: enrolled } },
      statusModule: { overallStatus: "RECRUITING" },
      sponsorCollaboratorsModule: { leadSponsor: { name: sponsor }, collaborators: collaborators.map((name) => ({ name })) },
    },
  };
}

function fakeRegistry(byName, byId = {}, byTrialName = {}) {
  const searched = [];
  return {
    searched,
    search: async (name, condition) => (searched.push([name, condition]), byName[name] ?? []),
    fetch: async (id) => byId[id] ?? null,
    named: async (name) => byTrialName[name] ?? [],
  };
}

// Scores by reading the record: a match only when it names tooth agenesis.
function fakeModel(reading = READING) {
  const shown = [];
  return {
    shown,
    read: async (text) => (shown.push(text), reading),
    score: async (_intro, items) =>
      items.map((item) => {
        const match = item.includes("Tooth Agenesis");
        const answer = match ? "match" : "other_indication";
        return { answer, probabilities: { match: match ? 0.96 : 0.02 } };
      }),
  };
}

const INDEX = {
  claims: {
    "tooth-regrowth-ex1": { headline: "Antibody regrows teeth", page: "/tooth-regrowth-ex1", names: ["Anti-USAG-1 antibody", "toothgrow"] },
  },
};

// --- lookup -------------------------------------------------------------------------

test("Scenario: Article about a treatment with registered trials", async () => {
  const registry = fakeRegistry({
    "EX-1": [study("NCT00000002", "EX-1 in lung cancer", "Lung Cancer"), study("NCT00000001", "EX-1 in tooth agenesis")],
  });

  const found = await lookUp({ text: TEXT, model: fakeModel(), registry, index: INDEX });

  assert.deepEqual([found.treatment, found.condition], ["EX-1", "tooth agenesis"]);
  assert.deepEqual(found.candidates.map((c) => [c.id, c.answer]), [
    ["NCT00000001", "match"],
    ["NCT00000002", "other_indication"],
  ]);
  const [first] = found.candidates;
  assert.equal(first.url, "https://clinicaltrials.gov/study/NCT00000001");
  assert.deepEqual(
    [first.title, first.conditions, first.phases, first.state],
    ["EX-1 in tooth agenesis", ["Tooth Agenesis"], ["PHASE2"], "RECRUITING"],
  );
  assert.ok(first.score > 0.9 && found.candidates[1].score < 0.5);
});

test("every name, part, known name and phrase is searched within the condition", async () => {
  const reading = {
    ...READING,
    intervention: "EX-1 and EX-2",
    other_names: ["Toothgrow", "the drug", "NCT01234567"],
    known_names: ["TRG-035"],
    search_phrases: ["USAG-1 antibody"],
  };
  const registry = fakeRegistry({});

  const found = await lookUp({ text: TEXT, model: fakeModel(reading), registry, index: INDEX });

  assert.deepEqual(registry.searched.map(([name]) => name), ["EX-1 and EX-2", "Toothgrow", "EX-1", "EX-2", "TRG-035", "USAG-1 antibody"]);
  assert.ok(registry.searched.every(([, condition]) => condition === "tooth agenesis"));
  assert.deepEqual([found.names, found.known_names], [["EX-1 and EX-2", "Toothgrow"], ["TRG-035"]]);
});

test("Scenario: Text that states a registry number", async () => {
  const registry = fakeRegistry({}, { NCT01234567: study("NCT01234567", "EX-1 first study in people") });

  const found = await lookUp({ text: `${TEXT} Registered as nct01234567.`, model: fakeModel(), registry, index: INDEX });

  assert.deepEqual(found.candidates.map((c) => c.id), ["NCT01234567"]);
});

test("Scenario: Page that links to the paper it reports", async () => {
  const registry = fakeRegistry({}, { NCT07654321: study("NCT07654321", "EX-1 in tooth agenesis, second study") });
  const asked = [];
  const papers = {
    trialNumbers: async (paper) => {
      asked.push(paper);
      if (paper.pubmedId) throw new Error("papers 503");
      return paper.doi === "10.1234/example.2026.0042" ? ["NCT07654321"] : [];
    },
  };
  const page = { registryNumbers: [], dois: ["10.1234/example.2026.0042"], pubmedIds: ["31234567"] };

  const found = await lookUp({ text: TEXT, model: fakeModel(), registry, index: INDEX, page, papers });

  // A paper that cannot be looked up is passed over.
  assert.deepEqual(asked, [{ doi: "10.1234/example.2026.0042" }, { pubmedId: "31234567" }]);
  assert.deepEqual(found.paper_numbers, ["NCT07654321"]);
  assert.deepEqual(found.candidates.map((c) => [c.id, c.agrees]), [["NCT07654321", ["paper"]]]);
});

test("a registry number in a link on the page is first, whatever its score", async () => {
  const registry = fakeRegistry(
    { "EX-1": [study("NCT00000001", "EX-1 in tooth agenesis")] },
    { NCT01234567: study("NCT01234567", "EX-1 first study in people", "Healthy Volunteers") },
  );
  const page = { registryNumbers: ["NCT01234567"], dois: [], pubmedIds: [] };

  const found = await lookUp({ text: TEXT, model: fakeModel(), registry, index: INDEX, page });

  assert.deepEqual(found.candidates.map((c) => [c.id, c.agrees]), [["NCT01234567", ["stated"]], ["NCT00000001", []]]);
  assert.ok(found.candidates[0].score < 0.5);
});

test("Scenario: Text that names the trial", async () => {
  const named = study("NCT00000009", "EX-1 in adults with tooth agenesis", "Tooth Agenesis", { acronym: "REGROW-2" });
  const registry = fakeRegistry({ "EX-1": [study("NCT00000001", "EX-1 in tooth agenesis")] }, {}, { "REGROW-2": [named] });

  const found = await lookUp({ text: TEXT, model: fakeModel({ ...READING, trial_name: "REGROW-2" }), registry, index: INDEX });

  assert.equal(found.details.trial_name, "REGROW-2");
  assert.deepEqual(found.candidates.map((c) => [c.id, c.agrees]), [["NCT00000009", ["trial_name"]], ["NCT00000001", []]]);
});

test("Scenario: Text that gives the trial's size and who ran it", async () => {
  const registry = fakeRegistry({
    "EX-1": [
      study("NCT00000001", "EX-1 in tooth agenesis", "Tooth Agenesis", { enrolled: 40, sponsor: "Example Bio" }),
      study("NCT00000002", "EX-1 in tooth agenesis", "Tooth Agenesis", { enrolled: 118, sponsor: "Kyoto University" }),
      // Agreeing details never lift a record that is not a trial for the condition.
      study("NCT00000003", "EX-1 in lung cancer", "Lung Cancer", { enrolled: 120, sponsor: "Kyoto University" }),
    ],
  });
  const reading = { ...READING, participants: 120, sponsor: "Kyoto University" };

  const found = await lookUp({ text: TEXT, model: fakeModel(reading), registry, index: INDEX });

  assert.deepEqual(found.candidates.map((c) => [c.id, c.agrees]), [
    ["NCT00000002", ["participants", "sponsor"]],
    ["NCT00000001", []],
    ["NCT00000003", ["participants", "sponsor"]],
  ]);
});

test("a record agrees with a trial's name, size and sponsor by rule", () => {
  const record = (more) => study("NCT00000001", "EX-1 in adults (REGROW-2)", "Tooth Agenesis", more);

  assert.deepEqual(agreeing(record({ acronym: "REGROW-2" }), { trial_name: "regrow 2" }), ["trial_name"]);
  assert.deepEqual(agreeing(record({ acronym: "REGROW-21" }), { trial_name: "REGROW-21" }), ["trial_name"]);
  assert.deepEqual(agreeing(study("NCT00000001", "EX-1", "x", { acronym: "REGROW-21" }), { trial_name: "REGROW-2" }), []);
  assert.deepEqual(agreeing(record({ enrolled: 2539 }), { participants: 2500 }), ["participants"]);
  assert.deepEqual(agreeing(record({ enrolled: 751 }), { participants: 2500 }), []);
  assert.deepEqual(agreeing(record({ sponsor: "University of Oxford" }), { sponsor: "Oxford University" }), ["sponsor"]);
  assert.deepEqual(agreeing(record({ sponsor: "Example", collaborators: ["University of Oxford"] }), { sponsor: "Oxford University" }), ["sponsor"]);
  assert.deepEqual(agreeing(record({ sponsor: "Oxford Immunotec Ltd" }), { sponsor: "Oxford University" }), []);
  assert.deepEqual(agreeing(record({ enrolled: 100, sponsor: "Example" }), {}), []);
});

test("Scenario: Text that is not about a treatment", async () => {
  const registry = fakeRegistry({});
  const model = fakeModel({ about_a_treatment: false, gist: "A report on waiting times." });

  const found = await lookUp({ text: "Waiting lists grew again.", model, registry, index: INDEX });

  assert.deepEqual([found.about_a_treatment, found.candidates, registry.searched], [false, [], []]);
});

test("Scenario: Treatment already tracked", async () => {
  const found = await lookUp({ text: TEXT, model: fakeModel(), registry: fakeRegistry({}), index: INDEX });

  assert.deepEqual(found.tracked, [{ slug: "tooth-regrowth-ex1", headline: "Antibody regrows teeth", page: "/tooth-regrowth-ex1" }]);
});

test("no more than sixty records are scored", async () => {
  const many = Array.from({ length: 75 }, (_, n) => study(`NCT${String(n).padStart(8, "0")}`, "EX-1 study"));

  const found = await lookUp({ text: TEXT, model: fakeModel(), registry: fakeRegistry({ "EX-1": many }), index: INDEX });

  assert.equal(found.candidates.length, 60);
});

// --- registry -----------------------------------------------------------------------

function registryOver(pages) {
  const asked = [];
  const fetch = async (address, options) => {
    const url = new URL(address);
    asked.push({ url, agent: options.headers["User-Agent"] });
    const asked_for = url.searchParams.get("query.intr") ?? url.searchParams.get("query.titles") ?? url.pathname.split("/").pop();
    const key = `${asked_for}|${url.searchParams.get("query.cond") ?? ""}|${url.searchParams.get("pageToken") ?? ""}`;
    const body = pages[key];
    return body ? Response.json(body) : new Response("", { status: 404 });
  };
  return { registry: makeRegistry({ fetch, contact: "ops@example.org" }), asked };
}

test("a specific name returns every page of its trials and names the client", async () => {
  const { registry, asked } = registryOver({
    "EX-1||": { studies: [study("NCT00000001", "one")], totalCount: 2, nextPageToken: "p2" },
    "EX-1||p2": { studies: [study("NCT00000002", "two")], totalCount: 2 },
  });

  const found = await registry.search("EX-1", "tooth agenesis");

  assert.deepEqual(found.map((s) => s.protocolSection.identificationModule.nctId), ["NCT00000001", "NCT00000002"]);
  assert.match(asked[0].agent, /^thenwhat-lookup\/\S+ \(mailto:ops@example\.org\)$/);
});

test("a broad name is searched within the condition, then by its telling words", async () => {
  const { registry } = registryOver({
    "vitamin C||": { studies: [], totalCount: 900 },
    "vitamin C|chronic tooth agenesis|": { studies: [], totalCount: 0 },
    "vitamin C|tooth OR agenesis|": { studies: [study("NCT00000003", "three")], totalCount: 1 },
  });

  const found = await registry.search("vitamin C", "chronic tooth agenesis");

  assert.deepEqual(found.map((s) => s.protocolSection.identificationModule.nctId), ["NCT00000003"]);
});

test("Scenario: Name that identifies nothing", async () => {
  const { registry } = registryOver({
    "therapy||": { studies: [], totalCount: 90000 },
    "therapy|tooth agenesis|": { studies: [], totalCount: 400 },
  });

  assert.deepEqual(await registry.search("therapy", "tooth agenesis"), []);
});

test("a trial is fetched by its number, and an unknown number is none", async () => {
  const { registry } = registryOver({ "NCT00000001||": study("NCT00000001", "one") });

  assert.equal((await registry.fetch("NCT00000001")).protocolSection.identificationModule.briefTitle, "one");
  assert.equal(await registry.fetch("NCT99999999"), null);
});

test("trials are found by a trial's name, and a name that many trials carry identifies none", async () => {
  const { registry, asked } = registryOver({
    '"REGROW-2"||': { studies: [study("NCT00000009", "nine")], totalCount: 1 },
    '"study"||': { studies: [study("NCT00000001", "one")], totalCount: 4000 },
  });

  assert.deepEqual((await registry.named('REGROW-2"')).map((s) => s.protocolSection.identificationModule.nctId), ["NCT00000009"]);
  assert.match(asked[0].url.searchParams.get("fields"), /Acronym,EnrollmentCount,CollaboratorName/);
  assert.deepEqual(await registry.named("study"), []);
  assert.deepEqual(await registry.named("  "), []);
});

// --- papers -------------------------------------------------------------------------

function papersOver(byQuery) {
  const asked = [];
  const fetch = async (address, options) => {
    const url = new URL(address);
    asked.push({ query: url.searchParams.get("query"), agent: options.headers["User-Agent"] });
    const abstractText = byQuery[url.searchParams.get("query")];
    return Response.json({ resultList: { result: abstractText === undefined ? [] : [{ abstractText }] } });
  };
  return { papers: makePapers({ fetch, contact: "ops@example.org" }), asked };
}

test("a paper gives the registry number of its trial, by DOI or PubMed number", async () => {
  const { papers, asked } = papersOver({
    'DOI:"10.1234/example.2026.0042"': "A synthetic abstract. (ClinicalTrials.gov number, nct07654321.)",
    "EXT_ID:31234567 AND SRC:MED": "Registered as NCT07654321 and NCT07654322.",
    'DOI:"10.1/review"': "NCT00000001 NCT00000002 NCT00000003 NCT00000004",
  });

  assert.deepEqual(await papers.trialNumbers({ doi: "10.1234/example.2026.0042" }), ["NCT07654321"]);
  assert.deepEqual(await papers.trialNumbers({ pubmedId: "31234567" }), ["NCT07654321", "NCT07654322"]);
  // A paper that lists many trials is a review; an unknown paper gives none.
  assert.deepEqual(await papers.trialNumbers({ doi: "10.1/review" }), []);
  assert.deepEqual(await papers.trialNumbers({ doi: "10.1/unknown" }), []);
  assert.deepEqual(await papers.trialNumbers({ pubmedId: "abc" }), []);
  assert.equal(asked.length, 4);
  assert.match(asked[0].agent, /^thenwhat-lookup\/\S+ \(mailto:ops@example\.org\)$/);
});

// --- page ---------------------------------------------------------------------------

const BODY = "Researchers gave EX-1 to 120 people born without some teeth. ".repeat(12).trim();
const RICH_PAGE = `<html><head>
<title>Antibody regrows teeth | The Example</title>
<meta property="og:title" content="Antibody regrows teeth in first human trial">
<meta name="description" content="A drug called EX-1 restored missing teeth, a study says.">
<meta content="2026-03-04T09:30:00Z" property="article:published_time">
<script type="application/ld+json">${JSON.stringify({ "@graph": [{ "@type": "Organization", name: "The Example" }, { "@type": "NewsArticle", headline: "Antibody regrows teeth", articleBody: BODY }] })}</script>
<script>var tracking = "not for readers";</script></head><body>
<p>Subscribe to read the full story.</p>
<p>The results were <a href="https://doi.org/10.1234/example.2026.0042">published</a> and the study is
<a href='https://clinicaltrials.gov/study/NCT01234567'>registered</a>. An
<a href="https://pubmed.ncbi.nlm.nih.gov/31234567/">earlier report</a> covered mice.</p></body></html>`;

test("Scenario: Page that describes itself in its tags", () => {
  const page = readPage(RICH_PAGE);

  assert.deepEqual(
    [page.headline, page.summary, page.published],
    ["Antibody regrows teeth in first human trial", "A drug called EX-1 restored missing teeth, a study says.", "2026-03-04T09:30:00Z"],
  );
  const bare = readPage("<html><head><title>Teeth &amp; gums</title></head><body><p>Hi</p></body></html>");
  assert.deepEqual([bare.headline, bare.summary, bare.published, bare.body], ["Teeth & gums", null, null, null]);
});

test("Scenario: Page that carries the article as structured data", () => {
  const page = readPage(RICH_PAGE);
  const text = pageAsText(page);

  assert.equal(page.body, BODY);
  assert.ok(text.startsWith("Headline: Antibody regrows teeth in first human trial\n"));
  assert.match(text, /gave EX-1 to 120 people/);
  assert.doesNotMatch(text, /Subscribe to read|tracking/);
  const broken = readPage('<body><script type="application/ld+json">{not json</script><p>EX-1 regrew teeth.</p></body>');
  assert.deepEqual([broken.body, pageAsText(broken)], [null, "EX-1 regrew teeth."]);
});

test("links to a paper and to the registry are found, also in a publisher's own address", () => {
  const page = readPage(RICH_PAGE);
  assert.deepEqual([page.dois, page.pubmedIds, page.registryNumbers], [["10.1234/example.2026.0042"], ["31234567"], ["NCT01234567"]]);

  const links = [
    "https://www.nejm.org/doi/full/10.1056/NEJMoa2206038?query=featured",
    "https://www.nature.com/articles/s41591-023-02427-9",
    "https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(23)01053-X/fulltext",
  ];
  const publishers = readPage(links.map((link) => `<a href="${link}">paper</a>`).join(""));
  assert.deepEqual(publishers.dois, ["10.1056/nejmoa2206038", "10.1038/s41591-023-02427-9", "10.1016/s0140-6736(23)01053-x"]);
});

// --- model --------------------------------------------------------------------------

function modelOver(...replies) {
  const sent = [];
  const fetch = async (address, options) => {
    sent.push({ address, headers: options.headers, body: JSON.parse(options.body) });
    return Response.json({ choices: [{ message: { content: JSON.stringify(replies.shift()) } }] });
  };
  const model = makeModel({ fetch, apiKey: "test-key", model: "example-model", baseUrl: "https://llm.example.test/v1" });
  return { model, sent };
}

test("the model is shown the text and asked for a strict shape, with the configured model", async () => {
  const { model, sent } = modelOver(READING);

  const reading = await model.read(TEXT);

  assert.equal(reading.intervention, "EX-1");
  const [{ address, headers, body }] = sent;
  assert.equal(address, "https://llm.example.test/v1/chat/completions");
  assert.equal(headers.Authorization, "Bearer test-key");
  assert.equal(body.model, "example-model");
  assert.equal(body.messages.at(-1).content, TEXT);
  assert.deepEqual([body.response_format.type, body.response_format.json_schema.strict], ["json_schema", true]);
});

test("a model named with its provider, as the pipeline's settings name it, is asked for by its own name", async () => {
  const sent = [];
  const fetch = async (_address, options) => {
    sent.push(JSON.parse(options.body));
    return Response.json({ choices: [{ message: { content: JSON.stringify(READING) } }] });
  };

  await makeModel({ fetch, apiKey: "test-key", model: "openai:example-model" }).read(TEXT);

  assert.equal(sent[0].model, "example-model");
});

test("records are scored twenty to a call and probabilities that nearly sum to one are rescaled", async () => {
  const answer = (item) => ({ item, choice: "match", probabilities: { match: 0.9, other_indication: 0.06, not_a_match: 0.02 } });
  const first = { answers: Array.from({ length: 20 }, (_, n) => answer(n + 1)) };
  const second = { answers: [answer(1)] };
  const { model, sent } = modelOver(first, second);

  const scored = await model.score("Claim: …", Array.from({ length: 21 }, (_, n) => `record ${n}`));

  assert.equal(sent.length, 2);
  assert.equal(scored.length, 21);
  assert.equal(scored[0].answer, "match");
  assert.ok(Math.abs(scored[0].probabilities.match - 0.9 / 0.98) < 1e-9);
});

test("Scenario: Many items, one call", async () => {
  const sent = [];
  const fetch = async (address, options) => {
    const body = JSON.parse(options.body);
    sent.push({ address, headers: options.headers, body });
    const answers = body.questions.map((question, at) =>
      at === 1
        ? { type: "refusal", name: question.name }
        : {
            type: "choice",
            name: question.name,
            choice: "match",
            probabilities: [
              { value: "match", probability: 0.88 },
              { value: "other_indication", probability: 0.1 },
              { value: "not_a_match", probability: 0.02 },
            ],
            confidence: 0.82,
          },
    );
    // Answers need not come back in the order asked: they are matched by name.
    return Response.json({ answers: answers.reverse(), usage: { input_tokens: 9000 } });
  };
  const model = makeModel({ fetch, apiKey: "test-key", model: "openai:example-model", baseUrl: "https://llm.example.test/v1/", decisions: true });

  const scored = await model.score("Claim: …", Array.from({ length: 60 }, (_, n) => `record ${n}`));

  assert.equal(sent.length, 1);
  assert.equal(sent[0].address, "https://llm.example.test/v1/decisions");
  assert.equal(sent[0].headers.Authorization, "Bearer test-key");
  assert.deepEqual([sent[0].body.model, sent[0].body.input, sent[0].body.questions.length], ["example-model", "Claim: …", 60]);
  const [first] = sent[0].body.questions;
  assert.deepEqual([first.type, first.name], ["choice", "item-1"]);
  assert.match(first.instructions, /^Is this record a trial[\s\S]*\n\nrecord 0$/);
  assert.deepEqual(first.choices.map((choice) => choice.value), ["match", "other_indication", "not_a_match"]);
  assert.match(first.choices[1].description, /different condition/);
  assert.equal(scored.length, 60);
  assert.deepEqual(scored[0], { answer: "match", probabilities: { match: 0.88, other_indication: 0.1, not_a_match: 0.02 } });
  // A record the API declines has no score.
  assert.equal(scored[1], null);
});

test("a decision call that fails says its status and nothing that was sent", async () => {
  const fetch = async () => new Response(JSON.stringify({ error: "echo of record 0" }), { status: 429 });
  const model = makeModel({ fetch, apiKey: "test-key", model: "example-model", decisions: true });

  await assert.rejects(model.score("Claim: …", ["record 0"]), { message: "decisions 429" });
});

test("both model endpoints stop on spend limits without retrying or exposing provider text", async () => {
  for (const decisions of [false, true]) {
    for (const code of ["project_spend_limit_exceeded", "organization_spend_limit_exceeded", "rate_limit_exceeded"]) {
      let calls = 0;
      const model = makeModel({ apiKey: "test-key", model: "example-model", decisions,
        fetch: async () => {
          calls++;
          return Response.json({ error: { code, message: "synthetic article echo" } }, { status: 429 });
        },
      });
      await assert.rejects(decisions ? model.score("Synthetic claim", ["record"]) : model.read(TEXT), (error) => {
        assert.equal(error.code, code === "rate_limit_exceeded" ? undefined : "budget_exhausted");
        assert.doesNotMatch(error.message, /article echo/);
        return true;
      });
      assert.equal(calls, 1);
    }
  }
});

test("generated answers have bounded output, standard pricing and storage disabled", async () => {
  const { model, sent } = modelOver(READING, { answers: [] });
  await model.read(TEXT);
  await model.score("Synthetic claim", ["record"]);
  assert.deepEqual(sent.map(({ body }) => body.max_completion_tokens), [2048, 4096]);
  for (const { body } of sent) {
    assert.equal(body.store, false);
    assert.equal(body.service_tier, "default");
  }
});

test("both model endpoints abort stalled requests and response bodies without retrying", async () => {
  for (const decisions of [false, true]) {
    for (const stallBody of [false, true]) {
      let calls = 0;
      const model = makeModel({ apiKey: "test-key", model: "example-model", decisions, timeoutMs: 10,
        fetch: async (_address, { signal }) => {
          calls++;
          const stalled = () => new Promise((_resolve, reject) => signal.addEventListener("abort", () => reject(signal.reason), { once: true }));
          return stallBody ? { ok: true, json: stalled } : stalled();
        },
      });
      await assert.rejects(decisions ? model.score("Synthetic claim", ["record"]) : model.read(TEXT), { name: "AbortError" });
      assert.equal(calls, 1);
    }
  }
});

test("the public endpoint explains exhausted budgets and leaves static pages available", async () => {
  const env = {
    OPENAI_API_KEY: "test-key", LLM_MODEL: "example-model", CONTACT_EMAIL: "ops@example.test",
    LOOKUP_PER_READER: { limit: async () => ({ success: true }) },
    LOOKUP_IN_ALL: { limit: async () => ({ success: true }) },
    ASSETS: { fetch: async (request) => new URL(request.url).pathname === "/lookup.json"
      ? Response.json({ claims: {} }) : new Response("Reviewed claim") },
  };
  const response = await handle(new Request("https://example.test/api/lookup", { method: "POST", body: JSON.stringify({ text: TEXT }) }), env, {
    model: { read: async () => { throw Object.assign(new Error("synthetic echo"), { code: "budget_exhausted" }); } }, registry: {},
  });
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: "budget_exhausted" });
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.equal(await (await handle(new Request("https://example.test/claim"), env)).text(), "Reviewed claim");
});

test("the model reads the text while linked papers and stated numbers are looked up", async () => {
  const started = [];
  let reading;
  const model = {
    read: () => (started.push("read"), new Promise((resolve) => (reading = resolve))),
    score: fakeModel().score,
  };
  const registry = {
    ...fakeRegistry({}, { NCT01234567: study("NCT01234567", "EX-1 in tooth agenesis") }),
    fetch: async (id) => (started.push(`registry ${id}`), study(id, "EX-1 in tooth agenesis")),
  };
  const papers = { trialNumbers: async () => (started.push("papers"), []) };
  const page = { registryNumbers: ["NCT01234567"], dois: ["10.1234/example.2026.0042"], pubmedIds: [] };

  const looking = lookUp({ text: TEXT, model, registry, index: INDEX, page, papers });
  await new Promise((resolve) => setTimeout(resolve, 5));

  // The model has not answered yet, and the other two hosts have already been asked.
  assert.deepEqual(started, ["read", "papers", "registry NCT01234567"]);
  reading(READING);
  assert.deepEqual((await looking).candidates.map((c) => c.id), ["NCT01234567"]);
});

test("a record the model leaves out, or answers unusably, has no score", async () => {
  const { model } = modelOver({ answers: [{ item: 2, choice: "match", probabilities: { match: 3, other_indication: 0, not_a_match: 0 } }] });

  assert.deepEqual(await model.score("Claim: …", ["one", "two"]), [null, null]);
});

// --- article ------------------------------------------------------------------------

function web(pages) {
  const asked = [];
  const fetch = async (address) => {
    asked.push(address);
    const page = pages[address];
    if (page === undefined) return new Response("", { status: 404 });
    return typeof page === "number" ? new Response("", { status: page }) : new Response(page, { status: 200 });
  };
  return { fetch, asked };
}
const ARTICLE = "https://news.example.org/health/ex1";
const PAGE = `<html><head><title>EX-1 regrows teeth</title><style>p{}</style><script>track()</script></head><body><h1>EX-1 regrows teeth</h1><p>Scientists say&nbsp;EX-1 worked.</p></body></html>`;

test("an article that robots.txt allows is returned as text that opens with its headline", async () => {
  const { fetch } = web({ "https://news.example.org/robots.txt": "User-agent: *\nDisallow: /private/", [ARTICLE]: PAGE });

  const read = await readArticle(ARTICLE, { fetch, contact: "ops@example.org" });

  assert.equal(read.text, "Headline: EX-1 regrows teeth\n\nEX-1 regrows teeth EX-1 regrows teeth Scientists say EX-1 worked.");
  assert.equal(read.page.headline, "EX-1 regrows teeth");
});

test("navigation cannot push the main article past the lookup text limit", async () => {
  const navigation = "Home Departments Patient information ".repeat(2000);
  const html = `<html><head><title>New treatment</title><script>const example = "<main>Wrong text</main>";</script></head>
    <body><nav>${navigation}</nav><main><p>${TEXT}</p></main><footer>NCT01234567</footer></body></html>`;
  const { fetch } = web({ "https://news.example.org/robots.txt": "", [ARTICLE]: html });

  const read = await readArticle(ARTICLE, { fetch, contact: "ops@example.org" });

  assert.equal(read.text, `Headline: New treatment\n\n${TEXT}`);
  assert.deepEqual(read.page.registryNumbers, ["NCT01234567"]);
});

test("Scenario: Article the site does not allow to be read", async () => {
  for (const robots of ["User-agent: *\nDisallow: /", "User-agent: thenwhat\nDisallow: /health/\n\nUser-agent: *\nAllow: /", 403]) {
    const { fetch, asked } = web({ "https://news.example.org/robots.txt": robots, [ARTICLE]: PAGE });

    assert.deepEqual(await readArticle(ARTICLE, { fetch, contact: "ops@example.org" }), { refused: "robots" });
    assert.ok(!asked.includes(ARTICLE), "the article was fetched");
  }
});

test("an article that does not load, or a local address, is not read", async () => {
  const { fetch } = web({ "https://news.example.org/robots.txt": 404, [ARTICLE]: 402 });

  assert.deepEqual(await readArticle(ARTICLE, { fetch, contact: "ops@example.org" }), { refused: "unreadable" });
  for (const local of ["http://localhost:4321/x", "http://127.0.0.1/x", "http://10.0.0.5/x", "https://192.168.1.1/x", "ftp://news.example.org/x"]) {
    assert.deepEqual(await readArticle(local, { fetch, contact: "ops@example.org" }), { refused: "address" });
  }
});

// --- handler ------------------------------------------------------------------------

function env(overrides = {}) {
  const limiter = (allowed) => ({ limit: async () => ({ success: allowed }) });
  return {
    ASSETS: { fetch: async (request) => (new URL(request.url).pathname === "/lookup.json" ? Response.json(INDEX) : new Response("a page")) },
    LOOKUP_PER_READER: limiter(true),
    LOOKUP_IN_ALL: limiter(true),
    OPENAI_API_KEY: "test-key",
    LLM_MODEL: "example-model",
    CONTACT_EMAIL: "ops@example.org",
    ...overrides,
  };
}
const post = (body) => new Request("https://tracker.example.org/api/lookup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const stubs = { model: fakeModel(), registry: fakeRegistry({ "EX-1": [study("NCT00000001", "EX-1 in tooth agenesis")] }) };

test("Scenario: Reader asks about pasted text", async () => {
  const response = await handle(post({ text: TEXT }), env(), stubs);

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  const body = await response.json();
  assert.deepEqual([body.treatment, body.candidates[0].id, body.tracked[0].slug], ["EX-1", "NCT00000001", "tooth-regrowth-ex1"]);
});

test("anything but the lookup address is served as a page of the site", async () => {
  const response = await worker.fetch(new Request("https://tracker.example.org/how-it-works"), env());

  assert.equal(await response.text(), "a page");
});

test("requests the service will not answer say why with a code", async () => {
  const cases = [
    [new Request("https://tracker.example.org/api/lookup"), env(), 405, "method"],
    [post({}), env(), 400, "nothing_given"],
    [post({ text: "x".repeat(20001) }), env(), 413, "too_long"],
    [post({ url: "https://x.com/someone/status/1" }), env(), 422, "post"],
    [post({ url: "https://bit.ly/abc" }), env(), 422, "short"],
    [post({ text: TEXT }), env({ LOOKUP_PER_READER: { limit: async () => ({ success: false }) } }), 429, "busy"],
    [post({ text: TEXT }), env({ LOOKUP_IN_ALL: { limit: async () => ({ success: false }) } }), 429, "busy"],
    [post({ text: TEXT }), env({ OPENAI_API_KEY: undefined }), 503, "not_set_up"],
  ];
  for (const [request, bindings, status, code] of cases) {
    const response = await worker.fetch(request, bindings);
    assert.deepEqual([response.status, (await response.json()).error], [status, code], code);
  }
});

test("Scenario: Nothing a reader sends is written down", async () => {
  const written = [];
  const original = { log: console.log, error: console.error, warn: console.warn };
  console.log = console.error = console.warn = (...parts) => written.push(parts.join(" "));
  try {
    await handle(post({ text: TEXT }), env(), stubs);
    const broken = { ...stubs, model: { read: async () => { throw new Error("model down: Toothgrow"); } } };
    assert.equal((await handle(post({ text: TEXT }), env(), broken)).status, 502);
  } finally {
    Object.assign(console, original);
  }
  assert.ok(!written.join("\n").includes("Toothgrow"), "the text was logged");
});
