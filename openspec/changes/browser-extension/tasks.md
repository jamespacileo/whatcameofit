# Tasks

## 1. Lookup file

- [x] 1.1 Add the article comparison function and its tests; verify the address forms in the spec scenario give one key
- [x] 1.2 Publish `/lookup.json` from the export, with the notices moved to one shared constant; verify the site test for the lookup file passes and no unpublished claim is in it
- [x] 1.3 Add the site's address to the brand config; verify the extension build reads it

## 2. Extension

- [x] 2.1 Write the lookup and saved-copy logic as pure functions with tests; verify tracked, untracked, two-claim and freshness cases
- [x] 2.2 Build the popup (checking, tracked, untracked, not a web page, unreachable, saved copy) following DESIGN.md; verify every state in a states page at the popup's width
- [x] 2.3 Write the build script (manifest, icons, font, shared function); verify `extension/dist` loads as an unpacked extension's file set and `make check` runs the extension tests
- [x] 2.4 Generate the Safari project from `dist/` and compile it; verify the build succeeds without signing

## 3. In a real browser

- [ ] 3.1 The operator loads `extension/dist` in Chrome and clicks the button on a tracked and an untracked article; verify both views
- [ ] 3.2 The operator runs the Safari project and does the same; verify both views

## 4. Paste a link on the home page

- [x] 4.1 Read a pasted address in the shapes links are shared in and name shortened links and posts; verify the address tests pass for each outlet group and wrapper
- [x] 4.2 Offer the closest tracked claims for an untracked address; verify the three closest-match tests pass
- [x] 4.3 Make the home page's main field take a link or search words; verify the site builds and the search scenario still passes
- [x] 4.4 Try the field in a browser with a tracked link, an untracked one and a shortened one; verify each answer

## 5. A registry search of the open page (decided 2026-11-12)

- [x] 5.1 Read the open page inside the browser and choose what a search needs: a post's own words, an article as the site reads one, or the reader's selection; verify the seven open-page tests pass
- [x] 5.2 Offer the search in the popup for an untracked page where the site answers one, send what was read, and show the answer in the site's wording; verify every new state on the states page
- [x] 5.3 Run the page reader on one real post in a browser and put what it read through the service (2026-11-12: a post on X; its words came through without the writer's name, the time or the counts, and X was asked nothing)
- [x] 5.6 Open a post's link through X's shortener in the reader's browser and send the address it leads to; verify the five short-link tests pass (2026-11-12: the shortener's real page was read; from it the chain ran through a publisher's shortener to the article)
- [ ] 5.4 The operator loads `extension/dist` in Chrome, opens a post on X and on Reddit and an article behind a paywall they subscribe to, and presses the search; verify each answer
- [ ] 5.5 The operator does the same in Safari

