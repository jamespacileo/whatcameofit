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
  meaning: "The furthest trial that has started is a Phase 1 trial.",
  no_signal: null,
  first_reported: "31 Mar 2021",
  latest_promise: "Tooth regrowth medicine ready for general use (by 2030)",
};
const quiet = {
  headline: "Tideglusib on a collagen sponge regrows dentine in mouse teeth",
  page: "/dentine-repair-tideglusib",
  status: "Preclinical only",
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
  meaning:
    "A trial result was reported in which the primary endpoint was not met, and no other trial stands.",
  no_signal: null,
  first_reported: "22 Oct 2026",
  latest_promise: null,
};
const tracked = (claims, savedAt = null) => ({
  kind: "tracked",
  claims,
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
  ["Not a web page", { kind: "no-page" }],
  ["Site unreachable", { kind: "unreachable" }],
  ["Checking", { kind: "checking" }],
];

const board = document.querySelector("#board");
const actions = { open: (address) => console.log("open", address), retry: () => console.log("retry") };

for (const [label, state] of states) {
  const figure = document.createElement("figure");
  const caption = document.createElement("figcaption");
  caption.textContent = label;
  const frame = document.createElement("iframe");
  frame.title = label;
  frame.scrolling = "no";
  frame.srcdoc = `<!doctype html><html lang="en"><head><base href="${location.href}"><link rel="stylesheet" href="popup.css"></head><body><header class="masthead"><span class="name">${SITE.name}</span></header><main id="view"></main></body></html>`;
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

