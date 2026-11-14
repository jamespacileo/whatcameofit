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
