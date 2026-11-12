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
  postOffer: "Search the trial registry for this post",
  postDisclosure:
    "This sends the address to this site's server, which reads the post and the article it links to, and asks a language model what they report. The site keeps none of it.",
  postTracked: "This post links to an article we track. Its page has been through our usual checks:",
  textLabel: "Or paste the headline and opening paragraphs",
  textOffer: "Search the trial registry for this text",
  working: "Reading the article and searching the registry. This can take half a minute.",
  marked:
    "Automatic search. This list was made by software just now from a public registry. It has not been checked by a person and is not a status.",
  notATreatment: "This does not appear to report a specific treatment for a specific condition, so the registry was not searched.",
  trackedLead: "We track this treatment. Its page has been through our usual checks:",
  likelyLead: "Registry records that read as trials of this treatment for this condition, likeliest first:",
  trialSaid: "Of the trial itself, the article says:",
  none: "No matching trial record was found in ClinicalTrials.gov. That is not evidence that no trial exists: the registry may list the treatment under another name, or the trial may be registered elsewhere.",
  source: "Source of the records: ClinicalTrials.gov.",
};

// Where the text came from when the reader gave a post's address.
function sourceOf(post) {
  if (!post) return null;
  // A post the reader had open was read by their own browser, not by this site.
  const from = post.read_in_browser
    ? `Read by your browser from the post on ${post.platform} you have open`
    : `Read from a post on ${post.platform}`;
  if (post.article_read) return `${from} and the article it links to at ${post.article_host}.`;
  if (post.article) return `${from}. The article it links to at ${post.article_host} could not be read, so only the post was used.`;
  if (post.only_short_links) return `${from}. It links through a shortened address that this site may not follow, so only the post was used.`;
  return `${from}. No article was found among its links, so only the post was used.`;
}

const PASTE_INSTEAD = "Paste its text below, or put the address of the article it links to in the box above.";

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

// Why a record is listed where it is. Each is a fact a reader can check on the record.
const POINTED_TO = [
  ["stated", "The article gives this record's number."],
  ["paper", "A paper the article links to gives this record's number."],
];
const AGREES_ON = [
  ["trial_name", "the trial's name"],
  ["participants", "the number of participants"],
  ["sponsor", "who ran it"],
];

function joined(parts) {
  return parts.length < 3 ? parts.join(" and ") : `${parts.slice(0, -1).join(", ")} and ${parts.at(-1)}`;
}

/** Why a record is listed where it is, or null when only its score put it there. */
function whyListed(agrees) {
  const worded = (table) => table.filter(([code]) => agrees.includes(code)).map(([, words]) => words);
  const details = worded(AGREES_ON);
  const sentences = [
    ...worded(POINTED_TO),
    ...(details.length ? [`Its registration agrees with the article on ${joined(details)}.`] : []),
  ];
  return sentences.length ? sentences.join(" ") : null;
}

/** What the article says of its own trial, as the model read it, or null. */
function trialSaid(details) {
  const said = [
    details?.trial_name ? `it is called ${details.trial_name}` : null,
    details?.participants ? `${details.participants.toLocaleString("en-GB")} people took part` : null,
    details?.sponsor ? `${details.sponsor} ran or paid for it` : null,
  ].filter(Boolean);
  return said.length ? `${LIVE.trialSaid} ${joined(said)}.` : null;
}

/**
 * What to tell a reader when the service will not or cannot answer.
 * @param {{ platform?: string }} about what the service said of the refusal, beyond its code
 */
export function refusalMessage(code, about = {}) {
  if (code === "post" && about.platform) {
    return `This site cannot read posts on ${about.platform}. ${PASTE_INSTEAD}`;
  }
  if (code === "post_unreadable") {
    return `That post${about.platform ? ` on ${about.platform}` : ""} could not be read. It may be private or deleted. ${PASTE_INSTEAD}`;
  }
  return REFUSALS[code] ?? REFUSALS.failed;
}

/** Whether pasting the text is the way forward after this refusal. */
export function textWouldHelp(code) {
  return ["unreadable_robots", "unreadable", "post", "post_unreadable"].includes(code);
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
 * @returns {{ marked: string | null, lead: string, source: string | null, searchedAlso: string | null, trialSaid: string | null,
 *   tracked: { slug: string, headline: string, page: string }[],
 *   likely: { title: string, url: string, detail: string, why: string | null }[],
 *   rest: string | null, none: string | null, notices: string[] }}
 */
export function describeAnswer(answer) {
  const notices = [NOTICES[1], LIVE.source];
  const source = sourceOf(answer.post);
  const nothing = { searchedAlso: null, trialSaid: null, tracked: [], likely: [], rest: null, none: null };
  // A post that links to an article the site tracks: its reviewed page is the answer,
  // and no automatic search was made, so nothing is marked as one.
  if (answer.article_tracked) {
    return { ...nothing, marked: null, lead: LIVE.postTracked, source, tracked: answer.tracked ?? [], notices: [] };
  }
  if (!answer.about_a_treatment || !answer.treatment) {
    return { ...nothing, marked: LIVE.marked, lead: LIVE.notATreatment, source, notices };
  }
  const candidates = answer.candidates ?? [];
  // A record the article itself gives the number of is listed whatever its score.
  const likely = candidates.filter(
    (candidate) => candidate.score >= LIKELY_FROM || (candidate.agrees ?? []).includes("stated"),
  );
  const others = candidates.length - likely.length;
  const known = answer.known_names ?? [];
  return {
    marked: LIVE.marked,
    lead: `This appears to report ${answer.treatment}${answer.condition ? ` for ${answer.condition}` : ""}.`,
    source,
    searchedAlso: known.length
      ? `Also searched under ${known.length === 1 ? "a name" : "names"} the article does not give: ${known.join(", ")}.`
      : null,
    trialSaid: trialSaid(answer.details),
    tracked: answer.tracked ?? [],
    likely: likely.slice(0, SHOWN_AT_MOST).map((candidate) => ({
      title: candidate.title || candidate.id,
      url: candidate.url,
      detail: [phaseLabel(candidate.phases), stateLabel(candidate.state), candidate.id].filter(Boolean).join(" · "),
      why: whyListed(candidate.agrees ?? []),
    })),
    rest:
      others > 0
        ? `${others} other ${others === 1 ? "record was" : "records were"} found and read as not being trials of this treatment for this condition.`
        : null,
    none: likely.length === 0 ? LIVE.none : null,
    notices,
  };
}
