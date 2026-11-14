// Decides what the popup shows. Pure: no browser, network or clock in here.

// The saved lookup file's format. Refresh pre-automatic-lookup caches once so an
// upgrade sees current service settings. The background check writes the same shape.
export const CACHE_VERSION = 2;

/** Whether a copy saved at `savedAt` may still be used without asking the site again. */
export function isFresh(savedAt, now, maxAge) {
  return typeof savedAt === "number" && now - savedAt < maxAge;
}

/**
 * @param {string | null} key the current page's address in comparison form, or null
 *   when the tab is not a web page
 * @param {{ index: object | null, savedAt: number | null }} loaded the lookup file, and
 *   when it came from the saved copy because the site could not be reached, the time
 *   that copy was saved
 * @param {string | null} [siteKey] the site's own address in comparison form
 */
export function stateFor(key, loaded, siteKey = null) {
  if (key === null) return { kind: "no-page" };
  const { index, savedAt } = loaded;
  if (index === null) return { kind: "unreachable" };

  // One of the site's own pages is never a news report to search for: a claim's page
  // shows that claim, and any other page asks for an article.
  const own = siteKey !== null && (key === siteKey || key.startsWith(`${siteKey}/`) || key.startsWith(`${siteKey}?`));
  const path = own ? key.slice(siteKey.length).replace(/\?.*$/, "") : null;
  const claims = own
    ? Object.values(index.claims).filter((claim) => claim.page === path)
    : (index.articles[key] ?? []).map((slug) => index.claims[slug]).filter(Boolean);
  if (own && claims.length === 0) return { kind: "no-page" };
  // `live` is where the site answers a registry search, when it offers one.
  if (claims.length === 0) return { kind: "untracked", savedAt, live: index.live ?? null };
  return {
    kind: "tracked",
    ...(own ? { own: true } : {}),
    claims,
    // How many places the path has; each claim carries its own place on it.
    places: index.places ?? null,
    notices: index.notices ?? [],
    lastChecked: index.last_checked ?? null,
    savedAt,
  };
}
