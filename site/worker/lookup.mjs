// From a piece of text to ranked trial records. Pure orchestration: the model, the
// registry and the index of tracked claims are passed in. Behaviour: openspec live-lookup.
// The same steps as the pipeline's thenwhat.lookup.service; keep the two in step.
//
// The answer carries codes and registry fields only. The site words them.
import { isAName, nameKey, partsOf } from "./names.mjs";

const REGISTRY_NUMBER = /\bNCT\d{8}\b/gi;
// The most records one lookup will ask the model about.
const MAX_CANDIDATES = 60;
const MAX_RECORD_CHARACTERS = 1500;

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
    tracked: [],
    candidates: [],
    unscored: 0,
  };
}

/**
 * @param {{ text: string, model: object, registry: object, index: { claims: object } }} given
 */
export async function lookUp({ text, model, registry, index }) {
  const numbers = unique((text.match(REGISTRY_NUMBER) ?? []).map((number) => number.toUpperCase()));
  const reading = await model.read(text);
  if (!reading.about_a_treatment || !reading.intervention) return nothingFound(reading, numbers);

  const names = unique([reading.intervention, ...(reading.other_names ?? []).filter(isAName)]);
  // Names the model knows the treatment by. They widen the search; they are not from the text.
  const known = unique((reading.known_names ?? []).filter(isAName)).filter((name) => !names.includes(name));
  const terms = unique([...names, ...names.flatMap(partsOf), ...known, ...(reading.search_phrases ?? [])]);

  const records = new Map();
  for (const number of numbers) {
    const stated = await registry.fetch(number);
    if (stated) records.set(idOf(stated), stated);
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
        title: section.identificationModule?.briefTitle ?? "",
        conditions: section.conditionsModule?.conditions ?? [],
        interventions: (section.armsInterventionsModule?.interventions ?? []).map((one) => one.name),
        phases: section.designModule?.phases ?? [],
        state: section.statusModule?.overallStatus ?? null,
      };
    })
    .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));

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
    tracked,
    candidates,
    unscored: found.length - candidates.length,
  };
}
