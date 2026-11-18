# Proposal

## Why

On 2026-11-17 the operator asked for a critique of the claim page against the same research-summary site that `band-tones` followed, with the same notes: a top section whose tones give hierarchy, and a status card that reads with the title as one block. The critique (`.impeccable/critique/2026-11-17T08-06-55Z__site-src-pages-slug-astro.md`) measured what `band-tones` built: the three navies differ by 1.2:1 and 1.27:1, the status card stands outside the main column's tone, on the dark side, and a sentence-long title (28.9px) is smaller than the status label (29.75px). The operator chose the band as the first thing to fix.

## What Changes

- The main tone is one surface as wide as the sheet below it, and the title and the status card both stand on it. The card ends where the sheet's words end, as the title starts where they start.
- The tones are a clear step apart: `--band-main` is `#163a6c` (1.36:1 against the navy at the sides), and the status card is a well, `--band-card` `#081b36`, darker than the navy (1.52:1 against the surface it stands on). The card is no longer the lightest tone; it is the darkest, so its label has the strongest contrast in the band.
- Beside the card a sentence-long title is set at `1.95rem` and the status label at `1.5rem`, so the title leads.
- Below 68rem the band is one surface on `--band-main`, a step above the masthead, with the well on it. A topic page's band takes the same surface.
- On paper nothing changes.

This reverses one decision of `band-tones`: the card was the lightest tone, on the side navy. The navy itself, the masthead and the rule that no block is drawn in the accent are unchanged: `--band-main` stays darker than the accent.

Order: this change modifies a requirement that `band-tones` adds, so `band-tones` is archived first.

Out of scope: the order of the band's parts on a phone, the card's contents, the sheet.

## Capabilities

### Modified Capabilities

- `site-publishing`: the record band's surfaces, tones and the sizes of its title and status label.

## Impact

- `site/src/styles/global.css`, `DESIGN.md`.
