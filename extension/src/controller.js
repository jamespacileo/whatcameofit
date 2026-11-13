// One popup opening owns one current-tab snapshot and one automatic lookup.
// Browser reading and answer wording are supplied by the popup's shared readers.
import {
  acknowledged,
  addRecent,
  answerOf,
  candidatesOf,
  follow as withFollowed,
  followedNow,
  outletOf,
  unfollow as withoutFollowed,
} from "./kept.js";
import { isFresh, stateFor } from "./lookup.js";

// A check that ended in one of these is worth finding again in the reader's own list.
const KEPT_KINDS = new Set(["tracked", "answer", "untracked"]);

const SIX_HOURS = 6 * 60 * 60 * 1000;
// Refresh pre-automatic-lookup caches once so an upgrade sees current service settings.
const CACHE_VERSION = 2;

export function createPopupController({ storage, fetch, site, readTab, readPage, isCurrentPage, describeAnswer, present }) {
  const abort = new AbortController();
  let tab = null;
  let live = null;
  let opening = null;
  let searching = null;
  let closed = false;
  // The lookup file as last loaded, the reader's own lists, and the page's own state,
  // which "Back" returns to without checking or searching again.
  let index = null;
  let recent = [];
  let follows = [];
  let pageState = null;

  const save = (values) => Promise.resolve().then(() => storage.set(values)).catch(() => {});

  // What every view needs to know about the reader's lists: how long they are, which
  // claims are followed, and which of those have moved since they were last seen.
  function kept() {
    const now = followedNow(follows, index);
    return {
      recent: recent.length,
      following: follows.length,
      changed: now.filter((claim) => claim.changed).length,
      followed: follows.map((claim) => claim.page),
      was: Object.fromEntries(now.filter((claim) => claim.changed).map((claim) => [claim.page, claim.was])),
    };
  }

  const show = (state) => {
    if (!closed) present(state, kept());
  };

  // The page's own answer: shown, kept for "Back", and added to the reader's list.
  // A followed claim seen here has been seen, so its change is not announced twice.
  function showPage(state) {
    pageState = state;
    if (tab?.key && KEPT_KINDS.has(state.kind)) {
      recent = addRecent(recent, {
        key: tab.key,
        url: tab.url,
        title: tab.title || tab.key,
        outlet: outletOf(tab.url),
        at: Date.now(),
        answer: answerOf(state),
      });
      save({ recent });
    }
    show(state);
    if (state.kind === "tracked") {
      const seenNow = state.claims.reduce((list, claim) => acknowledged(list, index, claim.page), follows);
      if (JSON.stringify(seenNow) !== JSON.stringify(follows)) {
        follows = seenNow;
        save({ follows });
      }
    }
  }

  async function loadIndex() {
    const { lookup: saved = null } = await storage.get("lookup").catch(() => ({}));
    if (saved?.version === CACHE_VERSION && isFresh(saved.savedAt, Date.now(), SIX_HOURS)) {
      return { index: saved.index, savedAt: null };
    }
    try {
      const response = await fetch(`${site.url}/lookup.json`, { cache: "no-store", signal: abort.signal });
      if (!response.ok) throw new Error(`status ${response.status}`);
      const index = await response.json();
      await storage.set({ lookup: { version: CACHE_VERSION, index, savedAt: Date.now() } }).catch(() => {});
      return { index, savedAt: null };
    } catch {
      return saved ? { index: saved.index, savedAt: saved.savedAt } : { index: null, savedAt: null };
    }
  }

  async function performSearch() {
    if (closed || !tab || !live) return;
    show({ kind: "searching" });
    let request;
    try {
      request = await readPage(tab, abort.signal);
    } catch (error) {
      showPage(error?.code === "page_changed" ? { kind: "refused", code: "page_changed" } : { kind: "too-little" });
      return;
    }
    if (closed) return;
    if (!request) {
      showPage({ kind: "too-little" });
      return;
    }
    const current = await isCurrentPage(tab).catch(() => false);
    if (closed) return;
    if (!current) {
      showPage({ kind: "refused", code: "page_changed" });
      return;
    }
    try {
      const response = await fetch(site.url + live, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: abort.signal,
      });
      const found = await response.json();
      if (!response.ok) {
        showPage({ kind: "refused", code: found?.error ?? "failed" });
        return;
      }
      showPage({ kind: "answer", shown: describeAnswer(found) });
    } catch {
      showPage({ kind: "refused", code: "failed" });
    }
  }

  function search() {
    // Repeated activation while reading or waiting must not buy another lookup.
    if (!searching) {
      searching = performSearch().finally(() => { searching = null; });
    }
    return searching;
  }

  async function run() {
    if (closed) return;
    show({ kind: "checking" });
    tab = await readTab().catch(() => null);
    if (closed) return;
    const [loaded, saved] = await Promise.all([
      tab?.key ? loadIndex() : { index: null, savedAt: null },
      storage.get(["recent", "follows"]).catch(() => ({})),
    ]);
    if (closed) return;
    index = loaded.index;
    recent = saved?.recent ?? [];
    follows = saved?.follows ?? [];
    const state = stateFor(tab?.key ?? null, loaded);
    live = state.live ?? null;
    if (state.kind === "untracked" && live) {
      await search();
      return;
    }
    showPage(state);
  }

  // The reader's lists. Nothing here reads a page, asks the site or starts a search.
  function showRecent() {
    show({ kind: "recent", entries: recent.map((entry) => ({ ...entry, candidates: candidatesOf(entry, site) })) });
  }

  function showEntry(pageKey) {
    const entry = recent.find((one) => one.key === pageKey);
    if (entry) show({ kind: "entry", entry: { ...entry, candidates: candidatesOf(entry, site) } });
  }

  function clearRecent() {
    recent = [];
    save({ recent });
    showRecent();
  }

  function showFollowing() {
    show({ kind: "following", claims: followedNow(follows, index) });
  }

  function back() {
    if (pageState) show(pageState);
  }

  function follow(claim) {
    follows = withFollowed(follows, claim);
    save({ follows });
    if (pageState) show(pageState);
  }

  // Stopping from the list keeps the reader in the list.
  function unfollow(page, { fromList = false } = {}) {
    follows = withoutFollowed(follows, page);
    save({ follows });
    if (fromList) showFollowing();
    else if (pageState) show(pageState);
  }

  /** The reader opened a followed claim: it has been seen as it now stands. */
  function seen(page) {
    follows = acknowledged(follows, index, page);
    return save({ follows });
  }

  function open() {
    if (!opening) {
      opening = run().finally(() => { opening = null; });
    }
    return opening;
  }

  function close() {
    closed = true;
    abort.abort();
  }

  return { open, search, close, showRecent, showEntry, clearRecent, showFollowing, back, follow, unfollow, seen };
}
