# Tasks

## 1. Status glosses

- [x] 1.1 Add `STATUS_GLOSSES` for every status code to `site/src/lib/status.ts` using the wording in design.md, include it in the module-load `assertNeutral` call, and verify the site build type-checks with no missing code
- [x] 1.2 Show the wording table to the operator and record any changed gloss in design.md; verify each gloss claims no more than its `STATUS_MEANINGS` entry
- [x] 1.3 Add tests "Scenario: Status code without a gloss" and "Scenario: Gloss with verdict wording" to `site/tests/site.test.mjs` (every code in the export schema has a gloss; `assertNeutral` throws on a gloss containing "abandoned") and verify they pass
- [x] 1.4 Render the gloss under the label in `StatusCell.astro` and under the status label in the digest of `site/src/pages/[slug].astro`, style it in `global.css`, and add tests "Scenario: Gloss in a list" and "Scenario: Gloss on the claim page"; verify they pass against a built site

## 2. Rows lead with the intervention name

- [x] 2.1 Change the claim cell in `ClaimTable.astro` so the link text is `intervention.name` and the headline is plain text beneath it, with the link stretched over the cell; verify on the built topic page that the link reads the name and the headline is present
- [x] 2.2 Style the name and the two-line clamped headline in `global.css` for desktop and phone widths, and verify in the browser preview at both widths that no row overflows (the site has no dark theme)
- [x] 2.3 Add tests "Scenario: Row for a named intervention" and "Scenario: Two claims for one intervention", update "a topic page marks each row with its status and keeps amber for promises" if its selectors changed, and verify the suite passes
- [ ] 2.4 List the intervention names of all seeded claims, report any over 40 characters or worded as a description to the operator, and verify the list is in the change's PR description

## 3. Topic summary sentence

- [x] 3.1 Add the clause table (singular and plural per code) and the pure `topicSummary` function to `site/src/lib/status.ts` following the five rules in design.md, include every clause in `assertNeutral`, and verify with direct tests for two statuses, one claim, more than four statuses and zero claims
- [x] 3.2 Replace the count-only lede in `site/src/pages/topic/[vertical].astro` with the summary sentence followed by "Newest first.", and add tests "Scenario: Topic with two statuses", "Scenario: Topic with one claim", "Scenario: Topic with more than four statuses" and "Scenario: Summary of a topic with ended trials"; verify they pass and that "Scenario: Vertical with no published claims" still passes with no sentence shown

## 4. Record and check

- [x] 4.1 Record the row pattern, the gloss line and the summary sentence in `DESIGN.md`, and add "gloss" to `GLOSSARY.md` if the term is used in site copy or code; verify both files name the new elements
- [x] 4.2 Run `make check` and verify ruff, ty, pytest and the site build all pass
- [x] 4.3 Open the dementia topic page and one claim page in the browser preview, at desktop and phone widths, and verify the name-led rows, glosses and summary sentence read correctly with no console errors

## Workflow follow-up

- Archive the change after the PR is merged.
