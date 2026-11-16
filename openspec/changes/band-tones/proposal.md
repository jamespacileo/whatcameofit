# Proposal

## Why

On 2026-11-16 the operator compared a claim page with a research-summary site and asked for three things at its top: a band with more than one tone, "a different hue with a soft contrast that gives visual hierarchy"; a status card in a tone of the band, so the card and the title read as one block; and "At a glance" spread over two columns on a wide screen. The mock is `.impeccable/mocks/claim-examine/index.html`; the operator approved it and left the remaining decisions to the assistant.

## What Changes

- The record band has three tones: the navy at its sides, a lighter main column (`--band-main`) that runs from the masthead into the sheet below it, and the status card a step lighter still (`--band-card`) with a faint blue edge. The card is no longer white on the light page. The same in both themes.
- Inside the card the page's colours take their on-navy values: white lettering, the lifted blue for the status label, links and the marker, pale blue for secondary text. A panel that opens out of the card keeps the page's own colours.
- The title and the page actions start where the sheet's words start.
- From 60rem, "At a glance" is two columns of cells, each a label over its value. A cell whose card is open takes the full width.
- On paper nothing changes: the band and the card have no fill.

This replaces what `DESIGN.md` said of the band ("the one solid navy block", "the digest panel as a white card") and of "At a glance" (a label at the left and its value at the right) on a wide screen.

Out of scope: the band's side column stays empty; the summary, the notes and the sections keep their current folding.

## Capabilities

### Modified Capabilities

- `site-publishing`: the record band's tones, the status card's ground, and the layout of "At a glance" on a wide screen.

## Impact

- `site/src/styles/global.css`, `DESIGN.md`.
