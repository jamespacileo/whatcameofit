# Design

## Decisions

### D1. Match in the browser against a published file

The site is static, so there is no server to ask. The extension downloads `/lookup.json` and compares addresses itself. This also means no reading history ever leaves the reader's browser.

Alternative considered: a lookup service that takes a page address. Rejected: it needs a server, and it would receive every address a reader checks.

### D2. Only the current tab, only on click

The extension asks for `activeTab`, `storage` and the site's own address. It cannot see any tab until its button is clicked. A marker on the button for tracked pages would need permission to read the address of every tab; that is left out until the operator asks for it.

### D3. One comparison function, owned by the site

`site/src/lib/article-key.mjs` turns an address into its comparison form: host without `www.`, `m.` or `amp.`, path without a trailing slash or AMP suffix, tracking parameters removed, other parameters kept in order, no scheme or fragment. The site uses it to build the lookup file and the extension's build copies the same file, so the two cannot drift.

### D4. The site owns the wording

The lookup file carries labels and notices already worded by the site. The extension contains no status wording of its own, so the neutral-wording build check covers it.

### D5. One codebase for Chrome and Safari

The extension is a Manifest V3 web extension in plain JavaScript modules, with no bundler. `extension/build.mjs` writes `extension/dist/`, including the manifest (which needs the site's address) and icons drawn from the site's favicon. Safari's app wrapper is generated from `dist/` with Apple's `safari-web-extension-converter` and is not checked in.

### D6. The popup follows DESIGN.md

White ground, ink text, the blue accent for the site name, links, the status label and the button, pale amber only for a promise, Figtree bundled. Light only. The status sits in the same panel treatment as the claim page's digest, so a reader who clicks through sees the same thing larger.

## Risks

- **Address forms differ more than expected** (syndicated copies, regional hosts, paywall redirects). A miss shows "not a tracked report", which is safe but unhelpful. Mitigation: more than one article per claim, and the comparison function is tested and shared.
- **"Not tracked" read as "not true".** The untracked view says in words that it implies nothing about the story.
- **Safari distribution** needs an Apple developer account; running it locally needs "Allow unsigned extensions".
