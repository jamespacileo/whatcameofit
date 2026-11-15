# Released corpus verification — 15 November 2026

## Released changes

| Change | Merge | Worker | Safari installed |
| --- | --- | --- | --- |
| Condition/regimen card guard and current carousel slide (#132) | 7868b02657ed | 2aa98331-279a-419b-a4aa-f15f3aec3ee7 | 0.9.6 (15) |
| Bound LinkedIn captions and Bluesky original posts (#133) | a92783deaa42 | fa87fe45-554c-4d8e-87a3-38a2a98ff3f9 | 0.9.7 (16) |
| Bound Facebook posts and complete comparison regimens (#134) | 7cd56bc85498 | db3dcf70-f8ac-4ede-a425-877483a7ae18 | 0.9.8 (17) |

All three passed independent standards/spec reviews and GitHub Tests and build before merging; deployment completed successfully. The final source passed 1,439 pipeline, 608 site and 167 extension tests. The installed app is signed, universal, byte-matched to the built extension resources, with permissions unchanged and a rollback copy retained.

Native Safari has not executed these three new versions: the Mac locked during the checks and remains locked. The earlier 0.9.5 native results remain historical evidence, not proof for 0.9.8. Finish task 1.2/2.4 after unlock. Chrome runs execute the released collector and request composition on the actual live DOM, then submit to production; they are not labelled native Safari checks.

## Full corpus observation

The 258 rows now have 114 pass, 86 partial, 32 review and 26 blocked outcomes. Card observations are separate: 104 exact source/card mappings, 86 no-card answers, 32 unresolved identity/card reviews, 10 negative controls where a card is not applicable, and 26 unverified because source access failed. These are coverage observations, not a claim that all clinical matches are correct.

- `runs/2026-11-15-full-address.json`: 205 address outcomes, including 104 exact published mappings checked without model calls and 84 unique card pages checked for reachability and the recorded condition. Source/card mapping checks do not independently adjudicate all clinical evidence.
- `runs/2026-11-15-full-browser.json`: 55 live browser results, including 52 social rows and three additional video/Substack edge cases. S009 is a browser-policy block on the New York Times destination; no alternate access was attempted. The 205 address rows and 55 browser rows overlap on two rows.
- A048's transient HTTP 502 cleared on a released retry; the complete retifanlimab/carboplatin/paclitaxel regimen was returned.
- S026 now reads the selected pain-drug carousel slide. S036 and S045 no longer attach the unrelated biological-ageing card. S045 returns both bimagrumab and semaglutide and BELIEVE NCT05616013. Appropriate new card coverage remains open.
- Facebook S023 reads the NCI caption, not the neighbouring post. S024 remains caption-only: the pixel guard detected sensitive content and refused capture. S025 reads the identity-bound public video preview. No full video/audio claim is made.
- LinkedIn S010/S011/S036 omit sidebars, drafts and comments. Bluesky S006/S007 omit replies. The final YouTube short link N010 was followed to its observed video and its public expanded description was read with the video paused.

`reruns.json` contains one current observation per row. Historical run files are retained. Temporary pacing-queue durations are excluded from the displayed seconds and are explicitly not app-latency measurements. No source article/post text, screenshots or model gists are committed.

## Sheet and persistence

The native Sheet is 15DclgztI5Pbh-wOpHzi7ITtOFSCgke2yrba7LRzcoxA, URLs tab 1415648251. The first pass updated 104 mapped rows. The second updated the remaining 154 rows in H:P and Z:AF, preserving all other entered values, formulas, validation and formatting. Read-back found zero changed-cell differences and zero unrelated changes; Summary formulas are unchanged. Sheet counts match the assembled corpus above. Native visual verification remains unavailable: Chrome is signed into another account, and Safari is locked.

The durable corpus cache now retains 101 address responses and 55 browser responses from this audit without article text, screenshots or gists. Nine corpus-cache regression tests pass. The assembler emits the same 258 rows and result counts. A direct released negative-control lookup took 3,964 ms (server reading 2,189 ms); its repeated answer took 80 ms with no model-stage timing. This is one measured case, not a corpus-wide latency claim. Shared lookup requests were serialized and spaced by 13 seconds; no quota or budget was raised.

## Remaining work

Missing card coverage, synonymous condition descriptions, broad/unnamed captions, source refusals and full-video uncertainty remain open. Do not convert these to passes simply because a candidate trial exists. The private database contains additional unrelated backfill work beyond the published 84-claim snapshot; a bulk export has not been published as part of this audit. Prepare and verify relevant claims through the existing pipeline while preserving unrelated work and visible confidence reasons.
