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
- [ ] 4.4 Try the field in a browser with a tracked link, an untracked one and a shortened one; verify each answer
