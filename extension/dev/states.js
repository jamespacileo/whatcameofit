// Draws every popup state in its own frame, using the real stylesheet and view code.
import { SITE } from "./config.js";
import { render } from "./view.js";

const notices = [
  "This site gives no medical advice and recommends no treatment.",
  "A registered clinical trial is not a treatment option. Talk to a clinician about your own care.",
];
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
    "Automatic search. This list was made by software just now from a public registry. It has not been checked by a person and is not a status.",
  lead: "This appears to report divalent small interfering RNA for Prion disease.",
  source: "Read by your browser from the post on X you have open, and the article it links to at example.org.",
  searchedAlso: null,
  trialSaid: "Of the trial itself, the article says: it is called PRiSM and 30 people took part.",
  tracked: [],
  likelyLead: "Registry records that read as trials of this treatment for this condition, likeliest first:",
  confidenceMeaning: "Confidence estimates how closely each registry record matches this report.",
  likely: [
    {
      title: "PrP-targeting siRNA Safety & Mechanism Study",
      url: "https://clinicaltrials.gov/study/NCT07444580",
      detail: "Phase 1 · recruiting · NCT07444580",
      why: "The article gives this record's number.",
      confidence: 97,
      confidenceLabel: "97% match confidence",
    },
    {
      title: "A Study to Assess the Safety, Tolerability, Pharmacokinetics and Pharmacodynamics of ION717",
      url: "https://clinicaltrials.gov/study/NCT06153966",
      detail: "Phase 1/Phase 2 · active, not recruiting · NCT06153966",
      why: null,
      confidence: 72,
      confidenceLabel: "72% match confidence",
    },
  ],
  rest: "3 other records were found and read as not being trials of this treatment for this condition.",
  none: null,
  notices: [notices[1], "Source of the records: ClinicalTrials.gov."],
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
  ["Tracked, with a promise", tracked([claim])],
  ["Tracked, no signal, no promise", tracked([quiet])],
  ["Longest wording", tracked([long])],
  ["Two claims in one article", tracked([claim, quiet])],
  ["Tracked, from the saved copy", tracked([claim], Date.UTC(2026, 10, 10, 9))],
  ["Not a tracked report", { kind: "untracked", savedAt: null }],
  ["Searching", { kind: "searching" }],
  ["Answer from a post", { kind: "answer", shown: answer }],
  ["Too little read", { kind: "too-little" }],
  ["Search refused", { kind: "refused", code: "busy" }],
  ["Monthly allowance used", { kind: "refused", code: "budget_exhausted" }],
  ["Page changed", { kind: "refused", code: "page_changed" }],
  ["Not a web page", { kind: "no-page" }],
  ["Site unreachable", { kind: "unreachable" }],
  ["Checking", { kind: "checking" }],
];

const board = document.querySelector("#board");
const actions = {
  open: (address) => console.log("open", address),
  retry: () => console.log("retry"),
  search: () => console.log("search"),
};

for (const [label, state] of states) {
  const figure = document.createElement("figure");
  const caption = document.createElement("figcaption");
  caption.textContent = label;
  const frame = document.createElement("iframe");
  frame.title = label;
  frame.scrolling = "no";
  frame.srcdoc = `<!doctype html><html lang="en"><head><base href="${location.href}"><link rel="stylesheet" href="popup.css"></head><body><header class="masthead"><img class="mark" src="icons/32.png" width="20" height="20" alt=""><span class="name">${SITE.name}</span></header><main id="view"></main></body></html>`;
  frame.addEventListener("load", () => {
    // Nodes are made with this page's document and adopted by the frame when inserted,
    // so the frame's own stylesheet applies to them.
    render(frame.contentDocument.querySelector("#view"), state, SITE, actions);
    const fit = () => {
      frame.style.height = `${frame.contentDocument.body.scrollHeight}px`;
    };
    fit();
    frame.contentDocument.fonts.ready.then(fit);
  });
  figure.append(caption, frame);
  board.append(figure);
}

