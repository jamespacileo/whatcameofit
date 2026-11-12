# Browser extension

One click on the toolbar button shows what happened to the breakthrough in the article you are reading: the tracked claim, where it stands, and a button to its page on the site.

It compares the page's address with the site's `lookup.json` inside the browser. The address is never sent anywhere. It can see a tab only when its button is pressed.

For a page that is not tracked, and only where the site answers registry searches, the popup offers "Search the trial registry for this page". Pressing it reads the open page inside the browser and sends the site the text read and the links in it; for a post, also the platform's name. This is how a post on X or Reddit, or an article behind a paywall the reader subscribes to, can be searched: the reader's own browser reads the page, and the site asks the platform nothing. The page's address is not sent. Select words on the page first to send only those.

## Build

```sh
make extension
```

This writes `extension/dist`. The site's address comes from `site/site.config.mjs`; until a domain is chosen that is the local preview, so the site must be running (`docker compose up -d`).

## Chrome

1. Open `chrome://extensions` and turn on "Developer mode".
2. Press "Load unpacked" and choose `extension/dist`.
3. Open a tracked article and press the extension's button.

## Safari

```sh
make extension-safari
```

Apple's converter writes an Xcode project to `extension/safari` and the script compiles it without signing. To run it:

1. In Safari, turn on "Show features for web developers" (Settings, Advanced), then "Allow unsigned extensions" (Settings, Developer). Safari asks for this again after each restart.
2. Open the app the script names at the end of its output, once.
3. Turn the extension on in Safari's Settings, Extensions.

Distribution through the App Store needs an Apple developer account and a real bundle identifier (`SAFARI_BUNDLE_ID`).

## Layout

- `src/lookup.js`: decides what to show. Pure, tested in `tests/`.
- `src/view.js`: draws a state. Status wording comes from `lookup.json`; the site owns it.
- `src/open-page.js`: reads the open page (`collectFromPage`, which runs inside it) and chooses what a registry search needs (`composeRequest`, pure, tested in `tests/`).
- `src/popup.js`: the glue to the browser (current tab, saved copy, fetch, reading the page when asked).
- `build.mjs`: copies the above with what is shared with the site (the address comparison, how an address is told from a post, the page reader, the wording of an answer and the notices), the site's face and icon, and writes the manifest.
- `dev/`: a page showing every popup state side by side. `node extension/build.mjs --dev`, then serve `extension/dist` and open `states.html`.

Tests: `node --test extension/tests/` (also part of `make check`).
