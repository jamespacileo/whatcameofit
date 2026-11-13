# Safari acceptance — 13 November 2026

Tested the installed local Safari extension 0.8.0 against the production lookup service. No account settings or monthly spending limits were changed. The Apple submission remains unchanged.

| Scenario | Observed result |
| --- | --- |
| Startup | Initial install exposed `api.notifications.onClicked` on Safari's absent notifications API. The guarded build enabled successfully, opened its popup, and retained Following and Recently checked. |
| Watch page `VOo_Xf_UiZU` | Opening the extension automatically read the page and fell back to the visible video frame. The sparse title/frame did not identify a specific treatment; the popup stated the registry was not searched and nothing was ruled out. |
| Loaded transcript on that watch page | Opened Show transcript in YouTube and observed the loaded segment controls. The next popup used the text lookup path and attributed the source to the current YouTube post. It did not invent a treatment name from the imprecise transcript. |
| Description source links | The transcript lookup exposed YouTube's injected auto-dubbing help link being treated as an article source. Excluded `https://support.google.com/youtube/…` and added a synthetic regression that failed before the fix and passed after. |
| Shorts `VOo_Xf_UiZU` | Opening the extension automatically used a visible frame and completed the lookup. |
| Navigate past the Short | This account has watch history/recommendations off, so the next-feed view contained no video. The extension reported too little readable content and explicitly said nothing was sent. It did not reuse the preceding video's answer or capture recommendations. |
| Different Short `tLesHyxwxs8` | Direct navigation to the second Short produced a fresh frame lookup identifying “Elastin-like polypeptides” for tooth loss, with no matching ClinicalTrials.gov record found. This is an unreviewed extraction, not validation of the video or treatment. |
| Reopen the paused second Short | The popup immediately showed “Previous result · 13 Nov 2026” and the same structured answer. |

The account's disabled Shorts recommendations prevented an ordinary next-recommendation transition. Direct video changes and the empty-renderer transition were tested in Safari; preloaded-video scoping and stale-navigation rejection also have synthetic regression coverage. Current watch/Shorts/transcript DOM layouts were previously inspected in Chrome.

The final build includes the YouTube help-link fix and the newly merged branding. All 113 extension tests and 195 site tests passed, followed by production site and extension builds and an Xcode universal Safari build. The installed bundle was ad-hoc signed and strictly verified; every installed extension resource was compared with the build output. Only one extension identifier was registered.

Final enabled-build smoke check is pending the Safari checkbox being enabled.
