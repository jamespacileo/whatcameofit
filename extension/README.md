# Browser extension

Open the toolbar popup to see what happened to the breakthrough in the article you are reading. A tracked report shows its reviewed claim and a link to the evidence. An untracked page starts a registry lookup automatically when the service is available.

It compares the page's address with the site's `lookup.json` inside the browser. This initial check sends no page address. It can see a tab only when its button is pressed.

For a page that is not tracked, and only after the reader enables automatic search, opening the popup reads the current page inside the browser and sends the site the text and its outgoing links; for a post, also the platform's name. A cleaned page address supports result reuse. When text misses visible media, one bounded screenshot can be sent. The service uses OpenAI, which may retain content for safety checks. The popup discloses this before permission and in its details. Use public reports only. Select words on the page first to send only those, without a screenshot or source address.

The extension reads nothing as you browse with the popup closed. A reviewed match and a non-web tab start no model request. Repeated actions share an in-flight lookup, and closing the popup cancels its pending fetch. Each candidate is grouped in a card with its registry link, phase, state, identifier and model-estimated match confidence. Confidence concerns the match to the report.

Live answers can also include related paper metadata from OpenAlex and organisation identities from ROR, in collapsed sections. These are unreviewed search results, not evidence of effectiveness or an organisation's involvement. Only derived treatment/condition terms and explicitly named organisations go to these providers; page addresses, screenshots and article text do not. Public metadata is cached for seven days. Both integrations stay within their free allowances and can be unavailable without blocking the trial result.

Following and recent checks work in Safari. Background notifications and extension reminder choices are offered only when the browser provides its notifications API; Safari currently does not. Its background refresh still updates followed claims for the next popup opening. Claim pages also offer calendar reminders.

A post on X links out only through X's shortener (`t.co`), which the site's server may not follow. The popup opens such a link in the browser, as a click would, to learn which article it leads to, and sends that address. That is why the extension has permission for `t.co` as well as for the site.

On a YouTube video or Short, the reader uses the current video's title, loaded description, source links and any captions/transcript already loaded into its page. Comments, recommendations and inactive Shorts are excluded. Open **Show transcript** yourself when the spoken claim is missing from the title and description, then reopen the extension. If text is insufficient, the existing screenshot fallback can read the current visible video frame; it does not listen to audio, download the video or transcribe the whole recording. Missing or changing video context and advertisements cannot fall back to a screenshot of the whole YouTube page. The service does not fetch YouTube; browser-derived answers are not published to the shared cache. A layout the reader cannot identify can still be searched by selecting the relevant words.

## Build

Brand artwork comes from `site/public/mark.svg` and its small-size variant,
`site/public/favicon.svg`. After editing them, run `node site/scripts/brand-icons.mjs`
and rebuild the extension. To refresh artwork in an existing generated Safari project
without changing its signing, version or project settings, run
`node extension/sync-brand-icons.mjs`. The normal Safari build also does this after conversion.

```sh
make extension
```

This writes `extension/dist` using the version in `build.mjs`. The site's address comes from `site/site.config.mjs` and defaults to `https://whatcameofit.com`. Set `SITE_URL` to build for a local service, as below. The public site's registry search is enabled with a monthly usage allowance.

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

For a wider set of real pages (posts on each platform, paywalled, refused and non-English articles, pages that should not be read as treatment reports), with what the lookup service answered on each, see [test-corpus](test-corpus/README.md).

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

### App Store release checks

Use a stable Xcode release that App Store Connect accepts. A local build succeeding with a beta SDK does not mean Apple will accept its upload. On a machine with both installations, select the stable toolchain for **both conversion and archiving**, without changing the machine's global selection:

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer make extension-safari
```

Open the generated project with that same stable Xcode. Set the development team on the containing app and extension, select automatic signing, and use a new build number for both targets. Verify that their release versions match the extension manifest and their deployment targets remain macOS 12.0. Set the containing app's category to Reference and declare `ITSAppUsesNonExemptEncryption = NO` in both targets' Info.plist while the app uses only the existing HTTPS networking. Reassess the encryption declaration if that changes. The converter regenerates these files, so apply release settings after conversion.

Archive the Release scheme for a generic Mac, validate its signatures and bundled extension resources, then distribute through App Store Connect. Wait for processing and explicitly select the new build in the store version; uploading does not replace an already selected build. Update the description and review instructions, inspect the privacy disclosures against actual data flows, and use screenshots of the installed release. Verify **Waiting for Review** after submitting.

For 0.9.0 (9), Apple rejected an archive made with Xcode 27.2 beta (27B5019j), then accepted the same release built with stable Xcode 27.2 (27B52). The stable archive's extension resources matched the installed 0.9.0 build. A live Safari check of the University of Nottingham's `clinical-trial-tourettes` article returned five OpenAlex papers and two ROR identities; reopening reused the previous result. No new App Privacy category was needed for the derived searches, which are covered by the existing Search History disclosure.

As of 13 November 2026, 0.9.0 (9) is Waiting for Review. The [0.9.1 preview](https://github.com/jamespacileo/whatcameofit/releases/tag/v0.9.1-preview.1) adds the saved-check wording correction and was installed and tested locally in Safari. It does not replace the submitted App Store build. The release provides extension resources and an Xcode project requiring your own signing; Chrome registration remains parked. See the [release verification](../openspec/changes/release-polish/verification.md) for test and deployment evidence.

## Layout

- `src/lookup.js`: decides what to show. Pure, tested in `tests/`.
- `src/view.js`: draws a state. Status wording comes from `lookup.json`; the site owns it.
- `src/open-page.js`: reads the open page (`collectFromPage`, which runs inside it) and chooses what a registry search needs (`composeRequest`, pure, tested in `tests/`).
- `src/short-links.js`: learns where a link through X's shortener leads. Tested in `tests/`.
- `src/controller.js`: owns one popup's automatic lookup, cache, cancellation and explicit retries.
- `src/popup.js`: connects the controller to the active tab, shared readers and rendered view.
- `build.mjs`: copies the above with what is shared with the site (the address comparison, how an address is told from a post, the page reader, the wording of an answer and the notices), the site's face and icon, and writes the manifest.
- `dev/`: a page showing every popup state side by side. `node extension/build.mjs --dev`, then serve `extension/dist` and open `states.html`.

Tests run with `node --test extension/tests/*.test.mjs` after `npm --prefix site ci` (also part of `make check`). Synthetic YouTube fixtures use LinkeDOM to exercise real selectors without live network calls. The explicit glob discovers the test files on Node 24.

### Popup sizing regression

After `node extension/build.mjs --dev`, serve `extension/dist` locally and open `sizing.html`. Both checks must report PASS: the real popup renderer and stylesheet must measure 360px of content even when its host initially gives it only 100px. A viewport-relative body cap can prevent Safari from discovering the intended width. This checks the sizing contract; still verify the installed Safari popup visually after repeated openings and disclosure toggles.
