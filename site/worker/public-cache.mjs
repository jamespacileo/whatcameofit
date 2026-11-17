// Bounded reuse of public source answers within and across lookups: what a paper's
// abstract says its trial is, and what the public registry returned for one query.
// Only structured public answers are kept, under a digest of the public query: never an
// abstract, article text, image, reader or credential. A slow or failing cache is a miss.

// Version 2: a registry answer is kept without its people. An entry of version 1 could
// hold a whole record, contacts included, and is never read again.
const VERSION = 2;
// No source answer is reused for longer than this.
export const SOURCE_TTL_SECONDS = 86_400;
// The longest one cache read or write is waited on.
export const CACHE_TIMEOUT_MS = 200;
// A cached value larger than this is not written.
const MAX_VALUE_CHARACTERS = 2_000_000;

export async function digest(value) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(value)));
  return [...new Uint8Array(bytes)].map((n) => n.toString(16).padStart(2, "0")).join("");
}

/** `operation()` within `ms`; a late, failing or missing cache answers `fallback`. */
export async function bounded(operation, ms = CACHE_TIMEOUT_MS, fallback = null) {
  let timer;
  try {
    return await Promise.race([
      Promise.resolve().then(operation),
      new Promise((resolve) => { timer = setTimeout(resolve, ms, fallback); }),
    ]) ?? fallback;
  } catch {
    return fallback;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * A versioned, expiring store of one kind of public answer. Without a store every read
 * misses and every write is skipped. A miss is `undefined`, so a cached empty list counts.
 */
export function makeSourceCache(store, { kind, timeoutMs = CACHE_TIMEOUT_MS, now = Date.now } = {}) {
  return {
    async key(identity) {
      return store ? `source-v${VERSION}:${kind}:${await digest(identity)}` : null;
    },
    async get(key) {
      if (!store || !key) return undefined;
      const entry = await bounded(() => store.get(key, "json"), timeoutMs);
      const at = entry?.at;
      const seconds = Math.min(SOURCE_TTL_SECONDS, entry?.seconds ?? 0);
      if (entry?.version !== VERSION || typeof at !== "number" || at > now() || now() - at >= seconds * 1000) return undefined;
      return entry.value ?? undefined;
    },
    async put(key, value, seconds = SOURCE_TTL_SECONDS) {
      if (!store || !key || value === undefined || value === null) return;
      const kept = Math.max(60, Math.min(SOURCE_TTL_SECONDS, Math.floor(seconds)));
      const entry = JSON.stringify({ version: VERSION, at: now(), seconds: kept, value });
      if (entry.length > MAX_VALUE_CHARACTERS) return;
      await bounded(() => store.put(key, entry, { expirationTtl: kept }), timeoutMs);
    },
  };
}

const stopped = () => Object.assign(new Error("The request is no longer needed."), { name: "AbortError" });

/**
 * One request in flight per key, shared by every caller asking the same while it runs.
 * A caller whose `parent` signal aborts stops waiting at once; the request itself is
 * ended only once no caller still waits, so one lookup's cancellation never fails another.
 * @returns {(key: string, work: (signal: AbortSignal) => Promise<any>, parent?: AbortSignal) => Promise<any>}
 */
export function makeShared() {
  const running = new Map();
  return function shared(key, work, parent) {
    if (parent?.aborted) return Promise.reject(parent.reason ?? stopped());
    let entry = running.get(key);
    if (!entry) {
      const controller = new AbortController();
      const promise = Promise.resolve().then(() => work(controller.signal));
      entry = { controller, promise, waiting: 0 };
      const made = entry;
      const forget = () => { if (running.get(key) === made) running.delete(key); };
      promise.then(forget, forget);
      running.set(key, entry);
    }
    const joined = entry;
    joined.waiting += 1;
    return new Promise((resolve, reject) => {
      let left = false;
      const leave = (settle) => {
        if (left) return false;
        left = true;
        joined.waiting -= 1;
        parent?.removeEventListener("abort", onAbort);
        return settle();
      };
      const onAbort = () => leave(() => {
        if (joined.waiting === 0) {
          if (running.get(key) === joined) running.delete(key);
          joined.controller.abort(parent.reason ?? stopped());
        }
        reject(parent.reason ?? stopped());
      });
      parent?.addEventListener("abort", onAbort, { once: true });
      joined.promise.then(
        (value) => leave(() => resolve(value)),
        (error) => leave(() => reject(error)),
      );
    });
  };
}
