// "The record in brief": at most six fixed questions about a claim's records, each with
// a short answer and the record it was read from. Openspec site-publishing: "A claim
// page answers fixed questions from its records", "Each question has one fixed place",
// "Every answer shows the record it was read from", "The brief carries no result values".
//
// Pure: no clock, network or file. A question's place never depends on its answer, and
// "None on record" is said where its question sits. An answer states a fact and never
// begins with "Yes", so the list is not a tally. No answer carries a result value.

import type { ExportedClaim, ExportedEvent, ExportedReading, ExportedTrial } from "./export";
import { assertNeutral, sourceName } from "./status.ts";
import { formatDate } from "./timetable.ts";
import { COMPARATOR_WORDS, designText } from "./trial-facts.ts";

export interface BriefRecord {
  /** The registry's identifier, or the regulator's name. */
  label: string;
  url: string;
}

export interface BriefSource {
  how: "direct" | "model";
  /** What was read, as a clause: "3 ClinicalTrials.gov records". Null when `records` says it. */
  from: string | null;
  records: BriefRecord[];
  /** The day the record was read, or the registries last checked. */
  on: string | null;
  onLabel: "Record read" | "Records read" | "Registries last checked";
  /** For a model's reading: how sure it is, 0 to 1. */
  confidence: number | null;
}

export interface BriefRow {
  code: string;
  question: string;
  answer: string;
  /** Sentences shown when the answer is opened. */
  opened: string[];
  /** A link inside the opened answer, to records on the page. */
  link: { href: string; text: string } | null;
  /** A link shown under the answer without opening it. */
  shown: { href: string; text: string } | null;
  source: BriefSource;
}

export interface BriefGroup {
  code: "tested" | "now";
  name: string;
  rows: BriefRow[];
}

export const BRIEF_TITLE = "The record in brief";

export const GROUP_NAMES: Record<BriefGroup["code"], string> = {
  tested: "How it was tested",
  now: "Where the records stand now",
};

export const NONE = "None on record";

export const QUESTIONS = {
  tested: "Tested in people?",
  first_report: "What was the first report about?",
  measure: "What did the largest trial measure?",
  results: "Results posted to the registry?",
  under_way: "A trial under way?",
  approved: "Approved by a regulator?",
} as const;

/** What a trial is compared with, by the kind of treatment: a device has a dummy device. */
const DUMMY = {
  device: { noun: "a dummy device", plural: "a dummy device" },
  other: { noun: "a placebo", plural: "a placebo" },
} as const;

export const DEFINITIONS = {
  sham: "A sham is a device or procedure that looks the same and does nothing.",
  placebo: "A placebo looks like the treatment and has no active ingredient.",
  posted:
    "Posting means the sponsor put the trial's numbers on the registry. It does not say what the numbers show.",
  under_way:
    "A trial counts as under way when the registry lists it as started and not yet finished. This does not say a trial is open to new participants.",
  regulator: "A regulator is a public body that decides whether a treatment may be sold or used.",
  approval: "An approval is not advice to take a treatment",
  approval_scope: "Its approval covers the uses it names, in the place it governs.",
  no_trial: "No trial in people for this treatment and condition is among the records this site holds.",
  no_approval: "No approval of this treatment for this condition is among the records this site holds.",
  registry_words: "These are the registry's words. No plainer wording is given for this measure.",
} as const;

/** What the first report was about, when no trial is on record. */
export const FIRST_REPORT: Record<string, { answer: string; opened: string }> = {
  in_vitro: {
    answer: "A study in the laboratory",
    opened: "The first news report described a study in the laboratory. A result in the laboratory is not a result in people.",
  },
  animal: {
    answer: "A study in animals",
    opened: "The first news report described a study in animals. A result in animals is not a result in people.",
  },
  early_human: {
    answer: "An early study in people",
    opened: "The first news report described an early study in people. No registered trial of it is among the records this site holds.",
  },
  late_human: {
    answer: "A later study in people",
    opened: "The first news report described a later study in people. No registered trial of it is among the records this site holds.",
  },
};

/** The site's phrase for each kind of measure a reading can name: as stated, and as a
 * change when the registry's title names a change. "other" has no phrase. */
export const MEASURE_PHRASES: Record<string, { plain: string; change: string }> = {
  symptom_score: { plain: "A symptom score", change: "How much a symptom score changed" },
  frequency: { plain: "How often an event happened", change: "The change in how often an event happened" },
  body_measure: {
    plain: "A body measurement or lab value",
    change: "The change in a body measurement or lab value",
  },
  scan_finding: { plain: "What a scan or image showed", change: "The change in what a scan or image showed" },
  survival: { plain: "How long until an event, such as a relapse", change: "How long until an event, such as a relapse" },
  side_effects: { plain: "Side effects", change: "The change in side effects" },
  use_of_treatment: { plain: "How much the treatment was used", change: "How much the treatment was used" },
  quality_of_life: { plain: "A quality-of-life score", change: "How much a quality-of-life score changed" },
};

/** A reading less sure than this is not used; the answer gives the registry's own title. */
export const READING_SHOWN_FROM = 0.5;

const READING_BANDS = [
  { from: 0.5, word: "likely" },
  { from: 0.8, word: "very likely" },
] as const;

/** "very likely · 92%": how sure a reading is. Never how sure a result is. */
export function readingConfidenceLabel(confidence: number): string {
  let word: string = READING_BANDS[0].word;
  for (const band of READING_BANDS) if (confidence >= band.from) word = band.word;
  return `${word} · ${Math.round(confidence * 100)}%`;
}

const SMALL = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
const digits = (count: number) => count.toLocaleString("en-GB");
const word = (count: number) => SMALL[count] ?? digits(count);
const capital = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
const plural = (count: number, one: string, many: string) => (count === 1 ? one : many);
/** A date that never breaks across two lines. */
const day = (isoDate: string) => formatDate(isoDate).replace(/ /g, " ");

function latest(dates: (string | null | undefined)[]): string | null {
  const stated = dates.filter((date): date is string => Boolean(date)).sort();
  return stated[stated.length - 1] ?? null;
}

function registryOf(trials: ExportedTrial[]): string {
  const names = [...new Set(trials.map((trial) => sourceName(trial.source_name)))];
  return names.length === 1 ? names[0] : "registry";
}

function directFrom(trials: ExportedTrial[]): BriefSource {
  const on = latest(trials.map((trial) => trial.facts_as_of));
  if (trials.length === 1) {
    const [trial] = trials;
    return {
      how: "direct",
      from: null,
      records: [{ label: trial.trial_id, url: trial.url }],
      on,
      onLabel: "Record read",
      confidence: null,
    };
  }
  return {
    how: "direct",
    from: `${digits(trials.length)} ${registryOf(trials)} records`,
    records: [],
    on,
    onLabel: "Records read",
    confidence: null,
  };
}

function checked(lastChecked: string | null): BriefSource {
  return {
    how: "direct",
    from: "the records on this page",
    records: [],
    on: lastChecked,
    onLabel: "Registries last checked",
    confidence: null,
  };
}

const row = (fields: Omit<BriefRow, "link" | "shown"> & Partial<Pick<BriefRow, "link" | "shown">>): BriefRow => ({
  link: null,
  shown: null,
  ...fields,
});

/** The trial that states the most participants; the first of equals. Null when none states a number. */
export function largestTrial(trials: ExportedTrial[]): ExportedTrial | null {
  let found: ExportedTrial | null = null;
  for (const trial of trials) {
    const count = trial.facts?.participants?.count;
    if (count === undefined) continue;
    if (!found || count > (found.facts?.participants?.count ?? 0)) found = trial;
  }
  return found;
}

function testedRow(trials: ExportedTrial[], lastChecked: string | null): BriefRow {
  if (trials.length === 0) {
    return row({
      code: "tested",
      question: QUESTIONS.tested,
      answer: NONE,
      opened: [DEFINITIONS.no_trial],
      source: checked(lastChecked),
    });
  }
  const largest = largestTrial(trials);
  const count = `In ${digits(trials.length)} ${plural(trials.length, "trial", "trials")}`;
  if (!largest) {
    return row({
      code: "tested",
      question: QUESTIONS.tested,
      answer: count,
      opened: ["No trial's record states how many people it enrolled."],
      link: { href: "#trials", text: plural(trials.length, "See the trial", `See the ${digits(trials.length)} trials`) },
      source: directFrom(trials),
    });
  }
  const size = largest.facts!.participants!;
  const others = trials
    .filter((trial) => trial !== largest)
    .map((trial) => trial.facts?.participants?.count)
    .filter((stated): stated is number => stated !== undefined)
    .sort((a, b) => b - a);
  const opened: string[] = [];
  if (others.length === 1) opened.push(`The other trial enrolled ${digits(others[0])} people.`);
  else if (others.length > 1 && others.length <= 3) {
    const listed = `${others.slice(0, -1).map(digits).join(", ")} and ${digits(others[others.length - 1])}`;
    opened.push(`The other ${word(others.length)} trials enrolled ${listed} people.`);
  } else if (others.length > 3) {
    opened.push(
      `The others enrolled between ${digits(others[others.length - 1])} and ${digits(others[0])} people.`,
    );
  }
  opened.push(
    size.basis === "planned"
      ? "The largest number is a planned size, not people who took part."
      : "The largest number is people who took part, not a planned size.",
  );
  return row({
    code: "tested",
    question: QUESTIONS.tested,
    answer:
      trials.length === 1
        ? `In 1 trial of ${digits(size.count)} people`
        : `${count}. ${digits(size.count)} people in the largest`,
    opened,
    link: { href: "#trials", text: plural(trials.length, "See the trial", `See the ${digits(trials.length)} trials`) },
    source: directFrom(trials),
  });
}

const statesDesign = (trial: ExportedTrial) =>
  Boolean(trial.facts && (trial.facts.allocation || trial.facts.masking || trial.facts.comparators.length > 0));
const namesDummy = (trial: ExportedTrial) =>
  (trial.facts?.comparators ?? []).some((code) => code === "sham" || code === "placebo");

/** Counts records that name a dummy comparison. It never says the other trials had none. */
function comparisonRow(claim: ExportedClaim, trials: ExportedTrial[]): BriefRow | null {
  if (!trials.some(statesDesign)) return null;
  const dummy = claim.approach === "device" ? DUMMY.device : DUMMY.other;
  const naming = trials.filter(namesDummy);
  const question = `Compared with ${dummy.noun}?`;
  if (naming.length === 0) {
    return row({
      code: "comparison",
      question,
      answer: "No record names one",
      opened: [
        `No trial's record names ${dummy.noun} as a comparison.`,
        claim.approach === "device" ? DEFINITIONS.sham : DEFINITIONS.placebo,
      ],
      source: directFrom(trials),
    });
  }
  const opened: string[] = [];
  if (naming.length === 1) {
    const design = designText(naming[0].facts);
    if (design) opened.push(`The registry gives that trial's design as: ${design.charAt(0).toLowerCase()}${design.slice(1)}.`);
  }
  const kinds = new Set(naming.flatMap((trial) => trial.facts?.comparators ?? []));
  if (kinds.has("sham")) opened.push(DEFINITIONS.sham);
  if (kinds.has("placebo")) opened.push(DEFINITIONS.placebo);
  const rest = trials.length - naming.length;
  if (rest > 0) {
    opened.push(
      rest === 1
        ? "The other record names no such comparison."
        : `The other ${word(rest)} records name no such comparison.`,
    );
  }
  return row({
    code: "comparison",
    question,
    answer:
      naming.length === 1
        ? `One record names ${dummy.noun}`
        : `${capital(word(naming.length))} records name ${dummy.plural}`,
    opened,
    source: directFrom(naming),
  });
}

function firstReportRow(claim: ExportedClaim): BriefRow | null {
  const stage = claim.evidence_stage ? FIRST_REPORT[claim.evidence_stage] : undefined;
  if (!stage) return null;
  return row({
    code: "first_report",
    question: QUESTIONS.first_report,
    answer: stage.answer,
    opened: [stage.opened],
    source: {
      how: "direct",
      from: "this claim's record of its first report",
      records: [],
      on: claim.first_reported_date,
      onLabel: "Record read",
      confidence: null,
    },
  });
}

const usable = (reading: ExportedReading | undefined): reading is ExportedReading =>
  Boolean(reading && reading.confidence >= READING_SHOWN_FROM);

function measureRow(trials: ExportedTrial[]): BriefRow | null {
  const trial = largestTrial(trials);
  const outcome = trial?.facts?.primary_outcomes[0];
  if (!trial || !outcome) return null;
  const about = (trial.readings ?? []).filter((reading) => reading.outcome === 0);
  const measure = about.find((reading) => reading.kind === "measure");
  const followUp = about.find((reading) => reading.kind === "follow_up");
  const phrase = usable(measure) && measure.code ? MEASURE_PHRASES[measure.code] : undefined;
  const link = {
    href: `#trial-${trial.trial_id}`,
    text: trial.facts?.results ? "See this trial's posted results" : "See this trial",
  };
  const record = [{ label: trial.trial_id, url: trial.url }];
  if (!phrase) {
    return row({
      code: "measure",
      question: QUESTIONS.measure,
      answer: `“${outcome.measure}”`,
      opened: [DEFINITIONS.registry_words],
      link,
      source: { how: "direct", from: null, records: record, on: trial.facts_as_of, onLabel: "Record read", confidence: null },
    });
  }
  // Whether the measure is a change is read by rule from the registry's title.
  const isChange = /\bchange\b/i.test(outcome.measure);
  const timed = usable(followUp) && followUp.number !== null && followUp.unit !== null;
  const over = timed
    ? ` over ${digits(followUp.number!)} ${followUp.number === 1 ? followUp.unit!.slice(0, -1) : followUp.unit}`
    : "";
  const timing = timed && outcome.time_frame ? ` and gives its timing as “${outcome.time_frame}”` : "";
  return row({
    code: "measure",
    question: QUESTIONS.measure,
    answer: `${isChange ? phrase.change : phrase.plain}${over}`,
    opened: [`The registry names the measure “${outcome.measure}”${timing}.`],
    link,
    source: {
      how: "model",
      from: null,
      records: record,
      on: trial.facts_as_of,
      onLabel: "Record read",
      confidence: timed ? Math.min(measure!.confidence, followUp.confidence) : measure!.confidence,
    },
  });
}

const eventsOf = (claim: ExportedClaim, trials: ExportedTrial[], type: string): ExportedEvent[] => {
  const ids = new Set(trials.map((trial) => trial.trial_id));
  return claim.events.filter((event) => event.type === type && event.trial_id !== null && ids.has(event.trial_id));
};

function resultsRow(claim: ExportedClaim, trials: ExportedTrial[]): BriefRow {
  const posted = trials.filter((trial) => trial.facts?.results);
  if (posted.length === 0) {
    return row({
      code: "results",
      question: QUESTIONS.results,
      answer: NONE,
      opened: [DEFINITIONS.posted],
      source: directFrom(trials),
    });
  }
  const on = latest(eventsOf(claim, posted, "trial_results_posted").map((event) => event.event_date));
  const by =
    trials.length === 1
      ? "By the one trial on record"
      : posted.length === trials.length
        ? `By all ${digits(trials.length)} trials`
        : `By ${digits(posted.length)} of ${digits(trials.length)} trials`;
  return row({
    code: "results",
    question: QUESTIONS.results,
    answer: on ? `${by}. ${posted.length === 1 ? "Posted" : "The latest"} on ${day(on)}` : by,
    opened: [DEFINITIONS.posted],
    shown: { href: "#trials", text: "See the posted results" },
    source: directFrom(posted),
  });
}

function underWayRow(claim: ExportedClaim, trials: ExportedTrial[]): BriefRow {
  const underWay = trials.filter((trial) => trial.state === "under_way");
  if (underWay.length > 0) {
    return row({
      code: "under_way",
      question: QUESTIONS.under_way,
      answer: `${capital(word(underWay.length))} under way`,
      opened: [DEFINITIONS.under_way],
      source: directFrom(underWay),
    });
  }
  const finished = latest(
    eventsOf(claim, trials, "trial_status_change")
      .filter((event) => event.trial_state === "completed")
      .map((event) => event.event_date),
  );
  return row({
    code: "under_way",
    question: QUESTIONS.under_way,
    answer: finished ? `${NONE}. The last finished on ${day(finished)}` : NONE,
    opened: [DEFINITIONS.under_way],
    source: directFrom(trials),
  });
}

function approvedRow(claim: ExportedClaim, lastChecked: string | null): BriefRow {
  const approvals = claim.events
    .filter((event) => event.type === "regulatory_decision" && event.regulatory_outcome === "approved")
    .sort((a, b) => (a.event_date < b.event_date ? -1 : 1));
  const approval = approvals[0];
  if (!approval) {
    return row({
      code: "approved",
      question: QUESTIONS.approved,
      answer: NONE,
      opened: [DEFINITIONS.regulator, DEFINITIONS.no_approval],
      source: checked(lastChecked),
    });
  }
  // The regulator is named when the record's source is one; a record entered by hand
  // names no source, and the answer then gives the date alone.
  const regulator = approval.source_name === "manual entry" ? null : sourceName(approval.source_name);
  const by = regulator ? `By the ${regulator} on` : "On";
  return row({
    code: "approved",
    question: QUESTIONS.approved,
    answer: `${by} ${day(approval.event_date)}. ${DEFINITIONS.approval}`,
    opened: [DEFINITIONS.regulator, DEFINITIONS.approval_scope],
    source: {
      how: "direct",
      from: null,
      records: [{ label: regulator ? `the ${regulator}'s record` : "the record of the approval", url: approval.source_url }],
      on: null,
      onLabel: "Record read",
      confidence: null,
    },
  });
}

/** The section's rows, in their fixed places. A group with no row is left out. */
export function recordBrief(claim: ExportedClaim, lastChecked: string | null): BriefGroup[] {
  const trials = claim.trials ?? [];
  const tested = [
    testedRow(trials, lastChecked),
    trials.length > 0 ? comparisonRow(claim, trials) : firstReportRow(claim),
    measureRow(trials),
  ];
  const now = [
    trials.length > 0 ? resultsRow(claim, trials) : null,
    trials.length > 0 ? underWayRow(claim, trials) : null,
    approvedRow(claim, lastChecked),
  ];
  const groups: BriefGroup[] = [
    { code: "tested", name: GROUP_NAMES.tested, rows: tested.filter((entry): entry is BriefRow => entry !== null) },
    { code: "now", name: GROUP_NAMES.now, rows: now.filter((entry): entry is BriefRow => entry !== null) },
  ];
  return groups.filter((group) => group.rows.length > 0);
}

/** "Six answers read from the records on this page. …" */
export function briefNote(groups: BriefGroup[]): string {
  const answers = groups.reduce((total, group) => total + group.rows.length, 0);
  return `${capital(word(answers))} ${plural(answers, "answer", "answers")} read from the records on this page. Open one to see the record it came from. They describe the records, not the treatment, and are not advice.`;
}

/** How an opened answer says where it came from, as the words around its record links. */
export function sourceWords(source: BriefSource): { before: string; after: string } {
  const on = source.on ? ` ${source.onLabel} ${day(source.on)}.` : "";
  if (source.how === "model") {
    return {
      before: "A model read the plain wording from the quoted words, and a rule checked that they are in ",
      after: `. How sure the reading is: ${readingConfidenceLabel(source.confidence ?? 0)}.${on}`,
    };
  }
  return { before: `Read directly from ${source.from ?? ""}`, after: `.${on}` };
}

/** For a claim whose status is Trial registered and which has trials on record: how many,
 * how many have finished, and that the registry gives none a phase. Openspec
 * site-publishing: "The digest says when trials state no phase". */
export function digestBridge(claim: ExportedClaim): string | null {
  const trials = claim.trials ?? [];
  if (claim.status.code !== "trial_registered" || trials.length === 0) return null;
  const finished = trials.filter((trial) => trial.state === "completed").length;
  const are = trials.length === 1 ? "1 trial is on record" : `${digits(trials.length)} trials are on record`;
  const done =
    finished === 0
      ? ""
      : trials.length === 1
        ? " and it has finished"
        : finished === trials.length
          ? " and all have finished"
          : ` and ${digits(finished)} ${plural(finished, "has", "have")} finished`;
  // The registry marks a trial with no phase as "not applicable"; an older record states nothing.
  const unphased = (trial: ExportedTrial) => trial.phases.every((code) => code === "not_applicable");
  const phase = trials.every(unphased) ? " The registry gives none a phase." : "";
  return `${are}${done}.${phase}`;
}

// A build fails rather than publish a verdict in a question, an answer or a group name.
assertNeutral([
  BRIEF_TITLE,
  NONE,
  ...Object.values(GROUP_NAMES),
  ...Object.values(QUESTIONS),
  ...Object.values(DEFINITIONS),
  ...Object.values(FIRST_REPORT).flatMap((stage) => [stage.answer, stage.opened]),
  ...Object.values(MEASURE_PHRASES).flatMap((phrase) => [phrase.plain, phrase.change]),
  ...Object.values(DUMMY).flatMap((dummy) => [dummy.noun, dummy.plural]),
  ...Object.values(COMPARATOR_WORDS),
]);
