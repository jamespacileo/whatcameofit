# Verification

## Extension page (tasks 1.1 to 1.6, 6.1a)

2026-11-14. Scope: `/extension`, its links from the footer, the home page and a claim page, and the settings that publish it. The guide, the about page, the audience pages and the topic pages are not built.

- Site suite: 279 passed, 15 of them new in `site/tests/extension-page.test.mjs`. They cover the rule that picks the example claim, the drawn popup's labels against `extension/src/view.js`, the permissions against the extension's manifest, a build with no store (no page, no link), with one store and with both, and the scenarios in `specs/landing-pages/spec.md` for this page.
- Extension suite: 119 passed. No extension file was changed.
- Site build: passed its publication check (footer notices on every page). With no store address, 30 pages as before.
- Not run: the pipeline's tests and `make check` as a whole, which need the Docker database. No pipeline file was changed.
- Browser, dev server on the published export with placeholder store addresses: 1440, 900, 390, 375 and 320 pixels wide. No horizontal overflow at any. At 900 the answers wrap two and one. With an Android user agent at 390 and 375 both install controls are outlined on one row, 49 pixels tall. The status label's bottom edge is at 616 pixels on a 390 by 844 screen and at 668 on 320 by 700.
- Drawn popup against the extension's own states page (`extension/dist/states.html`, built with `node extension/build.mjs --dev`): the tracked answer was compared by eye and corrected to match (promise box, inset facts, notices, last-checked line, settings link, the two lists). The search and Following answers were drawn from `view.js` and `popup.css`, not compared against a rendered state.
- Design detector over the page and its two components: no findings.
- Finish review (independent reviewer, captures at 1440 and 390 wide): first pass "fix" with eight items; second pass seven resolved and the phone item partial; third pass "ship", with nothing remaining. That verdict covers the eight fixes, not a fresh review of the whole page.

Not checked:

- The page with a real store address, and the store listings themselves: no store lists the extension yet.
- Safari, Firefox and a real phone. The browser check that picks the reader's control was seen working in Chromium only.
- Keyboard focus by eye, the printed page, a forced palette and a screen reader.
- The both-outlined phone state is in no saved capture; the headless capture runs with a desktop user agent.

The example claim on 2026-11-14 is `parkinsons-solengepras`, chosen by the rule. It has not been checked by a person, so the drawn popup carries the unchecked notice, as the real popup would.

## Guide, topic pages, about page, audience pages (groups 2 to 6)

2026-11-14. Scope: `/guide` and its 27 entries, their links from the claim page and the method page, the topic page's opening and its card, `/about`, the three `/for/` pages, the footer links, and the lookup box moved into a component.

- `make check`: passed (ruff, ty, the pipeline's tests, the site's tests, the site build, the extension's tests).
- Site suite: 342 passed. New: 19 in `site/tests/guide-and-landing.test.mjs` (each guide check with a passing and a refused case, then the pages in one build of the fixture export), 7 in `site/tests/topic-card.test.mjs`, and `site/tests/lookup-component.test.mjs`. `site/tests/home-search.test.mjs` now reads the lookup's script from the component.
- Site build on the published export: 337 pages, the publication check passed.
- Browser, dev server on the published export. At 375 and 1280 wide: `/about`, `/guide`, `/guide/phase-3-trial`, `/guide/registered-trial-not-treatment-option` (the longest title), `/for/journalists`, `/for/clinicians`. No horizontal overflow on any of them. On `/about` at 375 by 812 the status label's top edge is at 699 pixels. The journalists' search was driven by script: a word with no match shows the no-result sentence, "tooth" lists eight claims, and picking one swaps the embed (339 by 420 at 375 wide, held to its frame) and the code. On the clinicians' page the example claim's article address returned its status, the dated sentence, "Copy sentence" and "Card to post", and the address did not enter the page's own.
- Topic card: the helper that built it rendered all 18 published topics at 1200 by 630 and looked at the cancer card; a 272-character summary was not clipped.
- Design detector over the new pages and components: no findings.
- Sources: every source of the nine research entries, and the PLOS ONE paper, was fetched and read on 2026-11-14. Notes with each address and what it supports were kept outside the repository.

Not checked:

- `/for/researchers`, `/guide/<slug>` with no claim to show, and a topic page were not opened in a browser; they are covered by the build tests only. No page was looked at between 375 and 1280, in print, in a forced palette, with a keyboard by eye, or with a screen reader.
- Whole-page captures: the pane's captures showed the top of each page only. Lower sections were read from the page's text and measured, not seen.
- "Copy sentence" on the topic page and the copy buttons were not pressed in a browser; the copied text is checked as a string.
- No independent finish review was run on any of these pages.
- The about page runs to about 2.2 screens at 1280 by 900 before the footer; the brief asks for under two.
- Three source notes carry a caveat. The United States NIH pages would not load, so no entry cites them. The Committee on Publication Ethics page was read, not its full guideline. No official page read says in plain words that trials stop for slow recruitment or funding, so no entry says so.

Waiting on the operator:

- 2.8: reading the 27 entries and setting each `checked: true`.
- 4.4: the sentence on funding in "Who runs it".
- 4.2: the choice between the three first-viewport directions for `/about`; the brief's lead is built.
