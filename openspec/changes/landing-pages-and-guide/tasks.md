## 0. Before building

- [x] 0.1 Operator confirms the brief in `design.md` and answers the six decisions at its end (2026-11-14)

## 1. Extension page

- [x] 1.1 Add the two store addresses to the site's settings, unset by default; verify the site builds with no `/extension` page and no link to one
- [x] 1.2 Run the structure round for the first viewport (`/impeccable` on the page) and record the chosen direction in a surface brief
- [x] 1.3 Draw the popup's tracked-claim answer in the page from the export, sharing the popup's wording; verify it matches the popup states page for the same claim
- [x] 1.4 Write the reads, sends and keeps table and the permissions list from the privacy page; verify every row against `privacy.astro` and the extension's manifest
- [x] 1.5 Install controls: the reader's browser first with scripting on, both without; verify with one store set, both set, and at 375 px
- [x] 1.6 Correct the extension lines in `PRODUCT.md` (what is sent, store status)

## 2. Guide

- [x] 2.1 Load entry files at build and check them in pure functions (a status without an entry, a research entry without a source, a missing related entry, verdict or advice wording); verify with site tests, one passing and one refused case each
- [x] 2.2 Entry page and index page; verify at 375 and 1280 px, with a long title, no live claim, and four sources
- [x] 2.3 Write the ten status entries from `status.ts` and the method page; verify each cites the rule it rests on
- [x] 2.4 Link the entries from the claim page's status panel, the no-signal panel, the unchecked notice and the method page's status list
- [x] 2.5 Write the eight entries on the site's own words from `GLOSSARY.md`
- [x] 2.6 Write the nine entries on how research is recorded, each from a regulator, registry or publisher source read on the day; record the day checked
- [x] 2.7 Add the entries to the sitemap and mark each up as a defined term
- [ ] 2.8 Operator reads the entries and sets each one checked (all 27 are published with `checked: false`; set `checked: true` in an entry's file in `site/src/guide` once read)

## 3. Topic pages for communities

- [x] 3.1 Add the "what this is" line; move Share and the feed under the summary; add "Copy sentence"; verify the copied text and the order at 375 px
- [x] 3.2 Build the topic card from the card description the claim cards use; verify with one claim, seven claims and a topic with no drawing
- [x] 3.3 End the page with "Not here?" where a suggestion address is set (done by the `invite-back` change: a topic page ends with "Another headline?" and the link to suggest one)

## 4. About page

- [x] 4.1 Read Dumas-Mallet et al. (2017) and state its finding in the site's words, with the link; record the day checked
- [x] 4.2 Run the structure round for the first viewport and record the chosen direction (three directions recorded in `.impeccable/surfaces/site-src-pages-about-astro.md`; the brief's lead is built; the operator has not yet chosen between them)
- [x] 4.3 Build the page with its example claim from the export and the lookup box as its last section; verify it holds no number the export lacks
- [ ] 4.4 Operator words "Who runs it" (the page names the operator as the privacy page does; the sentence on funding is `WHO_RUNS_IT.funding` in `site/src/lib/about.ts`, unset, and nothing is drawn for it until it is set)

## 5. Audience pages

- [x] 5.1 One template for the three pages
- [x] 5.2 Journalists: search that shows the chosen claim's embed and snippet; verify with a tracked claim, an unchecked claim and no result
- [x] 5.3 Clinicians: the lookup with the sentence to copy in its answer; verify a printed claim page from its link
- [x] 5.4 Researchers: the download with licence, build day and fields

## 6. Ways in and records

- [x] 6.1a The extension link in the footer, on the home page and at the end of a claim page, drawn only when the extension page is published
- [x] 6.1b Footer links for the guide, the about page and the audience pages
- [x] 6.2a Update `PRODUCT.md` and `DESIGN.md` for the extension page
- [x] 6.2b Update `PRODUCT.md` capabilities and `DESIGN.md` components for each further part as it ships
- [x] 6.3 Add the audience pages to "Where to say it" in `docs/launch.md`
- [x] 6.4 Verify `make check` passes
- [x] 6.5 Run the design detector over the new pages
