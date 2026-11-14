// Draws every popup state in its own frame, using the real stylesheet and view code.
import { SITE } from "./config.js";
import { render } from "./view.js";
import { LIVE } from "./live-lookup.js";
import { NOTICES } from "./notices.js";

const notices = [...NOTICES];
const claim = {
  headline: "Antibody against USAG-1 regrows teeth in mice",
  page: "/tooth-regrowth-usag1",
  status: "Phase 1 trial",
  place: 3,
  meaning: "The furthest trial that has started is a Phase 1 trial.",
  no_signal: null,
  first_reported: "31 Mar 2021",
  latest_promise: "Tooth regrowth medicine ready for general use (by 2030)",
};
const quiet = {
  headline: "Tideglusib on a collagen sponge regrows dentine in mouse teeth",
  page: "/dentine-repair-tideglusib",
  status: "Preclinical only",
  place: 1,
  meaning:
    "No clinical trial was found in the registries checked. The first reports are not recorded as describing a study in people.",
  no_signal: "No signal for 9 years",
  first_reported: "9 Jan 2017",
  latest_promise: null,
};
const long = {
  headline:
    "A personalised mRNA vaccine given with pembrolizumab was reported to cut the risk of melanoma returning or causing death by 42% in a Phase 3 trial",
  page: "/melanoma-mrna-vaccine-intismeran",
  status: "Trial missed its primary endpoint",
  place: null,
  meaning:
    "A trial result was reported in which the primary endpoint was not met, and no other trial stands.",
  no_signal: null,
  first_reported: "22 Oct 2026",
  latest_promise: null,
};
// A registry search's answer, as the site's own wording module returns it.
const answer = {
  marked:
    LIVE.marked,
  lead: "This appears to report divalent small interfering RNA for Prion disease.",
  subject: { treatment: "Divalent small interfering RNA", condition: "Prion disease" },
  source: "Read by your browser from the post on X you have open, and the article it links to at example.org.",
  searchedAlso: null,
  trialSaid: "Of the trial itself, the article says: it is called PRiSM and 30 people took part.",
  tracked: [],
  likelyLead: LIVE.likelyLead,
  confidenceMeaning: LIVE.confidenceMeaning,
  likely: [
    {
      title: "PrP-targeting siRNA Safety & Mechanism Study",
      url: "https://clinicaltrials.gov/study/NCT07444580",
      detail: "Phase 1 · recruiting · NCT07444580",
      phase: "Phase 1", state: "recruiting", registryId: "NCT07444580",
      why: "The article gives this record's number.",
      confidence: 97,
      confidenceLabel: "97% match confidence",
    },
    {
      title: "A Study to Assess the Safety, Tolerability, Pharmacokinetics and Pharmacodynamics of ION717",
      url: "https://clinicaltrials.gov/study/NCT06153966",
      detail: "Phase 1/Phase 2 · active, not recruiting · NCT06153966",
      phase: "Phase 1/Phase 2", state: "active, not recruiting", registryId: "NCT06153966",
      why: null,
      confidence: 72,
      confidenceLabel: "72% match confidence",
    },
  ],
  rest: "3 other records were found and read as not being trials of this treatment for this condition.",
  none: null,
  notices: [notices[1], LIVE.source],
};
const tracked = (claims, savedAt = null) => ({
  kind: "tracked",
  claims,
  places: 6,
  notices,
  lastChecked: "11 Nov 2026",
  savedAt,
});

const states = [
  ["First use", { kind: "sharing", enabled: false }],
  ["Automatic search settings", { kind: "sharing", enabled: true }],
  ["Tracked, with a promise", tracked([claim])],
  ["Tracked, no signal, no promise", tracked([quiet])],
  ["Longest wording", tracked([long])],
  ["Two claims in one article", tracked([claim, quiet])],
  ["Tracked, from the saved copy", tracked([claim], Date.UTC(2026, 10, 10, 9))],
  ["Not a tracked report", { kind: "untracked", savedAt: null }],
  ["Capturing visible media", { kind: "capturing" }],
  ["Reading image", { kind: "searching", visual: true }],
  ["Earlier check", { kind: "answer", shown: { ...answer, marked: "Automatic search from an earlier check. Not checked by a person and not a status." }, cachedAt: Date.UTC(2026, 10, 13, 9), canVisual: true }],
  ["Screenshot unavailable", { kind: "refused", code: "capture_unavailable" }],
  ["Sensitive content", { kind: "refused", code: "capture_sensitive" }],
  ["Searching", { kind: "searching" }],
  ["Answer from a post", { kind: "answer", shown: answer }],
  ["Image post, long candidate", { kind: "answer", canVisual: true, shown: { ...answer,
    subject: { treatment: "Tooth-regenerating patch", condition: "Dental caries (cavities)" },
    source: "Read from the visible screenshot and caption. This identifies what the post claims; it does not establish that the claim is true.",
    trialSaid: null, rest: null,
    likely: [{ ...answer.likely[0], title: "A Study to Evaluate Physiologic Dentin Regeneration and Safety of EX-1 in the Treatment of Dental Caries", confidence: 62, confidenceLabel: "62% match confidence", why: null }],
  } }],
  ["No matching record", { kind: "answer", shown: { ...answer, likely: [], rest: null, none: "No matching trial record was found in ClinicalTrials.gov. That is not evidence that no trial exists: it may use another name or registry." } }],
  ["Not identifiable", { kind: "answer", shown: { ...answer, subject: null, lead: "A specific treatment and condition could not be identified from the content that could be read. The registry was not searched; nothing has been ruled out.", likely: [], trialSaid: null, rest: null } }],
  ["Too little read", { kind: "too-little" }],
  ["Search refused", { kind: "refused", code: "busy" }],
  ["Monthly allowance used", { kind: "refused", code: "budget_exhausted" }],
  ["Page changed", { kind: "refused", code: "page_changed" }],
  ["Not a web page", { kind: "no-page" }],
  ["Site unreachable", { kind: "unreachable" }],
  ["Checking", { kind: "checking" }],
  // The reader's own lists. The third item is what those lists hold.
  ["Tracked, lists offered", tracked([claim]), { recent: 3, following: 1, changed: 1, followed: [], was: {} }],
  [
    "Tracked, followed and changed",
    tracked([claim]),
    { recent: 3, following: 1, changed: 0, followed: [claim.page], was: { [claim.page]: "Trial registered" }, reminders: { [claim.page]: "2027-05-13" } },
  ],
  // The moment after "Keep me up to date" is pressed: the tick is drawn.
  [
    "Tracked, just followed",
    tracked([claim]),
    { recent: 3, following: 1, changed: 0, followed: [claim.page], was: {}, fresh: claim.page },
  ],
  [
    "Recently checked",
    {
      kind: "recent",
      entries: [
        {
          key: "news.example.org/teeth",
          url: "https://news.example.org/teeth",
          title: "New drug to regenerate lost teeth",
          outlet: "news.example.org",
          at: Date.UTC(2026, 10, 13, 9),
          answer: { kind: "tracked" },
          candidates: [{ title: claim.headline, url: SITE.url + claim.page, status: claim.status }],
        },
        {
          key: "x.com/example/status/1",
          url: "https://x.com/example/status/1",
          title: "A post about a prion disease treatment entering trials",
          outlet: "x.com",
          at: Date.UTC(2026, 10, 12, 9),
          answer: { kind: "searched", unreviewed: "Automatic search. Not checked by a person and not a status." },
          candidates: answer.likely.map(({ title, url }) => ({ title, url, status: null })),
        },
        {
          key: "daily.example.com/miracle",
          url: "https://daily.example.com/miracle",
          title: "Scientists hail breakthrough that could end hair loss",
          outlet: "daily.example.com",
          at: Date.UTC(2026, 10, 11, 9),
          answer: { kind: "none" },
          candidates: [],
        },
      ],
    },
  ],
  ["Recently checked, registry not searched", { kind: "recent", entries: [{
    key: "news.example.org/image-post", url: "https://news.example.org/image-post",
    title: "An image post without enough readable detail", outlet: "news.example.org", at: Date.UTC(2026, 10, 13),
    answer: { kind: "searched", limitation: LIVE.notATreatment }, candidates: [],
  }] }],
  ["Recently checked, empty", { kind: "recent", entries: [] }],
  [
    "One check's candidates",
    {
      kind: "entry",
      entry: {
        key: "x.com/example/status/1",
        url: "https://x.com/example/status/1",
        title: "A post about a prion disease treatment entering trials",
        outlet: "x.com",
        at: Date.UTC(2026, 10, 12, 9),
        answer: { kind: "searched", unreviewed: "Automatic search. Not checked by a person and not a status." },
        candidates: answer.likely.map(({ title, url }) => ({ title, url, status: null })),
      },
    },
  ],
  [
    "Following",
    {
      kind: "following",
      claims: [
        { ...claim, gone: false, changed: true, was: "Trial registered" },
        { ...quiet, gone: false, changed: false, was: null },
        { headline: long.headline, page: long.page, status: long.status, gone: true, changed: false, was: null },
      ],
    },
  ],
  ["Following, empty", { kind: "following", claims: [] }],
];

const board = document.querySelector("#board");
const log = (name) => (...args) => console.log(name, ...args);
const actions = {
  open: log("open"),
  retry: log("retry"),
  search: log("search"),
  enableSharing: log("enableSharing"),
  disableSharing: log("disableSharing"),
  sharingView: log("sharingView"),
  previewVisual: log("previewVisual"),
  sendVisual: log("sendVisual"),
  cancelVisual: log("cancelVisual"),
  showRecent: log("showRecent"),
  showEntry: log("showEntry"),
  clearRecent: log("clearRecent"),
  showFollowing: log("showFollowing"),
  back: log("back"),
  follow: log("follow"),
  unfollow: log("unfollow"),
  remindLater: log("remindLater"),
  forget: log("forget"),
  openFollowed: log("openFollowed"),
};

for (const [label, state, kept = null] of states) {
  const figure = document.createElement("figure");
  const caption = document.createElement("figcaption");
  caption.textContent = label;
  const frame = document.createElement("iframe");
  frame.title = label;
  frame.scrolling = "no";
  frame.srcdoc = `<!doctype html><html lang="en"><head><base href="${location.href}"><link rel="stylesheet" href="popup.css"></head><body><header class="masthead"><img class="mark" src="icons/mark-reverse.svg" width="20" height="20" alt=""><span class="name">${SITE.name}</span></header><main id="view"></main></body></html>`;
  frame.addEventListener("load", () => {
    // Nodes are made with this page's document and adopted by the frame when inserted,
    // so the frame's own stylesheet applies to them.
    render(frame.contentDocument.querySelector("#view"), state, SITE, actions, kept);
    const fit = () => {
      frame.style.height = `${frame.contentDocument.body.scrollHeight}px`;
    };
    fit();
    frame.contentDocument.fonts.ready.then(fit);
    frame.contentDocument.addEventListener("toggle", fit, true);
  });
  figure.append(caption, frame);
  board.append(figure);
}

