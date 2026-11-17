# Proposal

## Why

After `band-well` the operator asked for mocks of the claim page's band that stand closer still to the research-summary site it follows, and for a serif on the headings. Three variants were mocked from the page's own markup and CSS (`.impeccable/mocks/hero-serif/index.html`), with a switch between four heading faces. On 2026-11-17 the operator chose "B with Newsreader".

## What Changes

- A second family, the heading face `--display` (Newsreader Variable, self-hosted), sets the title on a record band and the section headings of a claim page and a topic page. The status label, the records and every other page stay in Figtree. The face is preloaded on those pages only.
- The band's title is larger and takes one of three sizes by the headline's length (up to 70, up to 110, over 110 characters).
- The topic is a path ("Topics", then the topic's name) where the topic chip stood.
- The summary stands under the title in the band, held to five lines with "More". Below 40rem it is not drawn there and the sheet opens with it, as before; from 40rem the sheet's copy is not drawn.
- The status card's heading, "Where it stands", is in sight as a tab on the card. Its records are rows with a mark each.
- The band's actions are pills filled with the card's tone.
- The topic's drawing in the band's side column is large and has no disc.

This replaces what `DESIGN.md` said under Type ("One family"), under "Band side", and the topic chip's place on a claim's band.

Not done, and not decided: the heading face on the home page, the guide, the about page and the link-preview cards, which keep Figtree; the order of the band's parts on a phone.

Order: this change builds on `band-well`, which is archived first.

## Capabilities

### Modified Capabilities

- `site-publishing`: a record page's heading face, and the parts of a claim's band.

## Impact

- `site/package.json` (`@fontsource-variable/newsreader`), `site/src/layouts/Base.astro`, `site/src/pages/[slug].astro`, `site/src/styles/global.css`, `DESIGN.md`, `.impeccable/surfaces/site-src-pages-slug-astro.md`.
