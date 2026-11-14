# Tasks

## 1. Line rules

- [ ] 1.1 Show the two rule tables in design.md to the operator, record any changed wording or dropped rule there, and verify no line judges, predicts or advises
- [ ] 1.2 Add `site/src/lib/glance.ts` with `glance(claim)` returning the "On record" and "Not on record" line codes with their values and link targets, classing every `TrialState` value as running, completed or other; verify it type-checks and takes no clock or network
- [ ] 1.3 Add the wording per line code beside the status wording, reuse the comparator wording of `site/src/lib/trial-facts.ts`, and include every string in the module-load `assertNeutral` call; verify the build fails when a string is given the word "abandoned"
- [ ] 1.4 Add tests to `site/tests/site.test.mjs` for "Claim with completed trials", "Largest trial with a comparison group", "Results posted", "Papers on record", "Trial with no stated enrolment", "No trial running", "No results posted", "No comparison group", "Nothing absent by rule", "Approval and phase are not repeated" and "Line with verdict wording"; verify they pass

## 2. At a glance section

- [ ] 2.1 Add `site/src/components/Glance.astro` and render it in `site/src/pages/[slug].astro` after the follow offer and before the facts row, with `id="glance"`, `data-pagefind-ignore` and the one-line note; verify on the built Tourette claim page that both lists appear and each counting line links to its section
- [ ] 2.2 Style the two lists in `site/src/styles/global.css` (hairline and solid markers, dashed outline and hollow markers, no status colour, stacked under 40rem); verify in the browser preview at desktop and phone widths that nothing overflows at 320 pixels and there are no console errors
- [ ] 2.3 Add the test "Claim with no trial and no paper" and verify a claim with neither has no section and no placeholder

## 3. Row of section links

- [ ] 3.1 Add `site/src/components/SectionLinks.astro`, add `id="background"` to the background heading, and render the row under the follow offer with counts from the arrays the sections render; verify on a built page that each link lands on its section and the reached-by-link highlight shows
- [ ] 3.2 Style the row with the existing pill style, one sideways-scrolling row with faded ends under 40rem, each link 44 pixels tall, hidden on paper; verify in the browser preview at 320 pixels that every link can be reached and the page is not widened
- [ ] 3.3 Add tests "Claim with trials and papers", "Claim with no papers" and "Narrow screen", and verify they pass

## 4. Record and check

- [ ] 4.1 Record the "At a glance" section and the row of section links under Components in `DESIGN.md`, add "on record" and "not on record" to `GLOSSARY.md` if site copy now uses them as terms, and verify both files name the new elements
- [ ] 4.2 Run `make check` and verify ruff, ty, pytest, the site tests, the site build and the extension tests all pass
- [ ] 4.3 Open the Tourette claim, one preclinical claim and one approved claim in the browser preview and verify the lines match the trials and papers listed lower on each page

## Workflow follow-up

- Archive the change after the PR is merged.
