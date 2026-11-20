// The lookup file the site's lookup box and search, and the lookup Worker, read: version 2,
// keyed by pair address (site/src/pages/lookup/2.json.ts). Version 1, /lookup.json, is kept
// only for the released browser extension.

export const LOOKUP_FILE = "/lookup/2.json";
export const LOOKUP_FORMAT = { format: "lookup", format_version: 2 };

/**
 * The lookup file as the box and the Worker hold it: each pair's entry with its page added,
 * and under `headline` and `indication` too, the names their matching and drawing code was
 * written with. Those two go when that code is renamed; the file itself never carries them.
 * A file of another format, or none, reads as no pairs.
 * @param {any} file
 */
export function readLookupFile(file) {
  const ours = file?.format === LOOKUP_FORMAT.format && file?.format_version === LOOKUP_FORMAT.format_version;
  const pairs = {};
  for (const [address, entry] of Object.entries(ours ? file.pairs ?? {} : {})) {
    pairs[address] = { ...entry, page: `/${address}`, headline: entry.title, indication: entry.condition };
  }
  return { ...(ours ? file : {}), articles: ours ? file.articles ?? {} : {}, topics: ours ? file.topics ?? {} : {}, pairs };
}
