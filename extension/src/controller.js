// One popup opening owns one current-tab snapshot and one automatic lookup.
// Browser reading and answer wording are supplied by the popup's shared readers.
import { isFresh, stateFor } from "./lookup.js";

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

  const show = (state) => {
    if (!closed) present(state);
  };

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
      show(error?.code === "page_changed" ? { kind: "refused", code: "page_changed" } : { kind: "too-little" });
      return;
    }
    if (closed) return;
    if (!request) {
      show({ kind: "too-little" });
      return;
    }
    const current = await isCurrentPage(tab).catch(() => false);
    if (closed) return;
    if (!current) {
      show({ kind: "refused", code: "page_changed" });
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
        show({ kind: "refused", code: found?.error ?? "failed" });
        return;
      }
      show({ kind: "answer", shown: describeAnswer(found) });
    } catch {
      show({ kind: "refused", code: "failed" });
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
    const loaded = tab?.key ? await loadIndex() : { index: null, savedAt: null };
    if (closed) return;
    const state = stateFor(tab?.key ?? null, loaded);
    live = state.live ?? null;
    if (state.kind === "untracked" && live) {
      await search();
      return;
    }
    show(state);
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

  return { open, search, close };
}
