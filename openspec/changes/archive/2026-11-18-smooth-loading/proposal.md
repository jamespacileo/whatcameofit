# Proposal

## Why

The operator reported on 2026-11-17 that the landing page "loads in chunks" and asked for loading that feels smoother on the landing and claim pages, without changing how the landing page looks. Measured on the published site that day: controls a script works (the kind and span fields, the status field, the list tabs, the words to try) were left out of the first paint and appeared once their script ran, moving what sat below them; both faces swapped in over a device font with different widths and line height and a page a reader pressed was fetched only on the press.

The landing page's size (11.5 MB of HTML, 197,603 elements, about 19 day rows in sight) is the larger cause and is not part of this change.

## What Changes

- A control only a script can work holds its place from the first paint and comes into sight when its script is ready. Without scripts it is left out, as before.
- Each face has a fallback: a font already on the device, scaled to the face's widths and line height, measured from the font files.
- A page a reader points at or focuses is fetched before they press.

Nothing changes in how a loaded page looks.

## Capabilities

### Modified Capabilities

- `site-publishing`: how a page comes into sight while it loads.

## Impact

- `site/astro.config.mjs`, `site/src/styles/global.css`, `site/src/pages/index.astro`, `site/src/components/DayList.astro`, `site/src/components/HomeNarrow.astro`, `site/tests/`.
