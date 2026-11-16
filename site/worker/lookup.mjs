// From a piece of text to ranked trial records. Pure orchestration: the model, the
// registry and the index of tracked claims are passed in. Behaviour: openspec live-lookup.
// The same steps as the pipeline's thenwhat.lookup.service; keep the two in step.
//
// The answer carries codes and registry fields only. The site words them.
import { PAPER, STATED, agreeing } from "./details.mjs";
import { isAName, partsOf } from "./names.mjs";
import { withCurrentClaims } from "./tracked.mjs";
import { LIKELY_FROM } from "../src/lib/live-lookup.mjs";
import { timedOut, withDeadline } from "./deadline.mjs";

const REGISTRY_NUMBER = /\bNCT\d{8}\b/gi;
// The most records one lookup will ask the model about.
const MAX_CANDIDATES = 60;
const MAX_RECORD_CHARACTERS = 1500;
// The most linked papers one lookup asks about.
const MAX_PAPERS = 3;

const unique = (items) => [...new Set(items)];
const idOf = (study) => study.protocolSection.identificationModule.nctId;
const excerpt = (value, limit) => typeof value === "string" && value.length > limit
  ? `${value.slice(0, limit - " [truncated]".length)} [truncated]` : value;

// Keep membership once when both registry directions say exactly the same thing.
// Unpaired or inconsistent labels still reach the scorer; they are not inferred.
function unshownArms(intervention, arms) {
  return (intervention.armGroupLabels ?? []).filter(label => !arms.some(arm =>
    arm.label === label && (arm.interventionNames ?? []).some(name =>
      name === intervention.name || name.replace(/^[^:]+: /, "") === intervention.name)));
}

/** A registry record as it is shown to the model: what decides a match comes first. */
function candidateText(study) {
  const section = study.protocolSection ?? {};
  const treatment = section.armsInterventionsModule ?? {};
  const official = section.identificationModule?.officialTitle;
  // A complete short official title often holds the population the brief title omits.
  // Long titles remain secondary so boilerplate cannot displace treatment details.
  const title = official && official.length <= 240 ? official : section.identificationModule?.briefTitle;
  const described = {
    conditions: section.conditionsModule?.conditions ?? [],
    study_type: section.designModule?.studyType,
    title: excerpt(title, 240),
    // Arm roles and membership precede verbose descriptions: these establish
    // what is tested even when the record's later details exceed the limit.
    arms: (treatment.armGroups ?? []).map((arm) => ({
      label: arm.label ?? null, type: arm.type ?? null, interventions: arm.interventionNames ?? [],
    })),
    interventions: (treatment.interventions ?? []).map((one) => {
      const arms = unshownArms(one, treatment.armGroups ?? []);
      return { name: one.name ?? null, description: excerpt(one.description ?? null, 350), ...(arms.length ? { arms } : {}) };
    }),
    arm_descriptions: (treatment.armGroups ?? []).filter(arm => arm.description).map((arm) => ({
      label: arm.label ?? null, description: excerpt(arm.description, 350),
    })),
    official_title: official !== title ? excerpt(official, 240) : null,
    phases: section.designModule?.phases ?? [],
    status: section.statusModule?.overallStatus,
    sponsor: section.sponsorCollaboratorsModule?.leadSponsor?.name,
  };
  const kept = Object.fromEntries(
    Object.entries(described).filter(([, value]) => (Array.isArray(value) ? value.length : value)),
  );
  return `Candidate record from clinicaltrials.gov (${idOf(study)}):\n${excerpt(JSON.stringify(kept), MAX_RECORD_CHARACTERS)}`;
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
    papers_unchecked: 0,
    details: { trial_name: null, participants: null, sponsor: null },
    tracked: [],
    candidates: [],
    unscored: 0,
  };
}

// Linked papers together are waited on no longer than this, from the first request.
const PAPER_ALLOWANCE_MS = 5_000;
// Requests for linked papers start at least this far apart: two a second.
const PAPER_SPACING_MS = 500;
// The order registry requests are made in when several wait: what the article gives by
// number first, then what its papers give, then the trial's name, then the searches.
const STATED_FIRST = 0;
const FROM_PAPERS = 1;
const BY_NAME = 2;
const BY_SEARCH = 3;

const stopped = () => Object.assign(new Error("lookup ended"), { name: "AbortError" });

/** A wait of `ms` that ends early when `signal` is aborted. */
function pauseFor(ms, signal) {
  return new Promise((resolve) => {
    if (signal.aborted) { resolve(); return; }
    const done = () => { clearTimeout(timer); signal.removeEventListener("abort", done); resolve(); };
    const timer = setTimeout(done, ms);
    signal.addEventListener("abort", done, { once: true });
  });
}

/** One request at a time to the registry, most important first, in order within each
 * importance. None is made once `signal` is aborted, or once one has failed, since that
 * fails the lookup: each waiting one rejects instead. */
function registryQueue(signal) {
  const waiting = [];
  let busy = false;
  let failed = null;
  const next = () => {
    while (!busy && waiting.length) {
      let at = 0;
      for (let one = 1; one < waiting.length; one += 1) if (waiting[one].priority < waiting[at].priority) at = one;
      const [job] = waiting.splice(at, 1);
      if (signal.aborted || failed) { job.reject(failed ?? signal.reason ?? stopped()); continue; }
      busy = true;
      Promise.resolve().then(job.ask)
        .then(job.resolve, (error) => { failed = error; job.reject(error); })
        .finally(() => { busy = false; next(); });
    }
  };
  return (priority, ask) => new Promise((resolve, reject) => {
    waiting.push({ priority, ask, resolve, reject });
    next();
  });
}

/** The papers the page links to, by DOI or PubMed number. */
function linkedPapers(page) {
  return [
    ...(page?.dois ?? []).map((doi) => ({ doi })),
    ...(page?.pubmedIds ?? []).map((pubmedId) => ({ pubmedId })),
  ].slice(0, MAX_PAPERS);
}

/** The registry numbers given by the papers the page links to, and how many of those
 * papers could not be looked up: one that failed, that its host did not answer in time,
 * or that the allowance for them all ran out before. The lookup goes on without such a
 * paper and its answer says how many there were. A later paper is asked while an earlier
 * one is still waited on. Aborting `signal` ends the requests in flight and asks no more. */
async function paperNumbers(page, papers, signal, { allowanceMs, spacingMs }) {
  if (!page || !papers) return { numbers: [], unchecked: 0 };
  const linked = linkedPapers(page);
  if (!linked.length || signal.aborted) return { numbers: [], unchecked: 0 };
  const allowance = new AbortController();
  const end = () => allowance.abort(signal.reason ?? stopped());
  signal.addEventListener("abort", end, { once: true });
  const timer = setTimeout(() => allowance.abort(timedOut("papers")), allowanceMs);
  // The allowance ends every wait, even on a paper client that does not listen.
  const over = new Promise((_resolve, reject) => {
    allowance.signal.addEventListener("abort", () => reject(allowance.signal.reason), { once: true });
  });
  over.catch(() => {});
  const ask = async (paper, at) => {
    if (at) await pauseFor(at * spacingMs, allowance.signal);
    if (allowance.signal.aborted) throw allowance.signal.reason;
    return Promise.race([papers.trialNumbers(paper, { signal: allowance.signal }), over]);
  };
  try {
    const answers = await Promise.allSettled(linked.map(ask));
    const found = answers.flatMap((one) => (one.status === "fulfilled" && Array.isArray(one.value) ? one.value : []));
    return { numbers: unique(found), unchecked: answers.filter((one) => one.status === "rejected").length };
  } finally {
    clearTimeout(timer);
    signal.removeEventListener("abort", end);
    allowance.abort(stopped());
  }
}

/**
 * @param {{ text: string, model: object, registry: object, index: { claims: object },
 *   page?: object, papers?: object, onCore?: (core: object) => void, timings?: object }} given
 *   `page` is what the article's page says of itself (worker/page.mjs) and `papers` looks
 *   up the trial of a linked paper. `onCore` is given the answer once every clinical
 *   search and score is done, before optional research enrichment is waited on.
 *   `timings` holds stage durations; core_ms and total_ms are elapsed milestones.
 *   registry_ms sums active requests, excluding time waiting in the lookup queue.
 */
export async function lookUp({ text, model, registry, index, page, papers, research, image, pageUrl, onCore, timings,
  paperAllowanceMs = PAPER_ALLOWANCE_MS, paperSpacingMs = PAPER_SPACING_MS, timeBudgetMs = 45_000, now = Date.now }) {
  const started = now();
  const took = (stage, since = started) => { if (timings) timings[stage] = Math.max(0, now() - since); };
  const numbers = unique([
    ...(text.match(REGISTRY_NUMBER) ?? []).map((number) => number.toUpperCase()),
    ...(page?.registryNumbers ?? []),
  ]);
  // Three hosts, none waiting on another: the model reads the text while the linked
  // papers and the registry numbers the article gives are looked up. Only a treatment
  // needs those: an answer that it is not one is given as soon as the model has read,
  // and the other two are stopped, since nothing they say would change that answer.
  const others = new AbortController();
  const queued = registryQueue(others.signal);
  if (timings) timings.registry_ms = 0;
  const ask = (priority, work) => queued(priority, async () => {
    const began = now();
    try { return await work(); }
    finally { if (timings) timings.registry_ms += Math.max(0, now() - began); }
  });
  const asking = { signal: others.signal };
  const read = model.read(text, image ? { image, pageUrl } : undefined);
  const paperStarted = now();
  const linking = paperNumbers(page, papers, others.signal, { allowanceMs: paperAllowanceMs, spacingMs: paperSpacingMs })
    .finally(() => took("papers_ms", paperStarted));
  const stating = Promise.all(numbers.map((number) => ask(STATED_FIRST, () => registry.fetch(number, asking))));
  // A failure of either is raised where they are awaited below, and nowhere else.
  linking.catch(() => {});
  stating.catch(() => {});
  const core = (found) => {
    took("core_ms");
    try { onCore?.(found); } catch { /* A listener cannot change or fail the answer. */ }
    return found;
  };
  let reading;
  try {
    reading = await read;
  } catch (error) {
    others.abort();
    throw error;
  }
  took("read_ms");
  const claims = [reading, ...(Array.isArray(reading.additional_claims) ? reading.additional_claims : [])]
    .filter(one => one?.about_a_treatment && one.intervention);
  if (claims.length > 1) {
    try {
      return await lookUpMany({ claims, model, registry, index, numbers, linking, stating, ask, asking,
        others, core, took, started, now, timeBudgetMs });
    } finally { others.abort(); }
  }
  // An identifiable second item must not be lost if the first was an unspecified drug.
  if (claims.length === 1) reading = claims[0];
  if (!reading.about_a_treatment || !reading.intervention) {
    others.abort();
    const found = core(nothingFound(reading, numbers));
    took("total_ms");
    return found;
  }

  try {
    // Metadata enrichment starts as soon as the treatment is known. It adds no model
    // calls and cannot change clinical candidates, their scores, or a tracked claim's status.
    const researchStarted = now();
    const related = research ? Promise.resolve().then(() => research.search({
      intervention: reading.intervention,
      indication: reading.indication,
      searchPhrases: reading.search_phrases ?? [],
      organisations: [...(Array.isArray(reading.organisations) ? reading.organisations : []), reading.sponsor].filter(Boolean),
      linked: linkedPapers(page),
      published: page?.published ?? null,
    })).catch(() => ({ papers: [], organisations: [], availability: { openalex: "unavailable", ror: "unavailable" } }))
      .finally(() => took("research_ms", researchStarted)) : null;

    const names = unique([reading.intervention, ...(reading.other_names ?? []).filter(isAName)]);
    // Names the model knows the treatment by. They widen the search; they are not from the text.
    const known = unique((reading.known_names ?? []).filter(isAName)).filter((name) => !names.includes(name));
    const terms = unique([...names, ...names.flatMap(partsOf), ...known, ...(reading.search_phrases ?? [])]);

    const details = {
      trial_name: reading.trial_name ?? null,
      participants: reading.participants ?? null,
      sponsor: reading.sponsor ?? null,
    };
    // The registry is asked by name while linked papers are still being looked up. What
    // is known by number or by the trial's name comes first, so it is never cut off.
    const byPapers = linking.then(async ({ numbers: linked, unchecked }) => {
      const fromPapers = linked.filter((number) => !numbers.includes(number));
      const given = await Promise.all(fromPapers.map((number) => ask(FROM_PAPERS, () => registry.fetch(number, asking))));
      return { fromPapers, unchecked, given };
    });
    const byName = details.trial_name ? ask(BY_NAME, () => registry.named(details.trial_name, asking)) : Promise.resolve([]);
    const bySearch = Promise.all(terms.map((term) => ask(BY_SEARCH, () => registry.search(term, reading.indication, asking))));
    const [stated, { fromPapers, unchecked: papersUnchecked, given }, named, searched] =
      await Promise.all([stating, byPapers, byName, bySearch]);
    const records = new Map();
    for (const one of [...stated, ...given]) {
      if (one) records.set(idOf(one), one);
    }
    for (const study of [...named, ...searched.flat()]) {
      if (!records.has(idOf(study))) records.set(idOf(study), study);
    }
    const found = [...records.values()].slice(0, MAX_CANDIDATES);

    const alsoKnown = [...names.slice(1), ...known];
    const also = alsoKnown.length ? ` (also known as: ${alsoKnown.join(", ")})` : "";
    const intro =
      `Claim: ${reading.gist}\nIntervention: ${names[0]}${also}.\n` +
      `Indication: ${reading.indication}.\n\nEntity to match (intervention): ${names[0]}`;
    const scoring = now();
    const scores = found.length ? await model.score(intro, found.map(candidateText)) : [];
    took("score_ms", scoring);

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


    const clinical = core(withCurrentClaims({
      about_a_treatment: true,
      gist: reading.gist ?? "",
      treatment: names[0],
      condition: reading.indication ?? null,
      names,
      known_names: known,
      registry_numbers: numbers,
      paper_numbers: fromPapers,
      // Linked papers that could not be looked up: a trial one of them reports may be missing.
      papers_unchecked: papersUnchecked,
      details,
      candidates,
      unscored: found.length - candidates.length,
    }, index));
    const answer = related ? { ...clinical, research: await related } : clinical;
    took("total_ms");
    return answer;
  } finally {
    // Whatever is still waiting, on success or failure, is no longer needed.
    others.abort();
  }
}

/** A roundup shares one allowance, not a full independent lookup per claim. Explicit
 * records/papers are fetched once; each record is still scored against its own claim. */
async function lookUpMany({ claims, model, registry, index, numbers, linking, stating, ask, asking,
  others, core, took, started, now, timeBudgetMs }) {
  const plans = claims.map(reading => {
    const names = unique([reading.intervention, ...(reading.other_names ?? []).filter(isAName)]);
    const known = unique((reading.known_names ?? []).filter(isAName)).filter(name => !names.includes(name));
    const details = { trial_name: reading.trial_name ?? null, participants: reading.participants ?? null, sponsor: reading.sponsor ?? null };
    const terms = unique([...names, ...names.flatMap(partsOf), ...known, ...(reading.search_phrases ?? [])]);
    const also = [...names.slice(1), ...known];
    return { reading, names, known, details, records: [], selected: [], scores: [], queries: [], searched: new Set(), missing: false,
      intro: `Claim: ${reading.gist ?? ""}\nIntervention: ${names[0]}${also.length ? ` (also known as: ${also.join(", ")})` : ""}.\nIndication: ${reading.indication}.\n\nEntity to match (intervention): ${names[0]}`,
      jobs: [
        ...(details.trial_name ? [{ key: ["named", details.trial_name], priority: BY_NAME, work: () => registry.named(details.trial_name, asking) }] : []),
        ...terms.map(term => ({ key: ["search", term, reading.indication], priority: BY_SEARCH, work: () => registry.search(term, reading.indication, asking) })),
      ],
    };
  });
  let fromPapers = [], papersUnchecked = 0, failure = null;
  try {
    const remaining = timeBudgetMs - (now() - started);
    if (remaining <= 0) throw timedOut("lookup");
    await withDeadline(remaining, async signal => {
      const stop = () => others.abort(signal.reason);
      signal.addEventListener("abort", stop, { once: true });
      try {
        const byPapers = linking.then(async ({ numbers: linked, unchecked }) => {
          fromPapers = linked.filter(number => !numbers.includes(number));
          papersUnchecked = unchecked;
          return Promise.all(fromPapers.map(number => ask(FROM_PAPERS, () => registry.fetch(number, asking))));
        });
        byPapers.catch(() => {});
        const shared = new Map();
        // Round-robin admission gives each claim its first search before aliases can
        // exhaust the twelve-query page allowance. The queue retains source pacing.
        for (let at = 0; plans.some(plan => at < plan.jobs.length); at++) {
          for (const plan of plans) {
            const job = plan.jobs[at];
            if (!job) continue;
            const key = JSON.stringify(job.key);
            if (!shared.has(key) && shared.size >= 12) { plan.missing = true; continue; }
            if (!shared.has(key)) {
              const pending = ask(job.priority, job.work);
              pending.catch(() => {});
              shared.set(key, pending);
            }
            plan.queries.push(shared.get(key));
            if (job.key[0] === "search") plan.searched.add(job.key[1]);
          }
        }
        const [stated, linked, searched] = await Promise.all([
          stating, byPapers, Promise.all(plans.map(plan => Promise.all(plan.queries))),
        ]);
        if (signal.aborted) throw signal.reason;
        for (let at = 0; at < plans.length; at++) {
          const records = new Map();
          for (const record of [...stated, ...linked, ...searched[at].flat()]) {
            if (record && !records.has(idOf(record))) records.set(idOf(record), record);
          }
          plans[at].records = [...records.values()];
        }
        // The sixty-pair limit covers all claims, including repeated records scored
        // for different indications. No clinical score is shared between claims.
        const pairs = [];
        for (let at = 0; pairs.length < MAX_CANDIDATES && plans.some(plan => at < plan.records.length); at++) {
          for (const plan of plans) {
            if (pairs.length === MAX_CANDIDATES) break;
            const record = plan.records[at];
            if (record) { plan.selected.push(record); pairs.push({ plan, record }); }
          }
        }
        const scoring = now();
        const scores = pairs.length ? await model.score(
          "Each item contains its own independent claim and one candidate record. Compare only that item's claim and record; never transfer an identity or score between items.",
          pairs.map(({ plan, record }) => `${plan.intro}\n\n${candidateText(record)}`), { signal },
        ) : [];
        took("score_ms", scoring);
        if (signal.aborted) throw signal.reason;
        pairs.forEach(({ plan }, at) => plan.scores.push(scores[at] ?? null));
      } finally { signal.removeEventListener("abort", stop); }
    }, { label: "lookup" });
  } catch (error) {
    if (error?.code === "budget_exhausted") throw error;
    failure = error?.code === "timeout" ? "timeout" : "source_unavailable";
  }
  const answers = plans.map(plan => {
    const candidates = plan.selected.flatMap((study, at) => {
      const scored = plan.scores[at];
      if (!scored) return [];
      const section = study.protocolSection;
      return [{ id: idOf(study), url: `https://clinicaltrials.gov/study/${idOf(study)}`,
        score: scored.probabilities.match, answer: scored.answer,
        agrees: [...(numbers.includes(idOf(study)) ? [STATED] : []), ...(fromPapers.includes(idOf(study)) ? [PAPER] : []), ...agreeing(study, plan.details)],
        title: section.identificationModule?.briefTitle ?? "", conditions: section.conditionsModule?.conditions ?? [],
        interventions: (section.armsInterventionsModule?.interventions ?? []).map(one => one.name),
        phases: section.designModule?.phases ?? [], state: section.statusModule?.overallStatus ?? null,
      }];
    }).sort((a, b) => Number(b.agrees.includes(STATED)) - Number(a.agrees.includes(STATED)) ||
      Number(b.score >= LIKELY_FROM) - Number(a.score >= LIKELY_FROM) || b.agrees.length - a.agrees.length || b.score - a.score || a.id.localeCompare(b.id));
    const unscored = plan.records.length - candidates.length;
    const reason = failure ?? (plan.missing || unscored ? "work_limit" : null);
    return withCurrentClaims({
      about_a_treatment: true, treatment: plan.names[0], condition: plan.reading.indication ?? null,
      gist: plan.reading.gist ?? "", names: plan.names, known_names: failure ? [] : plan.known.filter(name => plan.searched.has(name)),
      registry_numbers: numbers, paper_numbers: fromPapers, papers_unchecked: papersUnchecked,
      details: plan.details, candidates, unscored,
      check_state: reason ? candidates.length ? "partial" : "unchecked" : "complete", check_reason: reason,
      research: { papers: [], organisations: [], availability: { openalex: "not_checked", ror: "not_checked" } },
    }, index);
  });
  const found = core({ ...nothingFound({}, numbers), about_a_treatment: true, claims: answers });
  took("total_ms");
  return found;
}
