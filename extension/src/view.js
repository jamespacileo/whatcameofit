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
  disclosure: (name) =>
    `This page’s text and links go to ${name} for the lookup. If text misses visible media, a screenshot is sent automatically with the page address. OpenAI reads the text and image and may retain it for safety checks. Use public reports only.`,
  privacy: "Privacy",
  confidenceUnavailable: "Match confidence unavailable",
  confidenceMeaning: "Confidence estimates how closely each registry record matches this report.",
  reviewed: "Reviewed claim",
  searching: "Reading this page and searching the registry. This can take half a minute.",
  tooLittleTitle: "Too little of this page could be read",
  tooLittleBody: "Select the words of the post or article, then choose Search again. Nothing was sent.",
  refusedTitle: "The search could not be made",
  refused: {
    busy: "Too many searches are being made right now. Try again in a minute.",
    not_set_up: (name) => `${name} is not offering the registry search at the moment.`,
    failed: "Nothing was found or ruled out. Try again in a minute.",
    budget_exhausted: "Automatic search has used its monthly allowance. It will be available again next month. Reviewed claim pages remain available.",
    page_changed: "The page changed while this lookup started. Reopen the extension on the page you want to check.",
    post_unreadable: "The linked article could not be read and the post has too little text. Open the article in your browser and reopen the extension.",
    capture_unavailable: "This browser could not capture the visible page. Open the image or article in a normal browser tab, or select its text and search again.",
    capture_sensitive: "A password or editing field is visible, so no screenshot was sent. Close it or open the public report in a separate tab.",
    image_too_large: "The visible image is too large to send. Zoom in on the claim or select its words and search again.",
    image_invalid: "The screenshot could not be read. Reopen the extension to try again.",
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
  // The reader's own lists. These sentences are the extension's and describe no claim.
  recent: "Recently checked",
  following: "Following",
  changedCount: (count) => `${count} changed`,
  back: "Back",
  keptHere: "Kept in this browser only. Never sent anywhere.",
  recentEmpty: "Nothing checked yet.",
  checkedOn: (outlet, date) => (outlet ? `${outlet} · checked ${date}` : `Checked ${date}`),
  possible: (count) => `${count} possible records`,
  noneThen: "No record was found when this was checked. Open the page and press the button to check it again.",
  openPage: "Open the page",
  clear: "Clear this list",
  follow: "Follow this claim",
  followingThis: "You follow this claim.",
  stop: "Stop following",
  followingEmpty: "You follow no claims yet. Open a tracked report and choose Follow.",
  changed: "Changed",
  wasNow: (was, now) => `Was: ${was}. Now: ${now}.`,
  wasSince: (was) => `Changed since you last looked. Was: ${was}.`,
  gone: "This claim is no longer published.",
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

// Where the status sits on the path from preclinical to approved: a row of places, one
// marked. Drawn only when the lookup file gives the place; the status is beside it in words.
function track(place, places) {
  if (!place || !places) return null;
  const steps = el(
    "span",
    "steps",
    Array.from({ length: places }, (_, index) => el("span", index + 1 === place ? "step here" : "step")),
  );
  steps.setAttribute("role", "img");
  steps.setAttribute("aria-label", `Place ${place} of ${places} on the path from preclinical to approved`);
  return el("dd", "track", [steps]);
}

// Following a claim, or stopping: one control under the way to its evidence.
function followControl(claim, kept, actions) {
  if (!kept || !actions.follow) return null;
  if (kept.followed.includes(claim.page)) {
    return el("p", "small followed", [
      text.followingThis,
      " ",
      press(text.stop, "text-button", () => actions.unfollow(claim.page)),
    ]);
  }
  return press(text.follow, "button quiet", () => actions.follow(claim));
}

function claimBlock(claim, site, actions, places, kept) {
  const was = kept?.was?.[claim.page];
  return el("article", "claim", [
    headline(claim.headline),
    was && el("p", "moved", [el("span", "tag changed", text.changed), " ", text.wasSince(was)]),
    el("dl", "digest", [
      el("dt", null, text.standing),
      el("dd", "status", claim.status),
      track(claim.place, places),
      claim.no_signal && el("dd", "no-signal", claim.no_signal),
      el("dd", "meaning", claim.meaning),
    ]),
    claim.unchecked && el("p", "unchecked", claim.unchecked),
    el("dl", "facts", [
      claim.first_reported && fact(text.firstReported, claim.first_reported),
      claim.latest_promise && fact(text.latestPromise, claim.latest_promise, "promise"),
    ]),
    link(text.open, site.url + claim.page, "button", actions.open),
    followControl(claim, kept, actions),
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

function privacyNote(site, actions) {
  return el("p", "small privacy-note", [
    text.disclosure(site.name),
    " ",
    link(text.privacy, `${site.url}/privacy`, null, actions.open),
  ]);
}

/** A registry search's answer, in the words the site's own module gave it. */
function answerBlock(shown, site, actions) {
  const records = (items, address, automatic = false) =>
    el(
      "ul",
      "records",
      items.map((item) =>
        el("li", "result-card", [
          el("h2", "result-title", [link(item.title ?? item.headline, address(item), null, actions.open)]),
          el("p", "result-confidence", automatic ? (item.confidenceLabel ?? text.confidenceUnavailable) : text.reviewed),
          // Phase, state and registry number are told apart at a glance as separate tags.
          item.detail &&
            el(
              "p",
              "tags result-detail",
              item.detail.split(" · ").map((part) => el("span", "tag", part)),
            ),
          item.why && el("p", "small result-reason", item.why),
        ]),
      ),
    );
  const context = [shown.source, shown.searchedAlso, shown.trialSaid].filter(Boolean);
  return [
    shown.marked && el("p", "unchecked", shown.marked),
    el("h1", "lead", shown.lead),
    shown.marked && privacyNote(site, actions),
    // What the search was given to work with, kept together and apart from its results.
    context.length > 0 && el("div", "context", context.map((line) => el("p", null, line))),
    shown.tracked.length > 0 && records(shown.tracked, (claim) => site.url + claim.page),
    shown.likely.length > 0 && el("p", "listed", shown.likelyLead),
    shown.likely.length > 0 && el("p", "small", shown.confidenceMeaning ?? text.confidenceMeaning),
    shown.likely.length > 0 && records(shown.likely, (record) => record.url, true),
    shown.none && el("p", null, shown.none),
    shown.rest && el("p", "small", shown.rest),
    shown.notices.length > 0 && el("footer", "notices", shown.notices.map((notice) => el("p", null, notice))),
  ];
}

// The way to the reader's two lists, under whatever the page's own answer is. A list
// that has moved says so in words, never by a mark alone.
function keptNav(kept, actions) {
  if (!kept || !actions.showRecent) return null;
  return el("nav", "kept", [
    press(text.recent, "text-button", actions.showRecent),
    press(
      [text.following, kept.changed > 0 && el("span", "tag changed", text.changedCount(kept.changed))],
      "text-button",
      actions.showFollowing,
    ),
  ]);
}

function listHead(title, actions) {
  return [press(text.back, "text-button back", actions.back), el("h1", null, title)];
}

// One checked page: its title leads back to the page, and what the check found leads on.
function recentCard(entry, actions) {
  const { candidates } = entry;
  const [only] = candidates;
  return el("li", "result-card", [
    el("h2", "result-title", [link(entry.title, entry.url, null, actions.open)]),
    el("p", "small", text.checkedOn(entry.outlet, day.format(new Date(entry.at)))),
    entry.answer.unreviewed && el("p", "small", entry.answer.unreviewed),
    candidates.length === 1 && only.status && el("p", "kept-status", only.status),
    candidates.length === 1 && link(only.status ? text.open : only.title, only.url, "button quiet", actions.open),
    candidates.length > 1 && press(text.possible(candidates.length), "button quiet", () => actions.showEntry(entry.key)),
    candidates.length === 0 && el("p", "small", text.noneThen),
  ]);
}

function recentView(state, actions) {
  return [
    ...listHead(text.recent, actions),
    state.entries.length === 0
      ? el("p", null, text.recentEmpty)
      : el("ul", "records", state.entries.map((entry) => recentCard(entry, actions))),
    el("footer", "notices", [
      el("p", null, text.keptHere),
      state.entries.length > 0 && press(text.clear, "text-button", actions.clearRecent),
    ]),
  ];
}

function entryView(state, actions) {
  const { entry } = state;
  return [
    press(text.back, "text-button back", actions.showRecent),
    el("h1", null, entry.title),
    el("p", "small", text.checkedOn(entry.outlet, day.format(new Date(entry.at)))),
    entry.answer.unreviewed && el("p", "unchecked", entry.answer.unreviewed),
    el(
      "ul",
      "records",
      entry.candidates.map((candidate) =>
        el("li", "result-card", [
          el("h2", "result-title", [link(candidate.title, candidate.url, null, actions.open)]),
          candidate.status && el("p", "kept-status", candidate.status),
        ]),
      ),
    ),
    link(text.openPage, entry.url, "button quiet", actions.open),
  ];
}

function followingView(state, site, actions) {
  return [
    ...listHead(text.following, actions),
    state.claims.length === 0
      ? el("p", null, text.followingEmpty)
      : el(
          "ul",
          "records",
          state.claims.map((claim) =>
            el("li", "result-card", [
              el("h2", "result-title", [
                claim.gone
                  ? claim.headline
                  : link(claim.headline, site.url + claim.page, null, () => actions.openFollowed(claim.page)),
              ]),
              claim.gone ? el("p", "small", text.gone) : el("p", "kept-status", claim.status),
              claim.changed &&
                el("p", "moved", [el("span", "tag changed", text.changed), " ", text.wasNow(claim.was, claim.status)]),
              press(text.stop, "text-button", () => actions.unfollow(claim.page, { fromList: true })),
            ]),
          ),
        ),
    el("footer", "notices", [el("p", null, text.keptHere)]),
  ];
}

const LISTS = new Set(["recent", "entry", "following"]);
// While the page is being read there is nothing to go back to, so the lists wait.
const BUSY = new Set(["checking", "searching", "capturing"]);

/**
 * @param {HTMLElement} root
 * @param {object} state from stateFor(), or { kind: "checking" | "searching" | "too-little" },
 *   { kind: "refused", code }, { kind: "answer", shown } with the site's wording of an answer,
 *   or one of the reader's lists: { kind: "recent", entries }, { kind: "entry", entry },
 *   { kind: "following", claims }
 * @param {{ name: string, url: string }} site
 * @param {{ open: (address: string) => void, retry: () => void, search: () => void }} actions
 * @param {object} [kept] what the reader's lists hold; without it no list is offered
 */
export function render(root, state, site, actions, kept = null) {
  let children;
  if (state.kind === "checking") {
    children = [el("p", "checking", text.checking)];
  } else if (state.kind === "recent") {
    children = recentView(state, actions);
  } else if (state.kind === "entry") {
    children = entryView(state, actions);
  } else if (state.kind === "following") {
    children = followingView(state, site, actions);
  } else if (state.kind === "tracked") {
    children = [
      ...state.claims.map((claim) => claimBlock(claim, site, actions, state.places, kept)),
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
  } else if (state.kind === "capturing") {
    children = [el("p", "checking", "Reading the visible image…"), privacyNote(site, actions)];
  } else if (state.kind === "visual-preview") {
    const preview = el("img", "visual-preview");
    preview.src = state.image.dataUrl;
    preview.alt = "The visible content that will be sent for lookup";
    children = [el("h1", null, "Search this visible image"), preview,
      el("p", "small", "This image and the page address go to What came of it? and OpenAI. Check for private messages or other personal information. A video contributes only this frame, not its audio."),
      press("Search this image", "button", actions.sendVisual), press("Cancel", "button quiet", actions.cancelVisual)];
  } else if (state.kind === "searching") {
    children = [el("p", "checking", state.visual ? "Reading the screenshot and searching the registry…" : text.searching), privacyNote(site, actions)];
  } else if (state.kind === "too-little") {
    children = [message(text.tooLittleTitle, text.tooLittleBody, press(text.again, "button quiet", actions.search))];
  } else if (state.kind === "refused") {
    const why = text.refused[state.code] ?? text.refused.failed;
    children = [
      message(
        text.refusedTitle,
        typeof why === "function" ? why(site.name) : why,
        press(text.again, "button quiet", state.code === "page_changed" ? actions.retry : actions.search),
      ),
      privacyNote(site, actions),
    ];
  } else if (state.kind === "answer") {
    children = answerBlock(state.shown, site, actions);
    if (state.cachedAt) children.unshift(el("p", "small", `Previous result · checked ${new Date(state.cachedAt).toLocaleString("en-GB")}. Search again for a fresh lookup.`));
    if (actions.search) children.push(press(text.again, "button quiet", actions.search));
  } else if (state.kind === "no-page") {
    children = [message(text.noPageTitle, text.noPageBody(site.name))];
  } else {
    const retry = el("button", "button quiet", text.retry);
    retry.type = "button";
    retry.addEventListener("click", actions.retry);
    children = [message(text.unreachableTitle(site.name), text.unreachableBody, retry)];
  }
  if (state.canVisual && actions.previewVisual) children.push(press("Preview a screenshot instead", "text-button", actions.previewVisual));
  if (!LISTS.has(state.kind) && !BUSY.has(state.kind) && state.kind !== "visual-preview") children.push(keptNav(kept, actions));
  root.replaceChildren(...children.filter(Boolean));
  root.dataset.state = state.kind;
  root.setAttribute("aria-busy", String(BUSY.has(state.kind)));
}
