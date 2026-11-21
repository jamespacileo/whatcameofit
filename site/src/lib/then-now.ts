// The home page's one pair, then and now (the claims site's lib/then-now, on pairs): the words
// for how long ago its first registry record was. Whole years only, counted to the day the
// bundle was made; nothing is said of a first record under a year old.

/** "5 years on", "1 year on", or null when the two days are under a year apart. */
export function yearsOn(then: string, now: string): string | null {
  const from = new Date(then.slice(0, 10) + "T00:00:00Z");
  const to = new Date(now.slice(0, 10) + "T00:00:00Z");
  let years = to.getUTCFullYear() - from.getUTCFullYear();
  const before = to.getUTCMonth() < from.getUTCMonth() || (to.getUTCMonth() === from.getUTCMonth() && to.getUTCDate() < from.getUTCDate());
  if (before) years -= 1;
  if (years < 1) return null;
  return `${years} ${years === 1 ? "year" : "years"} on`;
}
