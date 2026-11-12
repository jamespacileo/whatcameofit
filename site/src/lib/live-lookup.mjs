// The words a live lookup answer is shown in. The lookup service returns codes and
// registry fields; everything a reader reads is written here. Plain JavaScript, pure:
// the page builds its elements from what these functions return.
//
// A live answer is an automatic search, never a status. It says so first, every time.
import { NOTICES } from "./notices.ts";

// A record scored at or above this is listed; the rest are counted.
const LIKELY_FROM = 0.5;
const SHOWN_AT_MOST = 10;

export const LIVE = {
  offer: "Search the trial registry for this article",
  disclosure:
    "This sends the address to this site's server, which reads the article and asks a language model what it reports. The site keeps neither the address nor the article.",
  textLabel: "Or paste the headline and opening paragraphs",
  textOffer: "Search the trial registry for this text",
  working: "Reading the article and searching the registry. This can take half a minute.",
  marked:
    "Automatic search. This list was made by software just now from a public registry. It has not been checked by a person and is not a status.",
  notATreatment: "This does not appear to report a specific treatment for a specific condition, so the registry was not searched.",
  trackedLead: "We track this treatment. Its page has been through our usual checks:",
  likelyLead: "Registry records that read as trials of this treatment for this condition, likeliest first:",
  none: "No matching trial record was found in ClinicalTrials.gov. That is not evidence that no trial exists: the registry may list the treatment under another name, or the trial may be registered elsewhere.",
  source: "Source of the records: ClinicalTrials.gov.",
};

const REFUSALS = {
  unreadable_robots:
    "That site does not allow software to read its articles, so this one was not read. Paste its headline and opening paragraphs below instead.",
  unreadable: "The article could not be opened. It may be behind a paywall. Paste its headline and opening paragraphs below instead.",
  post: "That is a post, not the article itself. Paste the post's text below, or the address of the article it links to above.",
  short: "That is a shortened link. Open it, then paste the address of the article it leads to.",
  address: "That does not look like the address of an article.",
  too_long: "That is too much text. Paste the headline and the first few paragraphs only.",
  busy: "Too many searches are being made right now. Try again in a minute.",
  not_set_up: "The registry search is not available on this site at the moment.",
  failed: "The search could not be completed. Nothing was found or ruled out. Try again in a minute.",
};

/** What to tell a reader when the service will not or cannot answer. */
export function refusalMessage(code) {
  return REFUSALS[code] ?? REFUSALS.failed;
}

/** Whether pasting the text is the way forward after this refusal. */
export function textWouldHelp(code) {
  return ["unreadable_robots", "unreadable", "post"].includes(code);
}

function phaseLabel(phases) {
  const words = (phases ?? []).map((phase) =>
    phase === "NA" ? "No phase" : phase.replace(/^EARLY_PHASE(\d)$/, "Early Phase $1").replace(/^PHASE(\d)$/, "Phase $1"),
  );
  return words.join("/");
}

function stateLabel(state) {
  if (!state) return "";
  const words = state.toLowerCase().split("_");
  // The registry's own state names: "active, not recruiting", "not yet recruiting".
  return words[0] === "active" && words.length > 1 ? `active, ${words.slice(1).join(" ")}` : words.join(" ");
}

/**
 * A lookup answer in the site's words.
 * @returns {{ marked: string, lead: string, searchedAlso: string | null,
 *   tracked: { slug: string, headline: string, page: string }[],
 *   likely: { title: string, url: string, detail: string }[],
 *   rest: string | null, none: string | null, notices: string[] }}
 */
export function describeAnswer(answer) {
  const notices = [NOTICES[1], LIVE.source];
  if (!answer.about_a_treatment || !answer.treatment) {
    return { marked: LIVE.marked, lead: LIVE.notATreatment, searchedAlso: null, tracked: [], likely: [], rest: null, none: null, notices };
  }
  const candidates = answer.candidates ?? [];
  const likely = candidates.filter((candidate) => candidate.score >= LIKELY_FROM);
  const others = candidates.length - likely.length;
  const known = answer.known_names ?? [];
  return {
    marked: LIVE.marked,
    lead: `This appears to report ${answer.treatment}${answer.condition ? ` for ${answer.condition}` : ""}.`,
    searchedAlso: known.length
      ? `Also searched under ${known.length === 1 ? "a name" : "names"} the article does not give: ${known.join(", ")}.`
      : null,
    tracked: answer.tracked ?? [],
    likely: likely.slice(0, SHOWN_AT_MOST).map((candidate) => ({
      title: candidate.title || candidate.id,
      url: candidate.url,
      detail: [phaseLabel(candidate.phases), stateLabel(candidate.state), candidate.id].filter(Boolean).join(" · "),
    })),
    rest:
      others > 0
        ? `${others} other ${others === 1 ? "record was" : "records were"} found and read as not being trials of this treatment for this condition.`
        : null,
    none: likely.length === 0 ? LIVE.none : null,
    notices,
  };
}
