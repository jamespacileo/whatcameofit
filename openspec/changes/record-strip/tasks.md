# Tasks

## 1. Strip data

- [x] 1.1 Add a pure module in `site/src/lib` that returns, for one exported claim, the axis start and the last-checked day, the strip's marks (kind and position as a fraction of the axis) and its counts (trials, trials with results posted). Verify: `site/tests/record-strip.test.mjs` covers records before and after a report, a report with nothing else, a promise with no date, a promise after the last check, and 79 records.
- [x] 1.2 Add the shared axis start: earliest dated record year among published claims, floored to a multiple of five. Verify: a test with fixture claims dated 2006 and 2017 returns 2005.
- [x] 1.3 Add to `row-sentences.ts` the base sentence used when no other sentence applies, and the counts line wording, both under the existing neutrality checks. Verify: `site/tests/row-sentences.test.mjs` covers the base sentence, "0 trials", and a build-failing verdict word.
- [x] 1.4 Add a test that each sentence's subject has a matching mark or count (first trial year, results posted, regulator's decision). Verify: the test fails when a mark is removed from the fixture's expected output.

## 2. Strip component and key

- [x] 2.1 Read `/Users/jay/.claude/skills/impeccable/reference/craft-floor.md`, then build the strip component as inline SVG: axis, five-year gridlines, ring, tick, square above the axis, diamond, amber dashed flag, end stop; `role="img"` with the sentences as its name; ink in `currentColor`. Verify: rendered on `site-fixture` and inspected at 144 px and at phone row width.
- [x] 2.2 Build the key from the same marks with their words; run the words through the verdict check at build. Verify: a test asserts the six names are present and that verdict wording fails the build.
- [x] 2.3 Add strip and key styles to `site/src/styles/global.css`, including print and forced-colours rules. Verify: print preview and `forced-colors: active` emulation show every mark.

## 3. Surfaces

- [x] 3.1 `DayReport.astro`: draw the strip and counts line under the status; stop showing the two sentences in sight. Verify: `site/tests/home-days.test.mjs` or `day-list.test.mjs` asserts the strip, the counts, and that the sentences appear only in the strip's name.
- [x] 3.2 Home page: add the strip's key beside the kind pills. Verify: page test asserts one key before the first strip.
- [x] 3.3 `ClaimTable.astro`: draw the strip under the status at one width on wide screens and at the row's width below the breakpoint (see design decision 9); key above the table; status label still shown. Verify: `site/tests/site.test.mjs` asserts a strip and a status label on every row of a topic, year and approved-claims table.
- [x] 3.4 Check every other user of `ClaimTable` (claim page, guide entry, source page) at desktop and phone width and fix any overflow. Verify: screenshots of one page of each kind on `site-published`.

## 4. Guide and design records

- [x] 4.1 Add the guide entry for the record strip on the site's own words shelf, with what it rests on and what it does not tell; make the build fail when it is missing. Verify: `site/tests/guide-and-landing.test.mjs` covers presence and the failing build.
- [x] 4.2 `GLOSSARY.md`: add "record strip" and its marks. Verify: terms in code, key and guide match the glossary exactly.
- [x] 4.3 `DESIGN.md`: add the record strip component; amend principle 3 and the "every record line says its kind in words" rule to record the operator's decision of 2026-11-15 (status label stays in sight; repeated captions move to a key and text alternatives); update the home report row and index tables entries. Verify: the three passages read consistently with the built pages.

## 5. Verification

- [x] 5.1 Run `make check` with a branch-specific `TEST_DATABASE_URL`. Verify: ruff, ty, pytest and the site build pass.
- [x] 5.2 Run `impeccable detect --json` on the changed site files and look at home, one topic index and one year page on `site-published` at 1280 px and phone width. Verify: no new detector findings; a home report row is shorter than before on a phone; axes align down the table column.
- [x] 5.3 Read the strip with a screen reader path (accessibility tree via `read_page`) on a claim with trials before its report and on a claim with a report only. Verify: each is one image whose name gives counts and dates only.
