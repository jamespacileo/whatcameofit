// Which rows of a long list one page holds. Pure: the pager's script and the pages
// that draw the first page both read it.

export interface Page {
  /** The page shown, from 1. A page past the end is the last page. */
  page: number;
  pages: number;
  /** The first and last row shown, counted from 1. Both 0 for an empty list. */
  from: number;
  to: number;
}

export function pageOf(total: number, size: number, wanted: number): Page {
  const pages = Math.max(1, Math.ceil(total / size));
  const page = Number.isInteger(wanted) ? Math.min(Math.max(wanted, 1), pages) : 1;
  if (total === 0) return { page: 1, pages: 1, from: 0, to: 0 };
  return { page, pages, from: (page - 1) * size + 1, to: Math.min(page * size, total) };
}

/** "11–20 of 104 headlines"; a list that fits one page has no range to say. */
export function pageLine(at: Page, total: number, one: string, many: string): string {
  const noun = total === 1 ? one : many;
  if (at.pages === 1) return `${total} ${noun}`;
  return `${at.from}–${at.to} of ${total} ${noun}`;
}
