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
import { remember, reusable, savedFor } from "./results.js";
import { fingerprint, publicWebUrl } from "./visual.js";
import { remind as withReminder, reminderDay, unremind as withoutReminder } from "./watch.js";

// A check that ended in one of these is worth finding again in the reader's own list.
const KEPT_KINDS = new Set(["tracked", "answer", "untracked"]);

const SIX_HOURS = 6 * 60 * 60 * 1000;
// One search or screenshot attempt, everything in it included, ends by this time.
const LOOKUP_TIMEOUT_MS = 45_000;
// The lookup file and an earlier shared result are each waited on no longer than this.
const INDEX_TIMEOUT_MS = 5_000;
const CACHE_PROBE_TIMEOUT_MS = 1_500;
// A staged answer larger than this, or one line of it, is refused as malformed.
const MAX_STREAM_BYTES = 4_000_000;
const STREAMED = /^application\/x-ndjson\b/i;

const malformed = () => Object.assign(new Error("malformed"), { code: "failed" });
const ended = () => Object.assign(new Error("ended"), { name: "AbortError" });

function eventOf(line) {
  let event;
  try { event = JSON.parse(line); } catch { throw malformed(); }
  if (!event || typeof event !== "object" || !["core", "complete", "error"].includes(event.type)) throw malformed();
  if (event.type !== "error" && (!event.result || typeof event.result !== "object" || Array.isArray(event.result))) throw malformed();
  return event;
}

/**
 * The events of a staged lookup answer, one JSON object per line, as they arrive. A line
 * may be split across chunks, a character across bytes. Malformed, oversized or cut-off
 * input throws; aborting `signal` stops reading and cancels the body.
 */
export async function* lookupEvents(response, signal, { maxBytes = MAX_STREAM_BYTES } = {}) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  const stop = () => { reader.cancel().catch(() => {}); };
  signal?.addEventListener("abort", stop, { once: true });
  let buffer = "";
  let size = 0;
  let finished = false;
  try {
    for (;;) {
      if (signal?.aborted) throw ended();
      const { done, value } = await reader.read();
      if (signal?.aborted) throw ended();
      if (done) break;
      size += value.byteLength;
      if (size > maxBytes) throw malformed();
      try { buffer += decoder.decode(value, { stream: true }); } catch { throw malformed(); }
      for (let at = buffer.indexOf("\n"); at >= 0; at = buffer.indexOf("\n")) {
        const line = buffer.slice(0, at).trim();
        buffer = buffer.slice(at + 1);
        if (line) yield eventOf(line);
      }
    }
    try { buffer += decoder.decode(); } catch { throw malformed(); }
    finished = true;
    // A last line without its newline counts only if it is whole.
    if (buffer.trim()) yield eventOf(buffer.trim());
  } finally {
    signal?.removeEventListener("abort", stop);
    if (!finished) stop();
  }
}

const streamed = (response) => response?.ok && STREAMED.test(response.headers?.get?.("content-type") ?? "") &&
  typeof response.body?.getReader === "function";

/** `work(signal)` within `ms`, its body included: past it the signal is aborted and this
 * rejects, even if the work does not listen. `parent` aborting aborts the work too. */
async function bounded(ms, parent, work) {
  const controller = new AbortController();
  const stop = () => controller.abort();
  parent.addEventListener("abort", stop, { once: true });
  let timer;
  const late = new Promise((_resolve, reject) => {
    timer = setTimeout(() => { controller.abort(); reject(new Error("timeout")); }, ms);
  });
  try {
    return await Promise.race([Promise.resolve().then(() => work(controller.signal)), late]);
  } finally {
    clearTimeout(timer);
    parent.removeEventListener("abort", stop);
  }
}

export function createPopupController({ storage, fetch, site, readTab, readPage, isCurrentPage, capturePage, describeAnswer, present, requiresSharingConsent = false,
  lookupTimeoutMs = LOOKUP_TIMEOUT_MS, indexTimeoutMs = INDEX_TIMEOUT_MS, cacheProbeTimeoutMs = CACHE_PROBE_TIMEOUT_MS, now = Date.now }) {
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
  let justFollowed = null;
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
      // The claim followed by the press being answered now, so its tick is drawn once.
      fresh: justFollowed,
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
      const index = await bounded(indexTimeoutMs, abort.signal, async (signal) => {
        const response = await fetch(`${site.url}/lookup.json`, { cache: "no-store", signal });
        if (!response.ok) throw new Error(`status ${response.status}`);
        return response.json();
      });
      await storage.set({ lookup: { version: CACHE_VERSION, index, savedAt: Date.now() } }).catch(() => {});
      return { index, savedAt: null };
    } catch {
      return saved ? { index: saved.index, savedAt: saved.savedAt } : { index: null, savedAt: null };
    }
  }

  // One search or screenshot attempt: its own signal and one deadline over all of it. Once
  // it has ended, by its deadline or the popup closing, nothing it was waiting on shows,
  // saves or sends anything. A timeout is not an answer: it says so and offers a retry.
  function attempt(work) {
    const controller = new AbortController();
    let over = false;
    let timer;
    let closing;
    // A completed core answer already shown stays when only its enrichment runs out of time.
    let kept = null;
    const started = now();
    const scope = {
      signal: controller.signal,
      over: () => over || closed,
      show: (state) => { if (!scope.over()) show(state); },
      showPage: (state) => { if (!scope.over()) showPage(state); },
      save: (values) => (scope.over() ? Promise.resolve() : save(values)),
      keep: (state) => { kept = state; },
      // Milliseconds since this attempt began: a number, never content.
      elapsed: () => Math.max(0, now() - started),
    };
    const ended = new Promise((resolve) => {
      closing = () => { controller.abort(); resolve("closed"); };
      abort.signal.addEventListener("abort", closing, { once: true });
      timer = setTimeout(resolve, lookupTimeoutMs, "timeout");
    });
    if (abort.signal.aborted) closing();
    const done = Promise.resolve().then(() => work(scope)).then(() => "done", () => "done");
    return Promise.race([done, ended]).then(async (outcome) => {
      clearTimeout(timer);
      abort.signal.removeEventListener("abort", closing);
      const timedOut = outcome === "timeout" && !scope.over();
      over = true;
      if (outcome !== "done") controller.abort();
      if (timedOut && kept) {
        // The clinical result already left the blocking spinner. Before changing its
        // enrichment notice, recheck identity without allowing a stuck browser check
        // to hold this ended attempt open. Unknown identity fails closed.
        const samePage = await bounded(100, abort.signal, () => isCurrentPage(tab)).catch(() => false);
        if (samePage && !closed) showPage(kept);
      } else if (timedOut) showPage({ kind: "refused", code: "timeout" });
    });
  }

  const serviceRequest = request => {
    const { visualCandidate, selectionOnly, contentFingerprint, readableArticle, ...sent } = request;
    return sent;
  };
  const eligible = () => Boolean(sharing && capturePage && tab && live && !tab.incognito && publicWebUrl(tab.url));
  // A text reading that finds no treatment does not settle a page whose claim may be in
  // its media: a screenshot follows, and that first reading is neither shown nor kept.
  const mediaDependent = (request) => Boolean(request?.visualCandidate && !request.selectionOnly && !request.readableArticle);
  async function current(scope) {
    return !scope.over() && await isCurrentPage(tab).catch(() => false) && !scope.over();
  }
  function resultState(found, cachedAt = null, extra = {}) {
    const shown = describeAnswer(found);
    if (cachedAt && shown.marked) shown.marked = "Automatic search from an earlier check. It has not been checked by a person and is not a status.";
    return { kind: "answer", shown, cachedAt, canVisual: eligible(), ...extra };
  }
  // Stage durations for comparing a first answer with a complete one: numbers only.
  function timingsOf(stages, service) {
    const times = { ...stages };
    for (const [name, value] of Object.entries(service && typeof service === "object" ? service : {})) {
      if (/^[a-z_]+$/.test(name) && Number.isFinite(value)) times[`service_${name}`] = value;
    }
    return { timings: Object.fromEntries(Object.entries(times).map(([name, value]) => [name, Math.round(value)])) };
  }
  /** An earlier shared result for this page's cleaned address, or null. Never throws. */
  async function probeShared(scope, pageUrl) {
    if (!await current(scope)) return null;
    // An earlier shared result is a shortcut only: when it is slow, the search goes on.
    try {
      const { response, saved } = await bounded(cacheProbeTimeoutMs, scope.signal, async (signal) => {
        const response = await fetch(site.url + live, { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cacheOnly: true, pageUrl }), signal });
        return { response, saved: await response.json() };
      });
      return response.ok && saved?.cache?.shared && typeof saved.cache.checkedAt === "number" &&
        typeof saved.about_a_treatment === "boolean" ? saved : null;
    } catch { return null; }
  }
  // A finished answer: kept for this content when whole and final, then shown.
  function settle(scope, found, { key, provisional, stages = {}, service = null }) {
    if (provisional && found?.about_a_treatment === false) return found;
    if (key) {
      results = remember(results, tab.key, key, found, found.cache?.checkedAt ?? Date.now());
      scope.save({ results });
    }
    scope.showPage(resultState(found, found.cache?.checkedAt ?? null, timingsOf({ ...stages, complete_ms: scope.elapsed() }, service)));
    return found;
  }
  function refusedBy(scope, code) {
    scope.showPage({ kind: "refused", code: code ?? "failed", ...(eligible() && code !== "budget_exhausted" ? { canVisual: true } : {}) });
    return null;
  }
  // A staged answer: the completed clinical answer is shown as soon as it arrives, with
  // research still loading. If the rest never comes, the core answer stays, said to be
  // without its research, and is not kept. Nothing renders once the attempt has ended.
  async function receive(scope, response, { key, provisional }) {
    let core = null;
    let stages = {};
    const coreShown = () => core && !(provisional && core.about_a_treatment === false);
    try {
      for await (const event of lookupEvents(response, scope.signal)) {
        if (scope.over()) return null;
        if (event.type === "error" && core) break;
        if (!await current(scope)) { scope.showPage({ kind: "refused", code: "page_changed" }); return null; }
        if (event.type === "error") return refusedBy(scope, typeof event.error === "string" ? event.error : "failed");
        if (event.type === "complete") {
          scope.keep(null);
          return settle(scope, event.result, { key, provisional, stages, service: event.timings });
        }
        if (core) continue;
        core = event.result;
        stages = { core_ms: scope.elapsed() };
        if (coreShown()) {
          const pending = core.about_a_treatment === true && !core.research;
          const timings = timingsOf(stages, event.timings);
          scope.showPage(resultState(core, core.cache?.checkedAt ?? null, { ...(pending ? { research: "loading" } : {}), ...timings }));
          scope.keep(resultState(core, core.cache?.checkedAt ?? null, { ...(pending ? { research: "incomplete" } : {}), ...timings }));
        }
      }
    } catch {
      if (scope.over()) return null;
    }
    if (scope.over()) return null;
    scope.keep(null);
    if (!await current(scope)) return null;
    if (!core) return refusedBy(scope, "failed");
    if (coreShown()) {
      const pending = core.about_a_treatment === true && !core.research;
      scope.showPage(resultState(core, core.cache?.checkedAt ?? null, { ...(pending ? { research: "incomplete" } : {}), ...timingsOf(stages) }));
    }
    // A non-treatment core is a finished identification, so its screenshot may follow.
    return core;
  }
  async function send(scope, request, { reuse = false, key = null, provisional = false } = {}) {
    if (!await current(scope)) { scope.showPage({ kind: "refused", code: "page_changed" }); return null; }
    if (reuse && key) {
      const saved = reusable(results, tab.key, key, Date.now());
      if (saved) { scope.showPage(resultState(saved.found, saved.at, timingsOf({ reused_ms: scope.elapsed() }))); return saved.found; }
    }
    // A staged answer is asked for; a service that answers in one piece is read as before.
    const response = await fetch(site.url + live, {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/x-ndjson, application/json" },
      body: JSON.stringify({ ...serviceRequest(request), ...(request.pageUrl ? { refresh: !reuse } : {}), stream: true }), signal: scope.signal,
    });
    if (streamed(response)) return receive(scope, response, { key, provisional });
    const found = await response.json();
    if (!await current(scope)) { scope.showPage({ kind: "refused", code: "page_changed" }); return null; }
    if (!response.ok) return refusedBy(scope, found?.error);
    return settle(scope, found, { key, provisional });
  }
  async function visualSearch(scope, { preview = false, reuse = true } = {}) {
    if (!eligible() || scope.over()) return;
    const generation = ++visualGeneration;
    scope.show({ kind: "capturing" });
    try {
      const captured = await capturePage(tab, scope.signal);
      if (scope.over() || generation !== visualGeneration) return;
      const request = { ...serviceRequest(lastRead ?? { text: "", links: [] }), ...captured };
      // Image bytes enter only a one-way digest, never browser storage.
      const key = lastRead?.selectionOnly ? null : await fingerprint(request);
      if (scope.over()) return;
      if (preview) { visual = { request, key }; scope.show({ kind: "visual-preview", image: captured.image }); return; }
      scope.show({ kind: "searching", visual: true });
      await send(scope, request, { reuse, key });
    } catch (error) {
      if (generation === visualGeneration) scope.showPage({ kind: "refused", code: error?.code ?? "capture_unavailable", canVisual: false });
    }
  }
  async function performSearch(scope, { reuse = false } = {}) {
    if (scope.over() || !tab || !live) return;
    if (!sharing) { sharingView(); return; }
    visual = null;
    scope.show({ kind: "searching" });
    // The shared-result probe may start while the page is still being collected, once
    // the page reader has settled selection, private-window and address checks. When
    // this page has a saved result here, it waits: the content may match that instead.
    let probe = null;
    let probedFor = null;
    const startProbe = (pageUrl) => {
      if (probe || !reuse || !pageUrl || tab.incognito || scope.over() || savedFor(results, tab.key, Date.now())) return;
      probedFor = pageUrl;
      probe = probeShared(scope, pageUrl);
    };
    let request;
    try { request = await readPage(tab, scope.signal, { onContext: (context) => startProbe(context?.pageUrl) }); }
    catch (error) {
      scope.showPage(error?.code === "page_changed" ? { kind: "refused", code: "page_changed" } : { kind: "too-little", canVisual: eligible() });
      return;
    }
    if (scope.over()) return;
    lastRead = request;
    if (!request) { scope.showPage({ kind: "too-little", canVisual: eligible() }); return; }
    if (!await current(scope)) { scope.showPage({ kind: "refused", code: "page_changed" }); return; }
    try {
      const key = !request.selectionOnly && request.contentFingerprint ? request.contentFingerprint : null;
      if (reuse && key) {
        const saved = reusable(results, tab.key, key, Date.now());
        if (saved) { scope.showPage(resultState(saved.found, saved.at, timingsOf({ reused_ms: scope.elapsed() }))); return; }
      }
      if (reuse && request.pageUrl && !request.selectionOnly) {
        if (!probe || probedFor !== request.pageUrl) probe = probeShared(scope, request.pageUrl);
        const shared = await probe;
        if (!await current(scope)) { scope.showPage({ kind: "refused", code: "page_changed" }); return; }
        if (shared) {
          const final = shared.about_a_treatment === true || !mediaDependent(request);
          if (final || !eligible()) {
            // Dated as first checked, and kept for this content once whole and final.
            if (key && final) {
              results = remember(results, tab.key, key, shared, shared.cache.checkedAt);
              scope.save({ results });
            }
            scope.showPage(resultState(shared, shared.cache.checkedAt, timingsOf({ reused_ms: scope.elapsed() })));
            return;
          }
          // The public words were read as no treatment; what the media shows is read next.
          await visualSearch(scope, { reuse }); return;
        }
      } else if (probe) {
        // Not to be used: the reading has since turned out to be the reader's own selection.
        probe = null;
      }
      // A media-only post does not buy a fruitless caption-only model call first.
      const earlierVisual = reuse && results.some(entry => entry.key === tab.key && entry.found?.source?.kind === "screenshot");
      if (mediaDependent(request) && !request.links?.length && (request.text.length < 240 || earlierVisual)) {
        await visualSearch(scope, { reuse }); return;
      }
      const provisional = mediaDependent(request) && eligible();
      const found = await send(scope, request, { reuse, key, provisional });
      if (found?.about_a_treatment === false && provisional) await visualSearch(scope, { reuse });
    } catch { scope.showPage({ kind: "refused", code: "failed", canVisual: eligible() }); }
  }
  function search(options) {
    if (!searching) searching = attempt((scope) => performSearch(scope, options)).finally(() => { searching = null; });
    return searching;
  }
  function previewVisual() {
    if (!searching) searching = attempt((scope) => visualSearch(scope, { preview: true })).finally(() => { searching = null; });
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
    searching = attempt((scope) => send(scope, selected.request, { reuse: true, key: selected.key })
      .catch(() => scope.showPage({ kind: "refused", code: "failed" }))).finally(() => { searching = null; });
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
    justFollowed = claim.page;
    if (pageState) show(pageState);
    justFollowed = null;
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
