// How the trial listing is cut into the files a reader fetches, and how a reader finds
// the one that holds a registry number. Plain JavaScript: the build, the search box and
// the tests read this one file. Behaviour: openspec trial-pages.

// About how large one part is before compression. A registry number costs a reader one
// part; Cloudflare refuses any single file over 25 MiB.
export const PART_BYTES = 1024 * 1024;
// A listing of this many parts or fewer is searched for words as soon as a reader
// searches. A larger one is fetched whole only when the reader asks for it.
export const PARTS_SEARCHED_AT_ONCE = 2;

/**
 * The listing's rows in registry-number order, cut into parts of about `bytes` each.
 * Every row is in exactly one part, and no part is empty.
 * @returns {{ name: string, first: string, last: string, trials: unknown[][] }[]}
 */
export function splitListing(rows, bytes = PART_BYTES) {
  const ordered = [...rows].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const cut = [];
  let held = [];
  let size = 0;
  for (const row of ordered) {
    const length = JSON.stringify(row).length + 1;
    if (held.length && size + length > bytes) {
      cut.push(held);
      held = [];
      size = 0;
    }
    held.push(row);
    size += length;
  }
  if (held.length) cut.push(held);
  const width = Math.max(2, String(Math.max(0, cut.length - 1)).length);
  return cut.map((trials, at) => ({
    name: String(at).padStart(width, "0"),
    first: trials[0][0],
    last: trials.at(-1)[0],
    trials,
  }));
}

/** The part of a listing's manifest that would hold this registry number, or null. */
export function partFor(manifest, id) {
  const wanted = String(id).toUpperCase();
  return (manifest?.parts ?? []).find((part) => part.first <= wanted && wanted <= part.last) ?? null;
}
