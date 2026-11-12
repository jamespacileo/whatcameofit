# Browser extension

One click on the toolbar button shows what happened to the breakthrough in the article you are reading: the tracked claim, where it stands, and a button to its page on the site.

It compares the page's address with the site's `lookup.json` inside the browser. The address is never sent anywhere. It can see a tab only when its button is pressed.

For a page that is not tracked, and only where the site answers registry searches, the popup offers "Search the trial registry for this page". Pressing it reads the open page inside the browser and sends the site the text read and the links in it; for a post, also the platform's name. This is how a post on X or Reddit, or an article behind a paywall the reader subscribes to, can be searched: the reader's own browser reads the page, and the site asks the platform nothing. The page's address is not sent. Select words on the page first to send only those.

A post on X links out only through X's shortener (`t.co`), which the site's server may not follow. The popup opens such a link in the browser, as a click would, to learn which article it leads to, and sends that address. That is why the extension has permission for `t.co` as well as for the site.

## Build

```sh
make extension
```

This writes `extension/dist`. The site's address comes from `site/site.config.mjs`; until a domain is chosen that is the local preview, so the site must be running (`docker compose up -d`).

## Chrome

1. Open `chrome://extensions` and turn on "Developer mode".
2. Press "Load unpacked" and choose `extension/dist`.
3. Open a tracked article and press the extension's button.

## Try the registry search on this machine

The search needs the site's lookup service, which the local preview does not run. Start it, and build the extension for its address:

```sh
make lookup-dev                                  # the site with its lookup service, at http://localhost:8787
SITE_URL=http://localhost:8787 make extension    # in a second terminal
```

Load `extension/dist` in Chrome as above. If it was loaded before, press its reload arrow on `chrome://extensions`; if no search button appears, remove it and load it again, which clears its saved copy of the lookup file.

Then open each of these and press the extension's button, then "Search the trial registry for this page":

1. A post on X that links to a news story. The answer should say it was read by your browser from the post and the article it links to, naming the outlet.
2. A post on Reddit that links to a study or a story.
3. An article on a site that refuses software, such as the-sun.com or medicalxpress.com.
4. Any of the above with a sentence selected first: only the selection is searched.
5. A tracked article. No search is offered: the claim is shown.

To see what went wrong when something does, right-click inside the popup, choose "Inspect" and read the Console.

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
- `src/short-links.js`: learns where a link through X's shortener leads. Tested in `tests/`.
- `src/popup.js`: the glue to the browser (current tab, saved copy, fetch, reading the page when asked).
- `build.mjs`: copies the above with what is shared with the site (the address comparison, how an address is told from a post, the page reader, the wording of an answer and the notices), the site's face and icon, and writes the manifest.
- `dev/`: a page showing every popup state side by side. `node extension/build.mjs --dev`, then serve `extension/dist` and open `states.html`.

Tests: `node --test extension/tests/` (also part of `make check`).
