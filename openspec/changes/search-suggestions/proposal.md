# Proposal

## Why

On 2026-11-17 the operator asked for the search box to complete what a reader types, across topics, articles, clinical trials, treatments and indications. A critique of the phone view the same day had found that typing was the only way to ask, and that a first-time reader had nothing to choose from. Four options were mocked from real rows of the published export (`.impeccable/mocks/search-autocomplete/`); the operator chose "A", grouped by kind.

## What Changes

- While words are typed in the box, rows are offered under it in five kinds, each under its name and always in the same order: topics, treatments, conditions, reports, trials on record. Two rows of a kind at most.
- A row says what it names with the typed words in bold, and in grey how much is behind it or where its claim stands. An outlet's title keeps its quotation marks and the heading face.
- A topic opens its page; a treatment and a report open their claim; a condition and a trial search for themselves. A last row sends the words as typed.
- Up and down keys move through the rows, Enter takes the chosen one, Escape closes them. With no row chosen, Enter searches exactly as before.
- One letter offers nothing. A pasted address offers nothing and is looked up at once, as before.
- The order of rows is by rules a reader could check (`site/src/lib/suggest.ts`): no model and no score.
- Reports and trials come from the search detail file, which the box now asks for the first time it is typed in, not on the first search.

## Impact

- `site/src/lib/suggest.ts` (new, pure) and its tests; `site/src/components/Lookup.astro`; `site/src/styles/global.css`.
- One more request (`/search-detail.json`) for a reader who types in the box and does not search.
- No new data: every row comes from `lookup.json` and `search-detail.json`, which are already published.
