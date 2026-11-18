# Proposal

## Why

On 2026-11-16 the operator asked for a claim page with fewer blocks of text in sight ("many blocks of text like paragraphs could be collapsed by default") and approved a mock (`.impeccable/mocks/claim-examine/index.html`) with a filled side column in the band, a clamped summary and notes on request. On 2026-11-17 the operator asked for the remaining parts of that mock to be built.

## What Changes

- A claim's summary is held to three lines, and the grey note of "At a glance", trials, registry records, papers and organisations to one line, each with a "More" control that appears only when there is more. Nothing is removed from the page: with no script, for a screen reader and on paper the text is whole.
- The notes of "The record in brief" and of the reported statements stay whole: they say the answers and statements are not about the treatment and are not advice.
- "Pass it on" and "Check again later" start folded on every width, and the registry records section starts folded when it holds only possible records, which count for nothing. A link into a folded section still opens it.
- The band's side column on a wide screen holds the topic's drawing, large, as decoration.

Decided by the assistant under the operator's instruction: which notes stay whole, and that the second Follow offer under the summary stays, because its sentence says the list is kept in this browser only.

## Capabilities

### Modified Capabilities

- `site-publishing`: clamped summary and notes, sections folded at first, the band's side drawing.

## Impact

- `site/`: `scripts/clamps.ts`, `TopicDrawing.astro` (taken out of `TopicChip.astro`), `pages/[slug].astro`, `Glance.astro`, `Organisations.astro`, `layouts/Base.astro`, styles, a test.
- `DESIGN.md`.
