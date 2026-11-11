// Draws one popup state. Status wording comes from the lookup file; the few sentences
// here are the extension's own and never describe a claim.

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

/**
 * @param {HTMLElement} root
 * @param {object} state from stateFor(), or { kind: "checking" }
 * @param {{ name: string, url: string }} site
 * @param {{ open: (address: string) => void, retry: () => void }} actions
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
      savedNote(state, site) && el("footer", "notices", [savedNote(state, site)]),
    ];
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
