# Design

`collectFromPage` remains the self-contained function injected on popup opening. On YouTube it resolves a single watch or active Shorts renderer bound to the current video ID. It returns only the relevant text/links and a media-scope descriptor. Missing or stale context returns no inferred page content; an explicit text selection remains usable.

`inspectVisible` accepts that descriptor and restricts media to a video within the chosen renderer. Capture obtains a fresh descriptor before each before/after inspection, applying the existing active-tab, navigation, sensitive-field and embedded-document guards. It refuses ads, offscreen players and missing scope rather than capturing the whole personalised page. No YouTube DOM selector logic is duplicated in capture.

Shared address comparison recognises watch, share, Shorts, live and embed forms by video ID. The stricter source-URL helper strips only known playback/sharing parameters, refusing unknown ones. Text-result fingerprints exclude the advancing playback clock; visual results retain their fresh screenshot digest. The Worker continues to refuse public-cache writes for browser-only content.

The caption API requires permission to edit the video, so this change uses only DOM text the browser has already loaded. There is no full-video understanding guarantee. Synthetic fixtures exercise real selectors using the test-only LinkeDOM dependency; real browser acceptance remains necessary because YouTube changes its markup.
