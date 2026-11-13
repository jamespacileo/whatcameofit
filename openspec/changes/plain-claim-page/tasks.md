# Tasks

## 1. Title by intervention name

- [ ] 1.1 In `site/src/pages/[slug].astro` make the `h1` the intervention name and move the headline to a paragraph directly under it carrying `data-pagefind-meta="title"`; verify on a built claim page that the `h1` reads the name and the headline follows it
- [ ] 1.2 Style the heading and the headline paragraph in `site/src/styles/global.css`, keeping the long-title rule, and verify in the browser preview at desktop and phone widths, with the longest published name, that nothing overflows
- [ ] 1.3 Add tests "Scenario: Page of a named intervention" and "Scenario: Search result for a claim" to `site/tests/site.test.mjs`, update "Scenario: Reader opens a claim" and "Scenario: Search by intervention name" if they read the `h1`, and verify the suite passes

## 2. Provenance line

- [ ] 2.1 Add the provenance wording to `site/src/lib/notices.ts` and render the line under the headline in place of the `.unchecked` box, leaving `UNCHECKED_NOTE` and `lookup.json` unchanged; verify a built unchecked page and a built checked page each show the line with the right wording
- [ ] 2.2 Remove the `.unchecked` styles that no page uses any more and style `.provenance` in `global.css`; verify with a search that no template references `.unchecked` and that the line wraps cleanly on a phone
- [ ] 2.3 Add tests "Scenario: Claim no person has checked", "Scenario: Claim a person has checked" and "Scenario: Export with no check date", and verify "Scenario: Preview build" and the `lookup.json` assertions still pass

## 3. Three questions answered by rule

- [ ] 3.1 Show the wording table in design.md to the operator, record any changed answer there, and verify each answer claims no more than its `STATUS_MEANINGS` entry and none predicts or advises
- [ ] 3.2 Add `STATUS_ANSWERS` and the shared no-prediction sentence to `site/src/lib/status.ts`, include every string in the module-load `assertNeutral` call, and verify the site build type-checks with no missing code or question
- [ ] 3.3 Render the "In plain words" section between the facts row and the timetable, with the counted-trials sentence linking to the matched records where the status rests on trials; verify on built pages for a preclinical, a Phase 2 and an approved claim that all three answers appear
- [ ] 3.4 Style the question list in `global.css` and verify in the browser preview at desktop and phone widths that it reads as three short answers with no overflow and no console errors
- [ ] 3.5 Add tests for the scenarios "Claim with no trial on record", "Claim in a mid-stage trial", "Approved claim", "Next step is not a prediction", "Claim whose trials ended early", "Status code without answers" and "Answer with verdict wording", and verify they pass

## 4. Record and check

- [ ] 4.1 Record the name heading, the provenance line and the question list in `DESIGN.md`, update principle 1 if the top of the page it describes has changed, and add any new term used in site copy to `GLOSSARY.md`; verify both files name the new elements
- [ ] 4.2 Run `make check` and verify ruff, ty, pytest, the site tests, the site build and the extension tests all pass
- [ ] 4.3 Open one unchecked claim page and the approved-claims page's first claim in the browser preview and verify the heading, provenance line and answers read correctly

## Workflow follow-up

- Archive the change after the PR is merged.
