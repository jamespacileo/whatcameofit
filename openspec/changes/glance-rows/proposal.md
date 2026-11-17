# Proposal

## Why

On 2026-11-17 the operator asked for "At a glance" to be given the research-summary site's treatment and to feel simpler, with nothing lost. Each of its cells carried up to six parts in sight: a label, a value, a score, the source's words, a disclosure line and a source. Three variants were mocked from the page's own markup and CSS (`.impeccable/mocks/glance-variants/index.html`); the operator chose "A", rows that open.

## What Changes

- "At a glance" is one list in the pattern of "The record in brief". A closed row is its label and its value on one line, the value's other names under it, and a chevron.
- The row opens to the source's definition, whole and unlabelled, ending in a quiet pill that names the source and opens it in a new tab; then labelled parts: the match, where the claim's term is filed, the term as its source names it with its credit, and why it matched.
- **The score moves.** Until now a term's score stood on the row, in sight, as `score-chip` requires of every score. By the operator's instruction of 2026-11-17 a score in the high band, and how a term was found, are said where the row opens. A score below the high band stays in sight on the closed row. This is an exception to `score-chip`'s "in sight, with nothing to press" for term matches in "At a glance" only; every other score on the page is unchanged.
- **The source's name moves** with it: it is the pill at the end of the source's words and the credit under them. Every source is still credited in the page's footer.
- The row's press is a button with `aria-expanded`, as a trial's row is. With no script, and on paper, every row is open. A link from the band to a term opens it.
- The claim's own facts are rows of the same list.

Nothing shown before is dropped. This replaces the two-column cells that `band-tones` gave "At a glance" on a wide screen. Two group names ("The claim", "On record") were built and removed the same day.

## Capabilities

### Modified Capabilities

- `site-publishing`: the layout and disclosure of "At a glance" on a claim page.

## Impact

- `site/src/components/Glance.astro`, `site/src/scripts/folds.ts`, `site/src/styles/global.css`, `site/tests/site.test.mjs`, `DESIGN.md`.
