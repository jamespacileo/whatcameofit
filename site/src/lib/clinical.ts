// The clinical pages' shared words: a category's address and the credit's edition.

export const categoryPath = (identifier: string): string => `/clinical/${identifier}`;

/** "MeSH 2026", or each year when the records were read from more than one. */
export function meshEdition(years: string[]): string {
  if (years.length === 0) return "MeSH";
  if (years.length === 1) return `MeSH ${years[0]}`;
  return `MeSH ${years.slice(0, -1).join(", ")} and ${years[years.length - 1]}`;
}
