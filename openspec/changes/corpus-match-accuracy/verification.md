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

## Complete-regimen background-card guard — 15 November 2026

The vocabulary and drug-linking seams could identify a single component as the complete combination, including at confidence 1.0. Regressions reproduced this before the fix. Explicit components in canonical names and regimen aliases are now excluded before classification or drug-name lookup; the export also skips older approved component links before choosing an eligible whole-regimen record. It suppresses that component’s derived target without changing its stored decision or clinical status. Comma-separated lists, combination prefixes/suffixes, optional components, and a branded primary name are covered.

Final `make check`: 1,450 pipeline tests, 608 site tests, 167 extension tests, static/type/build checks passed. Independent Standards and Spec reviews passed at `989de3c` after their findings were reproduced and fixed. A rollback-only database export compared all 84 published claims and found zero background-card differences. For the prepared bimagrumab-plus-semaglutide and COURAGE regimens, the export retains the independently matched Obesity condition cards (0.98 and 0.99) and omits single-drug cards. These two new claim pages have not been published by this code-only change; staging the full approved database would also introduce 108 other claims, which still need a publication-data review. No source text, credentials, model retries or extra live classifications were needed for this verification. Safari resources are unchanged from 0.9.8 (17); its native execution remains unverified while the Mac is locked.

## Evidence-stage publication check — 15 November 2026

The rollback-only private-data check found 110 prepared claims without confirmed stages. The new rule confirms 68 existing suggestions at the unchanged 0.95 threshold for both chosen probability and confidence; 42 remain unknown. Decision-log counts (381,516) and usage-row counts (27,588) were identical before and after, showing no new model calls. Seven unknown-stage claims without trials now remain explicitly `no_trial_found`; the full new-claim status distribution is 10 preclinical, 16 no trial found, 8 registered, 9 Phase 1, 13 Phase 2, 50 Phase 3 and 4 terminated. All database changes in this verification were rolled back.

Compared with the pre-fix private export, none of the 84 currently published claims changed stage, status or background cards. Seventeen already had smaller explaining-event ID lists in the private export than in the published snapshot; those differences predate this fix and do not change their status codes or histories. They remain part of the publication-data review.

`make check` passed 1,455 pipeline, 608 site and 167 extension tests. The subsequently added migration regression passed separately, bringing pipeline coverage to 1,456 tests; it verifies that new rows use the honest unknown-stage default and existing rows are untouched. Standards review passed. Spec review found a missing claims-capability delta, which was added to keep stage-confirmation requirements coherent. The public guide, status explanations and topic summary wording no longer infer a human study from a missing trial record. No new publication snapshot or Safari resource is included.

PR #137 merged as `5370a81d61442ab9c9f1e5131856d730ee9d39f8`. Production run 43732886723 passed and deployed Worker `bd351ff5-deed-4c32-8d25-c0eb349e7b89` at 16:02:49 UTC. The released `/guide/no-trial-record-found` visibly states that a missing registry match does not establish whether the treatment has been studied in people. Migration 0022 and the 68 eligible recorded-stage confirmations were applied to the private database at 16:00 UTC with no new decision or usage rows. The public snapshot remains 84 claims. Native Safari verification remains blocked by the locked Mac.

## Vocabulary entry-name evidence — 15 November 2026

The daraxonrasib term candidate had a recorded exact entry-name match but its classifier prompt omitted that evidence. The revised prompt includes it, explicitly preserving uncertainty because an entry term can be narrower than its record. The new named-claim-only pending reread preserves approvals/rejections and previous labels; failed calls retain their previous fit and score. A regression caught an existing kind link entering the new reread path; the kind link is now excluded along with explicit regimen components.

The bounded private check reread two pending daraxonrasib terms with unchanged thresholds. MeSH `C000731071` changed from broader 0.56 to exact 0.99 and was approved by rule. Pancreatic Neoplasms remains pending (broader 0.54). The [current MeSH record](https://meshb.nlm.nih.gov/record/ui?ui=C000731071) identifies daraxonrasib and lists RAS Inhibitor A122; the [NCI drug dictionary](https://www.cancer.gov/publications/dictionaries/cancer-drug/def/daraxonrasib) independently identifies RMC-6236. Two new decision logs and two usage rows were recorded; a subsequent ordinary terms run added neither (381,518 decision rows; 27,590 usage rows before and after). The new background card has not yet been published. No source article text or new lookup identity equivalence was introduced.

`make check` passed 1,460 pipeline, 608 site and 167 extension tests before the extra kind-preservation regression. All 70 subject-term tests and type checks pass after that correction (1,461 pipeline tests total); CI verifies the final complete suite.

Both independent reviews passed. PR #138 merged as `9fc91ff84b9e63ba366f0eaaa767afebf0b45366`; final CI passed all 1,461 pipeline tests. Production run 43734470533 deployed Worker `28de385f-135b-4257-ba55-215cd1cfd053` at 16:19:13 UTC. This is a code-only release; the new background card still awaits the normal all-approved-claims publication snapshot.

## Trial-setting correction — 15 November 2026

Live Chrome inspection of corpus A041 confirmed that its main report concerns previously treated metastatic pancreatic cancer and separately links a first-line study. The prior released answer read the primary condition correctly but gave that separate record a match probability of 1.00. The primary registry identifies [NCT06625320](https://clinicaltrials.gov/study/NCT06625320) as previously treated and [NCT07491445](https://clinicaltrials.gov/study/NCT07491445) as first-line; [the HRA record](https://www.hra.nhs.uk/planning-and-improving-research/application-summaries/research-summaries/rasolute-303/) confirms the latter setting.

Six bounded private-provider checks reused the two stored public registry records. For a previously treated claim, their match probabilities were 1.00 and 0.00; for a first-line claim, 0.00 and 0.99; for an unrestricted metastatic-pancreatic-cancer claim, 1.00 and 0.96. All six classified as expected with the revised question. This is a targeted validation, not a general accuracy estimate. It adds three paid batches, no new source fetch or article-text storage, and no retry. Existing approved private evidence was not rewritten. Release and affected-URL reruns remain to be completed.
