# Proposal

## Why

A design review on 2026-11-12 (`.impeccable/critique/`) found the link-preview card to be the most shareable thing the site has, and the pages around it less pointed than the card. The operator chose to work on shareability first, with a plain count of approvals and no added framing.

## What Changes

- On the card, the year a claim was promised by sits on pale amber with a dashed rule, the colour that means "promised" everywhere else on the site. Claims with no dated promise keep the card they had.
- The claim page's "Pass it on" section shows the square card itself beside the sentence, in place of a paragraph describing the images, and opens with one line saying what the section is for.
- When a pasted link is an article the site tracks, the home page answers with the claim's status the way the claim page does: the status in words, its place on the path, the no-signal note, what the status means, and a link to the records.
- The lookup file carries each claim's place on the path so the answer can be drawn without a second request.
- The approved-claims page and each year page state how many of their claims have an approval on record, as a count and nothing else.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sharing`: the promised year on the card; the card shown on the claim page.
- `site-publishing`: the lookup's answer for a tracked article; the approval counts.

## Impact

- **Site:** `site/src/lib/card.ts`, `site/src/lib/card-image.ts`, `site/src/pages/[slug].astro`, `site/src/pages/index.astro`, `site/src/pages/lookup.json.ts`, `site/src/pages/it-happened.astro`, `site/src/pages/year/[year].astro`, `site/src/styles/global.css`.
- **Lookup file:** two added fields, `places` and each claim's `place`. Nothing is removed, so the browser extension reads it as before.
- **Wording risk:** a count of approvals could be read as a score for a field of medicine. It is worded as a count of records ("Approvals on record: 1 of 3"), with no adjective and no comparison.
- **Not in this change:** motion, the not-found page's wording, the orientation line for readers arriving cold, and the review's other findings.
