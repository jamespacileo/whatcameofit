# Proposal

## Why

Readers meet a breakthrough story in their browser, not on this site. The operator asked on 2026-11-11 for a quick way to get the tracked status of an article that is open in Safari or Chrome, as an extension with a minimal design.

## What Changes

- The site publishes a lookup file, `/lookup.json`, built from the export: every published claim's source article addresses, and for each claim the headline, status wording, first-reported date, latest dated promise and page address.
- A browser extension for Chrome and Safari. One click on its toolbar button shows, for the article in the current tab, the claim it reports and where that claim stands, with a button to the claim page.
- The extension compares the tab's address with the lookup file inside the browser. The address of the page being read is never sent anywhere.
- The site's address joins the brand config, because the extension has to know where the site is served.

Not in this change: a marker on the toolbar button before it is clicked (it would need permission to read every tab's address), suggesting an untracked article, Firefox, and store listings.

## Capabilities

### New Capabilities

- `browser-extension`: looks up the article in the current tab and shows its claim's status.

### Modified Capabilities

- `site-publishing`: the site publishes the article lookup file.

## Impact

- **Site:** one new build output, `lookup.json`, and one shared function for comparing article addresses. No change to the export.
- **New directory:** `extension/`, plain JavaScript with a small build script. The Safari project is generated from the built extension by Apple's converter and is not checked in.
- **Privacy:** no personal data. The extension requests only the current tab on click, local storage for its copy of the lookup file, and the site's own address.
- **Until the site is deployed** the extension only works against the local preview. Publishing it in the Chrome Web Store or the App Store needs developer accounts and is the operator's decision.
