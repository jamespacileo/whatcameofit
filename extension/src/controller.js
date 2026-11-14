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
import { CACHE_VERSION, isFresh, stateFor } from "./lookup.js";
import { remember, reusable } from "./results.js";
import { fingerprint, publicWebUrl } from "./visual.js";
import { remind as withReminder, reminderDay, unremind as withoutReminder } from "./watch.js";

// A check that ended in one of these is worth finding again in the reader's own list.
const KEPT_KINDS = new Set(["tracked", "answer", "untracked"]);

const SIX_HOURS = 6 * 60 * 60 * 1000;

export function createPopupController({ storage, fetch, site, readTab, readPage, isCurrentPage, capturePage, describeAnswer, present, requiresSharingConsent = false }) {
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
  // One reminder per claim, each a day to look again; the background check shows it.
  let reminders = [];
  let follows = [];
  let pageState = null;
  let results = [];
  let visual = null;
  let lastRead = null;
  let visualGeneration = 0;
  let sharing = !requiresSharingConsent;
  let sharingWriteFailed = false;
  const sharingView = () => show({ kind: "sharing", enabled: sharing });

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
      reminders: Object.fromEntries(reminders.map((reminder) => [reminder.page, reminder.date])),
    };
  }

  const show = (state) => {
    if (!closed) present(state, kept());
  };

  // The page's own answer: shown, kept for "Back", and added to the reader's list.
  // A followed claim seen here has been seen, so its change is not announced twice.
  function showPage(state) {
    pageState = state;
    // The site's own claim page is not a report the reader checked.
    if (tab?.key && !tab.incognito && !state.own && KEPT_KINDS.has(state.kind)) {
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

  const serviceRequest = request => {
    const { visualCandidate, selectionOnly, contentFingerprint, ...sent } = request;
    return sent;
  };
  const eligible = () => Boolean(sharing && capturePage && tab && live && !tab.incognito && publicWebUrl(tab.url));
  async function current() {
    return !closed && await isCurrentPage(tab).catch(() => false) && !closed;
  }
  function resultState(found, cachedAt = null) {
    const shown = describeAnswer(found);
    if (cachedAt && shown.marked) shown.marked = "Automatic search from an earlier check. It has not been checked by a person and is not a status.";
    return { kind: "answer", shown, cachedAt, canVisual: eligible() };
  }
  async function send(request, { reuse = false, key = null } = {}) {
    if (!await current()) { showPage({ kind: "refused", code: "page_changed" }); return null; }
    if (reuse && key) {
      const saved = reusable(results, tab.key, key, Date.now());
      if (saved) { showPage(resultState(saved.found, saved.at)); return saved.found; }
    }
    const response = await fetch(site.url + live, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...serviceRequest(request), ...(request.pageUrl ? { refresh: !reuse } : {}) }), signal: abort.signal,
    });
    const found = await response.json();
    if (!await current()) { showPage({ kind: "refused", code: "page_changed" }); return null; }
    if (!response.ok) { showPage({ kind: "refused", code: found?.error ?? "failed", ...(eligible() && found?.error !== "budget_exhausted" ? { canVisual: true } : {}) }); return null; }
    if (key) {
      results = remember(results, tab.key, key, found, found.cache?.checkedAt ?? Date.now());
      save({ results });
    }
    showPage(resultState(found, found.cache?.checkedAt ?? null));
    return found;
  }
  async function visualSearch({ preview = false, reuse = true } = {}) {
    if (!eligible() || closed) return;
    const generation = ++visualGeneration;
    show({ kind: "capturing" });
    try {
      const captured = await capturePage(tab, abort.signal);
      if (closed || generation !== visualGeneration) return;
      const request = { ...serviceRequest(lastRead ?? { text: "", links: [] }), ...captured };
      // Image bytes enter only a one-way digest, never browser storage.
      const key = lastRead?.selectionOnly ? null : await fingerprint(request);
      if (preview) { visual = { request, key }; show({ kind: "visual-preview", image: captured.image }); return; }
      show({ kind: "searching", visual: true });
      await send(request, { reuse, key });
    } catch (error) {
      if (generation === visualGeneration) showPage({ kind: "refused", code: error?.code ?? "capture_unavailable", canVisual: false });
    }
  }
  async function performSearch({ reuse = false } = {}) {
    if (closed || !tab || !live) return;
    if (!sharing) { sharingView(); return; }
    visual = null;
    show({ kind: "searching" });
    let request;
    try { request = await readPage(tab, abort.signal); }
    catch (error) {
      showPage(error?.code === "page_changed" ? { kind: "refused", code: "page_changed" } : { kind: "too-little", canVisual: eligible() });
      return;
    }
    if (closed) return;
    lastRead = request;
    if (!request) { showPage({ kind: "too-little", canVisual: eligible() }); return; }
    if (!await current()) { showPage({ kind: "refused", code: "page_changed" }); return; }
    try {
      if (reuse && !request.selectionOnly && request.contentFingerprint) {
        const saved = reusable(results, tab.key, request.contentFingerprint, Date.now());
        if (saved) { showPage(resultState(saved.found, saved.at)); return; }
      }
      if (reuse && request.pageUrl) {
        try {
          const response = await fetch(site.url + live, { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cacheOnly: true, pageUrl: request.pageUrl }), signal: abort.signal });
          const saved = await response.json();
          if (!await current()) { showPage({ kind: "refused", code: "page_changed" }); return; }
          if (response.ok && saved.cache?.shared && saved.about_a_treatment === true) {
            showPage(resultState(saved, saved.cache.checkedAt)); return;
          }
        } catch { if (closed) return; }
      }
      // A media-only post does not buy a fruitless caption-only model call first.
      const earlierVisual = reuse && results.some(entry => entry.key === tab.key && entry.found?.source?.kind === "screenshot");
      if (request.visualCandidate && !request.selectionOnly && !request.links?.length && (request.text.length < 240 || earlierVisual)) {
        await visualSearch({ reuse }); return;
      }
      const key = !request.selectionOnly && request.contentFingerprint ? request.contentFingerprint : null;
      const found = await send(request, { reuse, key });
      if (found?.about_a_treatment === false && request.visualCandidate && !request.selectionOnly) await visualSearch({ reuse });
    } catch { showPage({ kind: "refused", code: "failed", canVisual: eligible() }); }
  }
  function search(options) {
    if (!searching) searching = performSearch(options).finally(() => { searching = null; });
    return searching;
  }
  function previewVisual() {
    if (!searching) searching = visualSearch({ preview: true }).finally(() => { searching = null; });
    return searching;
  }
  function cancelVisual() {
    visualGeneration++;
    visual = null;
    if (pageState) show(pageState);
    else showPage({ kind: "too-little", canVisual: eligible() });
  }
  function sendVisual() {
    if (!visual || searching) return searching;
    const selected = visual; visual = null;
    show({ kind: "searching", visual: true });
    searching = send(selected.request, { reuse: true, key: selected.key })
      .catch(() => showPage({ kind: "refused", code: "failed" })).finally(() => { searching = null; });
    return searching;
  }

  async function run() {
    if (closed) return;
    show({ kind: "checking" });
    tab = await readTab().catch(() => null);
    if (closed) return;
    const [loaded, saved] = await Promise.all([
      tab?.key ? loadIndex() : { index: null, savedAt: null },
      storage.get(["recent", "follows", "results", "sharing", "reminders"]).catch(() => ({})),
    ]);
    if (closed) return;
    index = loaded.index;
    recent = saved?.recent ?? [];
    follows = saved?.follows ?? [];
    reminders = saved?.reminders ?? [];
    results = saved?.results ?? [];
    sharing = !sharingWriteFailed && (!requiresSharingConsent || saved?.sharing?.version === 1 && saved.sharing.enabled === true);
    const state = stateFor(tab?.key ?? null, loaded, site.key ?? null);
    live = state.live ?? null;
    if (state.kind === "untracked" && live) {
      if (!sharing) {
        if (saved?.sharing?.enabled === false) showPage({ ...state, live: null });
        else sharingView();
        return;
      }
      await search({ reuse: true });
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
    results = [];
    const saving = save({ recent, results });
    showRecent();
    return saving;
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

  /** A reminder in six months or a year; `today` is the reader's own date. */
  function remindLater(claim, choice, today) {
    reminders = withReminder(reminders, claim, reminderDay(choice, today));
    save({ reminders });
    if (pageState) show(pageState);
  }

  function forget(page) {
    reminders = withoutReminder(reminders, page);
    save({ reminders });
    if (pageState) show(pageState);
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
    visual = null;
    lastRead = null;
    visualGeneration++;
    abort.abort();
  }

  async function enableSharing() {
    if (!await saveSharing(true)) return;
    if (!live && pageState) show(pageState);
    else await search({ reuse: true });
  }

  async function disableSharing() {
    if (!await saveSharing(false)) return;
    showPage(!live && pageState ? pageState : { kind: "untracked" });
  }

  async function saveSharing(enabled) {
    sharing = false;
    try {
      await storage.set({ sharing: { version: 1, enabled } });
      sharingWriteFailed = false;
      sharing = enabled;
      return true;
    } catch {
      sharingWriteFailed = true;
      // Removing a previous opt-in is a fail-closed fallback when updating fails.
      let cleared = false;
      if (!enabled && storage.remove) {
        try { await storage.remove("sharing"); cleared = true; } catch { /* Explain the unsaved choice. */ }
      }
      show({ kind: "sharing-error", requested: enabled, cleared });
      return false;
    }
  }

  return { open, search, previewVisual, sendVisual, cancelVisual, close, showRecent, showEntry, clearRecent, showFollowing, back, follow, unfollow, seen, remindLater, forget, sharingView, enableSharing, disableSharing };
}
