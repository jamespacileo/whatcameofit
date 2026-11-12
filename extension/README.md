# Browser extension

Open the toolbar popup to see what happened to the breakthrough in the article you are reading. A tracked report shows its reviewed claim and a link to the evidence. An untracked page starts a registry lookup automatically when the service is available.

It compares the page's address with the site's `lookup.json` inside the browser. The address is never sent anywhere. It can see a tab only when its button is pressed.

For a page that is not tracked, and only where the site answers registry searches, opening the popup reads the current page inside the browser and sends the site the text and its outgoing links; for a post, also the platform's name. The service uses OpenAI, which may retain text for safety checks. The popup displays this disclosure while searching and with its automatic result. Use public reports only. The page's address is not sent. Select words on the page first to send only those.

The extension reads nothing as you browse with the popup closed. A reviewed match and a non-web tab start no model request. Repeated actions share an in-flight lookup, and closing the popup cancels its pending fetch. Each candidate is grouped in a card with its registry link, phase, state, identifier and model-estimated match confidence. Confidence concerns the match to the report.

A post on X links out only through X's shortener (`t.co`), which the site's server may not follow. The popup opens such a link in the browser, as a click would, to learn which article it leads to, and sends that address. That is why the extension has permission for `t.co` as well as for the site.

## Build

```sh
make extension
```

This writes `extension/dist`, version 0.2.0. The site's address comes from `site/site.config.mjs` and defaults to `https://whatcameofit.com`. Set `SITE_URL` to build for a local service, as below. The public site's registry search is enabled with a monthly usage allowance.

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

Load `extension/dist` in Chrome as above. If it was loaded before, press its reload arrow on `chrome://extensions`. If it keeps using an old lookup file with search disabled, remove it and load it again to clear that file's six-hour cache.

Then open each of these and open the extension's toolbar popup. An untracked page should search immediately:

1. A post on X that links to a news story. The answer should say it was read by your browser from the post and the article it links to, naming the outlet.
2. A post on Reddit that links to a study or a story.
3. An article on a site that refuses software, such as the-sun.com or medicalxpress.com.
4. Any of the above with a sentence selected first: only the selection is searched.
5. A tracked article. Its reviewed claim appears without a registry search.

To see what went wrong when something does, right-click inside the popup, choose "Inspect" and read the Console.

To have an agent with computer use do this in your place, hand it [agent-test-brief.md](agent-test-brief.md).

## Safari

```sh
make extension-safari
```

Apple's converter writes `extension/safari/WhatCameOfIt/WhatCameOfIt.xcodeproj`. The script sets both display names to the built manifest's name, currently **What came of it?**, and both release versions to its version. The app and extension target macOS 12.0. It compiles an unsigned Release build for Intel and Apple silicon and prints the app's path. This verifies compilation. Safari runtime testing is a separate step.

The app identifier defaults to `com.whatcameofit.WhatCameOfIt`; the extension identifier adds `.Extension`. Set `SAFARI_BUNDLE_ID` when building for another registered app identifier.

For the local registry-search service, use `SITE_URL=http://localhost:8787 make extension-safari` while `make lookup-dev` is running. To run the unsigned app:

1. In Safari, turn on "Show features for web developers" (Settings, Advanced), then "Allow unsigned extensions" (Settings, Developer). Safari asks for this again after each restart.
2. Open the app the script names at the end of its output, once.
3. Turn the extension on in Safari's Settings, Extensions.

App Store distribution needs Apple Developer Program access, a registered bundle identifier and distribution signing. The script's unsigned build is for local testing. The production `extension/dist` resources can also be zipped for Apple's Safari Web Extension Packager in App Store Connect. Store submission and production screenshots remain separate release steps.

## Layout

- `src/lookup.js`: decides what to show. Pure, tested in `tests/`.
- `src/view.js`: draws a state. Status wording comes from `lookup.json`; the site owns it.
- `src/open-page.js`: reads the open page (`collectFromPage`, which runs inside it) and chooses what a registry search needs (`composeRequest`, pure, tested in `tests/`).
- `src/short-links.js`: learns where a link through X's shortener leads. Tested in `tests/`.
- `src/controller.js`: owns one popup's automatic lookup, cache, cancellation and explicit retries.
- `src/popup.js`: connects the controller to the active tab, shared readers and rendered view.
- `build.mjs`: copies the above with what is shared with the site (the address comparison, how an address is told from a post, the page reader, the wording of an answer and the notices), the site's face and icon, and writes the manifest.
- `dev/`: a page showing every popup state side by side. `node extension/build.mjs --dev`, then serve `extension/dist` and open `states.html`.

Tests run with `node --test extension/tests/*.test.mjs` (also part of `make check`). The explicit glob discovers the test files on Node 24.
