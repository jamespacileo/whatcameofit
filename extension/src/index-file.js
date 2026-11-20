// The lookup file as the extension fetches, saves and reads it. Since the site was keyed by
// pair (openspec pairs-site, task 4.10), the extension asks for version 2, /lookup/2.json,
// and falls back to version 1, /lookup.json, where a site has not built version 2 yet.
// Either is read into one shape: every pair under `pairs`, by its address, with the page,
// headline and indication the popup was written with (lookup-file.js, copied from the site).
import { readLookupFile } from "../../site/src/lib/lookup-file.mjs";

/** Where the lookup file is asked for, in order: version 2, then version 1. */
export const INDEX_PATHS = ["/lookup/2.json", "/lookup.json"];

/**
 * A lookup file of either version, as the popup and the background check read it.
 * @param {any} file the file as fetched or saved, or null
 */
export function readIndex(file) {
  if (!file || typeof file !== "object") return null;
  if (file.format === "lookup") return readLookupFile(file);
  // Version 1: its `claims` are already pairs by address, in the popup's own words.
  const { claims, ...rest } = file;
  return { ...rest, articles: file.articles ?? {}, pairs: claims ?? {} };
}

/**
 * Fetches the lookup file: version 2, or version 1 when the site answers 404 for it.
 * An ETag saved for the same address is sent, and a 304 answers with the saved file.
 * @param {(url: string, options?: object) => Promise<Response>} fetch
 * @param {string} siteUrl
 * @param {{ saved?: { file?: any, path?: string, etag?: string | null } | null, signal?: AbortSignal }} [options]
 * @returns {Promise<{ file: any, path: string, etag: string | null }>}
 */
export async function fetchIndex(fetch, siteUrl, { saved = null, signal } = {}) {
  for (const path of INDEX_PATHS) {
    const etag = saved?.path === path && typeof saved.etag === "string" ? saved.etag : null;
    const response = await fetch(`${siteUrl}${path}`, {
      cache: "no-store", ...(signal ? { signal } : {}), ...(etag ? { headers: { "If-None-Match": etag } } : {}),
    });
    if (response.status === 304 && etag) return { file: saved.file, path, etag };
    if (response.status === 404 && path !== INDEX_PATHS.at(-1)) continue;
    if (!response.ok) throw new Error(`status ${response.status}`);
    return { file: await response.json(), path, etag: response.headers?.get("ETag") ?? null };
  }
  throw new Error("no lookup file");
}
