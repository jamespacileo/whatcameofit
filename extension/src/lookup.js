// Decides what the popup shows. Pure: no browser, network or clock in here.

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
 */
export function stateFor(key, loaded) {
  if (key === null) return { kind: "no-page" };
  const { index, savedAt } = loaded;
  if (index === null) return { kind: "unreachable" };

  const claims = (index.articles[key] ?? []).map((slug) => index.claims[slug]).filter(Boolean);
  if (claims.length === 0) return { kind: "untracked", savedAt };
  return {
    kind: "tracked",
    claims,
    notices: index.notices ?? [],
    lastChecked: index.last_checked ?? null,
    savedAt,
  };
}
