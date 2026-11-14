// Whether a registry record agrees with what an article says about the trial it reports.
// A treatment often has dozens of trials; the article is about one, and gives it away by
// its name, its size or who ran it. Compared by rule: no model is asked. The same rules
// as the pipeline's thenwhat.lookup.details; keep the two in step.

// Why a record is ranked where it is, as codes, in the order they are listed.
export const STATED = "stated"; // the text or the page gives this record's registry number
export const PAPER = "paper"; // a paper the page links to gives it
const TRIAL_NAME = "trial_name";
const PARTICIPANTS = "participants";
const SPONSOR = "sponsor";

// How far a reported number of participants may be from the registered one: articles
// round, and report the people analysed rather than the people enrolled.
const PARTICIPANTS_WITHIN = 0.1;
// Words that say what kind of body a sponsor is, not which one.
const SPONSOR_FILLER = new Set("of the and at inc ltd plc llc co company corporation corp".split(" "));

const words = (text) => (text ? String(text).toLowerCase().match(/[a-z0-9]+/g) ?? [] : []);

/** Whether the wanted words appear in order, next to each other. */
function within(wanted, given) {
  for (let start = 0; start + wanted.length <= given.length; start += 1) {
    if (wanted.every((word, at) => given[start + at] === word)) return true;
  }
  return false;
}

/**
 * The details this registry record agrees with, as codes.
 * @param {{ trial_name?: string | null, participants?: number | null, sponsor?: string | null }} details
 */
export function agreeing(study, details) {
  const section = study?.protocolSection ?? {};
  const identification = section.identificationModule ?? {};
  const reasons = [];

  const name = words(details.trial_name);
  if (name.join("").length >= 3) {
    const carried = [identification.acronym, identification.briefTitle, identification.officialTitle].map(words);
    if (carried.some((given) => within(name, given))) reasons.push(TRIAL_NAME);
  }

  const enrolled = section.designModule?.enrollmentInfo?.count;
  const reported = details.participants;
  if (
    Number.isInteger(enrolled) &&
    reported &&
    enrolled > 0 &&
    Math.abs(enrolled - reported) <= PARTICIPANTS_WITHIN * Math.max(enrolled, reported)
  ) {
    reasons.push(PARTICIPANTS);
  }

  const sponsors = section.sponsorCollaboratorsModule ?? {};
  const registered = [sponsors.leadSponsor?.name, ...(sponsors.collaborators ?? []).map((one) => one.name)];
  const wanted = words(details.sponsor).filter((word) => !SPONSOR_FILLER.has(word));
  if (wanted.length && registered.some((one) => wanted.every((word) => words(one).includes(word)))) {
    reasons.push(SPONSOR);
  }
  return reasons;
}
