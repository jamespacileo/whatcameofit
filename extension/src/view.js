// Draws one popup state. Status wording comes from the lookup file, and the wording of a
// registry search's answer from the site's own module; the few sentences here are the
// extension's own and never describe a claim.

const text = {
  checking: "Checking this page…",
  standing: "Where it stands",
  firstReported: "First reported",
  latestPromise: "Latest promise",
  open: "See the evidence",
  untrackedTitle: "This page is not a tracked report",
  untrackedBody: (name) =>
    `${name} follows particular news reports of medical breakthroughs, and this page is not one of them. That says nothing about the story itself.`,
  search: "Search tracked claims",
  offer: "Search the trial registry for this page",
  disclosure: (name) =>
    `This reads the page you have open, here in your browser, and sends its text and the links in it to ${name}, which asks a language model what it reports. The page's address is not sent, and ${name} keeps none of it. If a post links through X's shortened address, your browser opens that link, as a click would, to learn which article it leads to. To send only some of the page, select those words first.`,
  searching: "Reading this page and searching the registry. This can take half a minute.",
  tooLittleTitle: "Too little of this page could be read",
  tooLittleBody: "Select the words of the post or the article, then press the button again.",
  refusedTitle: "The search could not be made",
  refused: {
    busy: "Too many searches are being made right now. Try again in a minute.",
    not_set_up: (name) => `${name} is not offering the registry search at the moment.`,
    failed: "Nothing was found or ruled out. Try again in a minute.",
  },
  again: "Search again",
  noPageTitle: "Open an article first",
  noPageBody: (name) =>
    `Go to a news article about a medical breakthrough, then press the ${name} button again.`,
  unreachableTitle: (name) => `${name} could not be reached`,
  unreachableBody: "Check your connection, then try again.",
  retry: "Try again",
  lastChecked: (date) => `Registries last checked ${date}.`,
  saved: (date, name) => `Shown from the copy saved on ${date}. ${name} could not be reached just now.`,
};

const day = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });

function el(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (typeof content === "string") node.textContent = content;
  else if (content) node.append(...content.filter(Boolean));
  return node;
}

function fact(label, value, className) {
  return el("div", className, [el("dt", null, label), el("dd", null, value)]);
}

function link(label, href, className, onOpen) {
  const node = el("a", className, label);
  node.href = href;
  node.target = "_blank";
  node.rel = "noopener";
  node.addEventListener("click", (event) => {
    event.preventDefault();
    onOpen(href);
  });
  return node;
}

// A name such as "USAG-1" must not break at its hyphen.
function headline(words) {
  const parts = words.split(" ").flatMap((word, index) => [
    index > 0 && " ",
    word.includes("-") ? el("span", "unbroken", word) : word,
  ]);
  return el("h1", null, parts);
}

function claimBlock(claim, site, actions) {
  return el("article", "claim", [
    headline(claim.headline),
    el("dl", "digest", [
      el("dt", null, text.standing),
      el("dd", "status", claim.status),
      claim.no_signal && el("dd", "no-signal", claim.no_signal),
      el("dd", "meaning", claim.meaning),
    ]),
    claim.unchecked && el("p", "unchecked", claim.unchecked),
    el("dl", "facts", [
      claim.first_reported && fact(text.firstReported, claim.first_reported),
      claim.latest_promise && fact(text.latestPromise, claim.latest_promise, "promise"),
    ]),
    link(text.open, site.url + claim.page, "button", actions.open),
  ]);
}

function savedNote(state, site) {
  return state.savedAt ? el("p", "saved", text.saved(day.format(new Date(state.savedAt)), site.name)) : null;
}

function message(title, body, action) {
  return el("section", "message", [el("h1", null, title), el("p", null, body), action]);
}

function press(label, className, onPress) {
  const node = el("button", className, label);
  node.type = "button";
  node.addEventListener("click", onPress);
  return node;
}

/** A registry search's answer, in the words the site's own module gave it. */
function answerBlock(shown, site, actions) {
  const records = (items, address) =>
    el(
      "ul",
      "records",
      items.map((item) =>
        el("li", null, [
          link(item.title ?? item.headline, address(item), null, actions.open),
          // Phase, state and registry number are told apart at a glance as separate tags.
          item.detail &&
            el(
              "span",
              "tags",
              item.detail.split(" · ").map((part) => el("span", "tag", part)),
            ),
          item.why && el("span", "small", item.why),
        ]),
      ),
    );
  const context = [shown.source, shown.searchedAlso, shown.trialSaid].filter(Boolean);
  return [
    shown.marked && el("p", "unchecked", shown.marked),
    el("h1", "lead", shown.lead),
    // What the search was given to work with, kept together and apart from its results.
    context.length > 0 && el("div", "context", context.map((line) => el("p", null, line))),
    shown.tracked.length > 0 && records(shown.tracked, (claim) => site.url + claim.page),
    shown.likely.length > 0 && el("h2", "listed", shown.likelyLead),
    shown.likely.length > 0 && records(shown.likely, (record) => record.url),
    shown.none && el("p", null, shown.none),
    shown.rest && el("p", "small", shown.rest),
    shown.notices.length > 0 && el("footer", "notices", shown.notices.map((notice) => el("p", null, notice))),
  ];
}

/**
 * @param {HTMLElement} root
 * @param {object} state from stateFor(), or { kind: "checking" | "searching" | "too-little" },
 *   { kind: "refused", code }, or { kind: "answer", shown } with the site's wording of an answer
 * @param {{ name: string, url: string }} site
 * @param {{ open: (address: string) => void, retry: () => void, search: () => void }} actions
 */
export function render(root, state, site, actions) {
  let children;
  if (state.kind === "checking") {
    children = [el("p", "checking", text.checking)];
  } else if (state.kind === "tracked") {
    children = [
      ...state.claims.map((claim) => claimBlock(claim, site, actions)),
      el("footer", "notices", [
        ...state.notices.map((notice) => el("p", null, notice)),
        state.lastChecked && el("p", "checked", text.lastChecked(state.lastChecked)),
        savedNote(state, site),
      ]),
    ];
  } else if (state.kind === "untracked") {
    children = [
      message(
        text.untrackedTitle,
        text.untrackedBody(site.name),
        link(text.search, `${site.url}/`, "button quiet", actions.open),
      ),
      // Offered only where the site answers such a search. Nothing is read until pressed.
      state.live && el("section", "offer", [press(text.offer, "button", actions.search), el("p", "small", text.disclosure(site.name))]),
      savedNote(state, site) && el("footer", "notices", [savedNote(state, site)]),
    ];
  } else if (state.kind === "searching") {
    children = [el("p", "checking", text.searching)];
  } else if (state.kind === "too-little") {
    children = [message(text.tooLittleTitle, text.tooLittleBody, press(text.again, "button quiet", actions.search))];
  } else if (state.kind === "refused") {
    const why = text.refused[state.code] ?? text.refused.failed;
    children = [
      message(text.refusedTitle, typeof why === "function" ? why(site.name) : why, press(text.again, "button quiet", actions.search)),
    ];
  } else if (state.kind === "answer") {
    children = answerBlock(state.shown, site, actions);
  } else if (state.kind === "no-page") {
    children = [message(text.noPageTitle, text.noPageBody(site.name))];
  } else {
    const retry = el("button", "button quiet", text.retry);
    retry.type = "button";
    retry.addEventListener("click", actions.retry);
    children = [message(text.unreachableTitle(site.name), text.unreachableBody, retry)];
  }
  root.replaceChildren(...children.filter(Boolean));
  root.dataset.state = state.kind;
}
