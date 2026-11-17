// The site's fixed words for a trial's own page, and the rules that turn a registry
// record's codes into them. Plain JavaScript: the Worker that answers /trials/<number>,
// the search box and the build all read this one file. Behaviour: openspec trial-pages.
//
// A trial page states what a registry record says. It never says how a trial turned
// out, and never that a trial is open to anyone: a build fails on such a word below.

// The registry's states, by the mapping of openspec trial-facts (the pipeline holds the
// same one in events/trial_facts.py). Every state that says a trial is looking for
// people becomes "under_way".
export const REGISTRY_STATES = {
  NOT_YET_RECRUITING: "not_started",
  RECRUITING: "under_way",
  ENROLLING_BY_INVITATION: "under_way",
  ACTIVE_NOT_RECRUITING: "under_way",
  COMPLETED: "completed",
  SUSPENDED: "suspended",
  TERMINATED: "terminated",
  WITHDRAWN: "withdrawn",
  UNKNOWN: "unknown",
};

// One fixed phrase for each state, accepted as written by the operator on 2026-11-17
// (openspec trial-first-route, design decision 2).
export const STATE_PHRASES = {
  not_started: "The registry lists this study as not yet started.",
  under_way: "The registry lists this study as started and not yet finished.",
  completed:
    "The registry lists this study as completed. That says the study ended, not what it found.",
  suspended: "The registry lists this study as paused.",
  terminated: "The registry lists this study as stopped early.",
  withdrawn: "The registry lists this study as withdrawn before anyone was enrolled.",
  unknown:
    "The registry lists this study's state as unknown: its record has not been confirmed for some time.",
};
// A state the registry has that the mapping does not: said as that, never guessed.
export const STATE_NOT_WORDED =
  "The registry gives this study a state this page has no words for. The registry's own record shows it.";

// Short forms, for a search result's one line.
export const STATE_WORDS = {
  not_started: "Not started",
  under_way: "Under way",
  completed: "Completed",
  suspended: "Paused",
  terminated: "Stopped early",
  withdrawn: "Withdrawn before it started",
  unknown: "State unknown",
};

export const PHASE_WORDS = {
  EARLY_PHASE1: "Early Phase 1",
  PHASE1: "Phase 1",
  PHASE2: "Phase 2",
  PHASE3: "Phase 3",
  PHASE4: "Phase 4",
  early_phase_1: "Early Phase 1",
  phase_1: "Phase 1",
  phase_2: "Phase 2",
  phase_3: "Phase 3",
  phase_4: "Phase 4",
};
export const NO_PHASE = "The registry gives no phase for this study.";

export const NO_REPORT = "No news report is linked to this record yet.";
export const NO_RESULTS = "The registry record holds no posted results.";
// For a record that says results are posted and gives no date for it.
export const RESULTS_UNDATED = "The registry record holds posted results.";
export const resultsPosted = (day) => `Results were first posted on the registry record on ${day}.`;
export const NOT_STATED = "Not stated";
export const STOPPED_REASON = "The reason the registry record gives for stopping:";
export const SELECTED_FIELDS =
  "Selected fields from ClinicalTrials.gov, formatted for reading. Registry text is reproduced without interpretation.";

export const PAGE_LABELS = {
  crumb: "Trial record",
  phase: "Phase",
  conditions: "Conditions",
  interventions: "Interventions",
  enrolment: "Enrolment",
  sponsor: "Lead sponsor",
  dates: "Study and record dates",
  results: "Results on the registry",
  start: "Study start",
  primaryCompletion: "Primary completion",
  completion: "Study completion",
  firstPosted: "Record first posted",
  lastChanged: "Record last changed by the registry",
  read: "Record read from the registry",
  planned: "planned",
  actual: "actual",
  estimated: "estimated",
  open: "Open the full record on ClinicalTrials.gov",
};

// What the search says of trials found in the listing.
export const SEARCH_WORDS = {
  heading: "Registered trials with these words",
  note: "Phase 2 and 3 studies that ClinicalTrials.gov lists as not finished. A trial on record is not a treatment option.",
  open: "See the registry facts",
  claim: "See the tracked claim",
  more: (count) => `And ${count} more. Add a word to narrow them.`,
};

// Words that say how a trial turned out, or that speak to a reader as someone who might
// take part. None may stand in this file's wording, and the tests hold a built trial
// page to the same list.
export const FORBIDDEN_WORDS =
  /\b(success\w*|fail\w*|positive|negative|promising|effective\w*|ineffective\w*|work(?:s|ed)|prove[nsd]?|breakthrough\w*|cure[sd]?|met|missed|significan\w*|dead|abandon\w*|late|overdue|missing|recruit\w*|enrol+ing|enrol+ now|join|eligib\w*|options?|available|participat\w*|take part|taking part|contact\w*|sign up|should|recommend\w*|advice|advis\w*)\b/i;

/** The first forbidden word in a text, or null. */
export const forbiddenWord = (text) => String(text).match(FORBIDDEN_WORDS)?.[0] ?? null;

export function assertPlainWording(texts) {
  for (const text of texts) {
    const found = forbiddenWord(text);
    if (found) {
      throw new Error(
        `Verdict or advice wording "${found}" in trial page wording: "${text}". A trial page states what a registry record says, never how a trial turned out or that it is open to anyone.`,
      );
    }
  }
}

export const FIXED_WORDING = [
  ...Object.values(STATE_PHRASES),
  STATE_NOT_WORDED,
  ...Object.values(STATE_WORDS),
  ...Object.values(PHASE_WORDS),
  NO_PHASE,
  NO_REPORT,
  NO_RESULTS,
  RESULTS_UNDATED,
  resultsPosted("3 March 2025"),
  NOT_STATED,
  STOPPED_REASON,
  SELECTED_FIELDS,
  ...Object.values(PAGE_LABELS),
  SEARCH_WORDS.heading,
  // The one sentence that must name what a trial is not; checked without that clause.
  SEARCH_WORDS.note.replace("A trial on record is not a treatment option.", ""),
  SEARCH_WORDS.open,
  SEARCH_WORDS.claim,
  SEARCH_WORDS.more(3),
];
assertPlainWording(FIXED_WORDING);

/** The site's state for a registry status code; null for a code the mapping lacks. */
export const stateOf = (status) => REGISTRY_STATES[status] ?? null;

/** The phrase for a registry status code. A record with no status is "unknown". */
export function statePhrase(status) {
  if (typeof status !== "string" || !status) return STATE_PHRASES.unknown;
  const state = stateOf(status);
  return state ? STATE_PHRASES[state] : STATE_NOT_WORDED;
}

/** Phases in the site's words, or null when the registry gives none ("NA" or empty). */
export function phaseWords(phases) {
  const named = (Array.isArray(phases) ? phases : []).map((phase) => PHASE_WORDS[phase]).filter(Boolean);
  return named.length ? named.join(", ") : null;
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** A registry date as it is given: a year, a month or a day. Never a day invented for a
 * month. `long` writes the month in full. Null when the value is not a date. */
export function registryDate(value, long = false) {
  if (typeof value !== "string" || !/^\d{4}(?:-\d{2}(?:-\d{2})?)?$/.test(value)) return null;
  const [year, month, day] = value.split("-");
  if (!month) return year;
  const name = MONTHS[Number(month) - 1];
  if (!name) return null;
  const shown = long ? name : name.slice(0, 3);
  return day ? `${Number(day)} ${shown} ${year}` : `${shown} ${year}`;
}

/** What the page says of posted results, from the record's flag and its date alone. */
export function resultsPhrase(hasResults, firstPosted) {
  const day = registryDate(firstPosted, true);
  if (day) return resultsPosted(day);
  return hasResults === true ? RESULTS_UNDATED : NO_RESULTS;
}

// --- finding a trial in the listing ---------------------------------------------------

const COLUMNS = ["id", "title", "acronym", "phases", "state", "updated", "conditions", "interventions", "claim"];

/** One listing row as an object, whatever order the file's columns are in. */
export function listedTrial(listing, row) {
  const columns = Array.isArray(listing?.columns) ? listing.columns : COLUMNS;
  return Object.fromEntries(columns.map((name, at) => [name, row[at]]));
}

/** The listed trial with this registry number, or null. */
export function findListed(listing, id) {
  const wanted = String(id).toUpperCase();
  const row = (listing?.trials ?? []).find((candidate) => candidate[0] === wanted);
  return row ? listedTrial(listing, row) : null;
}

const wordsOf = (text) => String(text ?? "").toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(Boolean);

/**
 * Listed trials that hold every searched word, as a whole word or the start of one, in
 * the title, acronym, an intervention's name or a condition. Ordered by a fixed rule:
 * the acronym or an intervention named exactly, then words in the title, then the
 * record the registry changed most recently. Never a score shown to a reader.
 * @returns {{ total: number, trials: object[] }}
 */
export function searchListing(listing, query, limit = 8) {
  // A lone letter finds too much to be a search; a lone digit is part of a name ("EX-2").
  const words = [...new Set(wordsOf(query))].filter((word) => word.length > 1 || /\d/.test(word));
  if (!words.length) return { total: 0, trials: [] };
  const asked = words.join(" ");
  const found = [];
  for (const row of listing?.trials ?? []) {
    const trial = listedTrial(listing, row);
    const title = wordsOf(trial.title);
    const names = [trial.acronym, ...(trial.interventions ?? [])].filter(Boolean);
    const rest = [...names, ...(trial.conditions ?? [])].flatMap(wordsOf);
    const all = [...title, ...rest];
    if (!words.every((word) => all.some((held) => held.startsWith(word)))) continue;
    let weight = 0;
    if (names.some((name) => wordsOf(name).join(" ") === asked)) weight += 4;
    if (words.every((word) => title.some((held) => held.startsWith(word)))) weight += 2;
    found.push({ trial, weight });
  }
  found.sort(
    (a, b) =>
      b.weight - a.weight ||
      String(b.trial.updated ?? "").localeCompare(String(a.trial.updated ?? "")) ||
      a.trial.id.localeCompare(b.trial.id),
  );
  return { total: found.length, trials: found.slice(0, limit).map((entry) => entry.trial) };
}
