# Proposal

## Why

On 2026-11-17 the operator asked for the home page to feel more interesting while keeping the minimal look of the research-summary site it follows, and for the serif of the claim page there too. Three variants of the opening were mocked from the page's own markup and CSS and the published export (`.impeccable/mocks/home-variants/index.html`); the operator chose "A".

## What Changes

- The home page's title and section headings are set in the heading face (Newsreader), which the home page now loads ahead of need as a claim page does.
- Under the box, one published claim is drawn as the site's idea in one look: what an outlet reported and when, how many whole years ago that was, and where the claim stands on the records, in the well a claim page shows its status in. The card leads to the claim.
- The claim is the site's example (`exampleClaim`), chosen by rule and never by hand, as on the about page and the extension page.
- The outlet's title is a quotation with the outlet named. The status is the site's label with its place on the path. "No signal" is said as the site says it.
- Below 40rem the card is not drawn, so a row of the list still starts on the first screen.
- The day-by-day list under it is brought into line (the operator's request of 2026-11-17): its name and each row's headline in the heading face, and one control, "Filter", in place of the row of four fields. The control opens a panel holding the same four fields with their names, says in their words what narrows the list, and takes one line on a phone where the fields took two. What each field does, and how a pick is kept in the address, is unchanged.

Not decided: whether the home page should pick its claim by another rule (the longest time since the report, say); the heading face on the guide, the about page and the link-preview cards.

## Capabilities

### Modified Capabilities

- `site-publishing`: the home page's opening.

## Impact

- `site/src/components/ThenNow.astro`, `site/src/lib/then-now.ts`, `site/src/pages/index.astro`, `site/src/layouts/Base.astro`, `site/src/styles/global.css`, `site/tests/then-now.test.mjs`, `site/tests/site.test.mjs`, `DESIGN.md`.
