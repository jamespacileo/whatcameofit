# Tasks

## 1. Title by intervention name

- [ ] 1.1 In `site/src/pages/[slug].astro` make the `h1` the intervention name and move the headline to a paragraph directly under it carrying `data-pagefind-meta="title"`; verify on a built claim page that the `h1` reads the name and the headline follows it
- [ ] 1.2 Style the heading and the headline paragraph in `site/src/styles/global.css`, keeping the long-title rule, and verify in the browser preview at desktop and phone widths, with the longest published name, that nothing overflows
- [ ] 1.3 Add tests "Scenario: Page of a named intervention" and "Scenario: Search result for a claim" to `site/tests/site.build-test.mjs`, update "Scenario: Reader opens a claim" and "Scenario: Search by intervention name" if they read the `h1`, and verify the suite passes

## 2. Provenance line

- [ ] 2.1 Add the provenance wording to `site/src/lib/notices.ts` and render the line under the headline in place of the `.unchecked` box, leaving `UNCHECKED_NOTE` and `lookup.json` unchanged; verify a built unchecked page and a built checked page each show the line with the right wording
- [ ] 2.2 Remove the `.unchecked` styles that no page uses any more and style `.provenance` in `global.css`; verify with a search that no template references `.unchecked` and that the line wraps cleanly on a phone
- [ ] 2.3 Add tests "Scenario: Claim no person has checked", "Scenario: Claim a person has checked" and "Scenario: Export with no check date", and verify "Scenario: Preview build" and the `lookup.json` assertions still pass

## 4. Record and check

- [ ] 4.1 Record the name heading and the provenance line in `DESIGN.md`, update principle 1 if the top of the page it describes has changed, and add any new term used in site copy to `GLOSSARY.md`; verify both files name the new elements
- [ ] 4.2 Run `make check` and verify ruff, ty, pytest, the site tests, the site build and the extension tests all pass
- [ ] 4.3 Open one unchecked claim page and the approved-claims page's first claim in the browser preview and verify the heading and provenance line read correctly

## Workflow follow-up

- Archive the change after the PR is merged.
