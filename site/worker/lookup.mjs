// From a piece of text to ranked trial records. Pure orchestration: the model, the
// registry and the index of tracked claims are passed in. Behaviour: openspec live-lookup.
// The same steps as the pipeline's thenwhat.lookup.service; keep the two in step.
//
// The answer carries codes and registry fields only. The site words them.
import { PAPER, STATED, agreeing } from "./details.mjs";
import { isAName, nameKey, partsOf } from "./names.mjs";

const REGISTRY_NUMBER = /\bNCT\d{8}\b/gi;
// The most records one lookup will ask the model about.
const MAX_CANDIDATES = 60;
const MAX_RECORD_CHARACTERS = 1500;
// From this score a record reads as a trial of the treatment for the condition.
export const LIKELY_FROM = 0.5;
// The most linked papers one lookup asks about.
const MAX_PAPERS = 3;

const unique = (items) => [...new Set(items)];
const idOf = (study) => study.protocolSection.identificationModule.nctId;

/** A registry record as it is shown to the model: what decides a match comes first. */
export function candidateText(study) {
  const section = study.protocolSection ?? {};
  const described = {
    title: section.identificationModule?.briefTitle,
    official_title: section.identificationModule?.officialTitle,
    conditions: section.conditionsModule?.conditions ?? [],
    interventions: (section.armsInterventionsModule?.interventions ?? []).map((one) => one.name),
    phases: section.designModule?.phases ?? [],
    status: section.statusModule?.overallStatus,
    sponsor: section.sponsorCollaboratorsModule?.leadSponsor?.name,
  };
  const kept = Object.fromEntries(
    Object.entries(described).filter(([, value]) => (Array.isArray(value) ? value.length : value)),
  );
  return `Candidate record from clinicaltrials.gov (${idOf(study)}):\n${JSON.stringify(kept).slice(0, MAX_RECORD_CHARACTERS)}`;
}

function nothingFound(reading, numbers) {
  return {
    about_a_treatment: false,
    gist: reading.gist ?? "",
    treatment: null,
    condition: null,
    names: [],
    known_names: [],
    registry_numbers: numbers,
    paper_numbers: [],
    details: { trial_name: null, participants: null, sponsor: null },
    tracked: [],
    candidates: [],
    unscored: 0,
  };
}

/** One request at a time to one host, in order. */
async function inTurn(items, ask) {
  const answers = [];
  for (const item of items) answers.push(await ask(item));
  return answers;
}

/** The registry numbers given by the papers the page links to. A paper that cannot be
 * looked up is passed over: the lookup goes on without it. */
async function paperNumbers(page, papers) {
  if (!page || !papers) return [];
  const linked = [
    ...(page.dois ?? []).map((doi) => ({ doi })),
    ...(page.pubmedIds ?? []).map((pubmedId) => ({ pubmedId })),
  ].slice(0, MAX_PAPERS);
  const found = [];
  for (const paper of linked) {
    found.push(...(await papers.trialNumbers(paper).catch(() => [])));
  }
  return unique(found);
}

/**
 * @param {{ text: string, model: object, registry: object, index: { claims: object },
 *   page?: object, papers?: object }} given `page` is what the article's page says of
 *   itself (worker/page.mjs) and `papers` looks up the trial of a linked paper.
 */
export async function lookUp({ text, model, registry, index, page, papers, image, pageUrl }) {
  const numbers = unique([
    ...(text.match(REGISTRY_NUMBER) ?? []).map((number) => number.toUpperCase()),
    ...(page?.registryNumbers ?? []),
  ]);
  // Three hosts, none waiting on another: the model reads the text while the linked
  // papers and the registry numbers the article gives are looked up.
  const [reading, linked, stated] = await Promise.all([
    model.read(text, image ? { image, pageUrl } : undefined),
    paperNumbers(page, papers),
    inTurn(numbers, (number) => registry.fetch(number)),
  ]);
  if (!reading.about_a_treatment || !reading.intervention) return nothingFound(reading, numbers);

  const names = unique([reading.intervention, ...(reading.other_names ?? []).filter(isAName)]);
  // Names the model knows the treatment by. They widen the search; they are not from the text.
  const known = unique((reading.known_names ?? []).filter(isAName)).filter((name) => !names.includes(name));
  const terms = unique([...names, ...names.flatMap(partsOf), ...known, ...(reading.search_phrases ?? [])]);

  const details = {
    trial_name: reading.trial_name ?? null,
    participants: reading.participants ?? null,
    sponsor: reading.sponsor ?? null,
  };
  const fromPapers = linked.filter((number) => !numbers.includes(number));
  // What is known by number or by the trial's name comes first, so it is never cut off.
  const records = new Map();
  for (const given of [...stated, ...(await inTurn(fromPapers, (number) => registry.fetch(number)))]) {
    if (given) records.set(idOf(given), given);
  }
  if (details.trial_name) {
    for (const study of await registry.named(details.trial_name)) {
      if (!records.has(idOf(study))) records.set(idOf(study), study);
    }
  }
  for (const term of terms) {
    for (const study of await registry.search(term, reading.indication)) {
      if (!records.has(idOf(study))) records.set(idOf(study), study);
    }
  }
  const found = [...records.values()].slice(0, MAX_CANDIDATES);

  const alsoKnown = [...names.slice(1), ...known];
  const also = alsoKnown.length ? ` (also known as: ${alsoKnown.join(", ")})` : "";
  const intro =
    `Claim: ${reading.gist}\nIntervention: ${names[0]}${also}.\n` +
    `Indication: ${reading.indication}.\n\nEntity to match (intervention): ${names[0]}`;
  const scores = found.length ? await model.score(intro, found.map(candidateText)) : [];

  const candidates = found
    .map((study, at) => ({ study, scored: scores[at] }))
    .filter(({ scored }) => scored)
    .map(({ study, scored }) => {
      const section = study.protocolSection;
      return {
        id: idOf(study),
        url: `https://clinicaltrials.gov/study/${idOf(study)}`,
        score: scored.probabilities.match,
        answer: scored.answer,
        // Why it is ranked where it is, beyond the score: codes from worker/details.mjs.
        agrees: [
          ...(numbers.includes(idOf(study)) ? [STATED] : []),
          ...(fromPapers.includes(idOf(study)) ? [PAPER] : []),
          ...agreeing(study, details),
        ],
        title: section.identificationModule?.briefTitle ?? "",
        conditions: section.conditionsModule?.conditions ?? [],
        interventions: (section.armsInterventionsModule?.interventions ?? []).map((one) => one.name),
        phases: section.designModule?.phases ?? [],
        state: section.statusModule?.overallStatus ?? null,
      };
    })
    // A record the article itself names is first whatever its score. Then the records
    // that read as trials of the treatment, those agreeing with more details first.
    .sort(
      (a, b) =>
        Number(b.agrees.includes(STATED)) - Number(a.agrees.includes(STATED)) ||
        Number(b.score >= LIKELY_FROM) - Number(a.score >= LIKELY_FROM) ||
        b.agrees.length - a.agrees.length ||
        b.score - a.score ||
        a.id.localeCompare(b.id),
    );

  const wanted = new Set([...names, ...known].map(nameKey));
  const tracked = Object.entries(index?.claims ?? {})
    .filter(([, claim]) => (claim.names ?? []).some((name) => wanted.has(nameKey(name))))
    .map(([slug, claim]) => ({ slug, headline: claim.headline, page: claim.page }))
    .sort((a, b) => a.slug.localeCompare(b.slug));

  return {
    about_a_treatment: true,
    gist: reading.gist ?? "",
    treatment: names[0],
    condition: reading.indication ?? null,
    names,
    known_names: known,
    registry_numbers: numbers,
    paper_numbers: fromPapers,
    details,
    tracked,
    candidates,
    unscored: found.length - candidates.length,
  };
}
