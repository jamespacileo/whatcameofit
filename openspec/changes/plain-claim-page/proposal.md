# Proposal

## Why

Claim lists now lead with a short name and say each status in plain words (change `plain-claim-lists`), but the claim page they link to does not follow through. It opens with a headline of about twenty words, shows a dashed warning box on 83 of the 84 published claims and nothing about provenance on the rest, and leaves a lay reader to work out the answers to the questions they came with: has this been tested in people, is it approved, what would come next.

Evidence sites such as examine.com title a page by the thing it is about, state who stands behind the page in one constant line, and build the page around the reader's questions. All three fit this site with fixed wording and no model.

## What Changes

- A claim page is titled by its intervention name. The headline stays directly under the title, in full.
- Every claim page carries one provenance line in the same place: how the page was put together, whether a person has checked it, and when the registries were last checked. It replaces the dashed box shown only on unchecked claims.

Out of scope: three fixed questions answered from the status (moved on 2026-11-14 to change `claim-at-a-glance`, which answers them from the records), an evidence snapshot of counts, a follow button or section rail, an on-page status history, the topics directory, the page's `<title>`, share text, cards, `lookup.json`, the embed and the extension. The unchecked notice in `lookup.json` and the extension is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-publishing`: a claim page is titled by the intervention name; every claim page carries a provenance line.

## Impact

- `site/src/pages/[slug].astro`: title block, provenance line in place of the unchecked box.
- `site/src/lib/notices.ts`: provenance wording. `UNCHECKED_NOTE` stays for `lookup.json`.
- `site/src/styles/global.css`, `DESIGN.md`, `GLOSSARY.md`: title and provenance line, recorded in the visual system.
- `site/tests/site.test.mjs`: one test per new scenario; existing claim-page tests that read the `h1` or the unchecked box are updated.
- No export shape change: `intervention.name`, `checked_by_person` and `last_checked_at` are already exported. No schema or seed regeneration.
