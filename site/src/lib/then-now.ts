// The home page's one claim, reported and on record (openspec home-then-now): the words
// for how long ago the report was. Whole years only, counted to the day the registries
// were last checked; nothing is said of a report under a year old.

/** "5 years on", "1 year on", or null when the report is under a year old. */
export function yearsOn(reported: string, checked: string): string | null {
  const from = new Date(reported.slice(0, 10) + "T00:00:00Z");
  const to = new Date(checked.slice(0, 10) + "T00:00:00Z");
  let years = to.getUTCFullYear() - from.getUTCFullYear();
  const before =
    to.getUTCMonth() < from.getUTCMonth() ||
    (to.getUTCMonth() === from.getUTCMonth() && to.getUTCDate() < from.getUTCDate());
  if (before) years -= 1;
  if (years < 1) return null;
  return `${years} ${years === 1 ? "year" : "years"} on`;
}
