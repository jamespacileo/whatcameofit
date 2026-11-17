# Proposal

## Why

On 2026-11-17 the operator asked for "At a glance" to be given the research-summary site's treatment and to feel simpler, with nothing lost. Each of its cells carried up to six parts in sight: a label, a value, a score, the source's words, a disclosure line and a source. Three variants were mocked from the page's own markup and CSS (`.impeccable/mocks/glance-variants/index.html`); the operator chose "A", rows that open.

## What Changes

- "At a glance" is one list in the pattern of "The record in brief". A term is one line: its label, its value with its other names, its score, and whose term it is. The line opens to whose words they are, the source's definition whole, where the claim's term is filed, and the card's credit and reasons.
- The source's name stays in sight on the closed row. Nothing shown before is dropped; the source's words and the filing are one press away.
- The row's press is a button with `aria-expanded`, as a trial's row is, not a `details`: the score chip is a control of its own and stands over the press. With no script, and on paper, every row is open. A link from the band to a term opens it.
- The claim's own facts are rows of the same list.

This replaces the two-column cells that `band-tones` gave "At a glance" on a wide screen.

## Capabilities

### Modified Capabilities

- `site-publishing`: the layout and disclosure of "At a glance" on a claim page.

## Impact

- `site/src/components/Glance.astro`, `site/src/scripts/folds.ts`, `site/src/styles/global.css`, `site/tests/site.test.mjs`, `DESIGN.md`.
