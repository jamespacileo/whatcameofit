# Corpus verification, 15 November 2026

The five previously failed rows and all 30 untested Social rows were attempted, plus the two untested social edge cases N013 and N014 in Negative: 37 rows total. Results are 18 pass, 1 partial, 17 review and 1 blocked, with no remaining fail verdict in this selected set. The 258-row workbook now contains 177 pass, 2 partial, 0 fail, 14 blocked, 27 review and 38 not run. Rows outside this rerun retain their existing Sheet values.

## Scope and builds

- Base: `64e7aa84b1c5593bc7cd63f424a0c2b9621742ed`, fetched current main.
- Worktree/branch: `codex-corpus-rerun-20261115` / `codex/corpus-rerun-20261115`.
- Extension build: 0.9.3; service model from existing configuration: `openai:gpt-6-luna`.
- The first corrected run used source fingerprint `589a58e09376fb799d5070212f940eafa9424c0471f36d25abd35bbc804810c5`.
- A focused seven-case follow-up used `cda788576c8ebca1403b19ab4bb0a3096fa8c314df1698aae58be2ed0e9df189`, adding acceptance of explicitly stated everyday targets such as hair growth.
- Fingerprints cover the five application files listed in `extension/test-corpus/runs/2026-11-15.json`; each row records its actual tested build.
- These changes have not been deployed or installed in Safari.

The original checkout contains unrelated work and is behind current main, so it was left untouched. The requested isolated Claude worker was attempted twice but its preflight could not access its Python runtime library; no model task ran. The corrections were implemented and verified directly in the clean worktree.

## Reproductions and corrections

The deployed address route was called for all 37 URLs. N003–N005 reproduced treatment false positives in earnings, supply and lawsuit reporting. The corrected local service returns no specific treatment for all three. Shared and local result caches advance to version 3 so old answers cannot conceal these corrections.

The social collector now binds text and screenshot scope to the addressed Instagram, Threads, Telegram or TikTok post. Regression checks reproduced and then eliminated neighbouring/recommended content, missing or stale identity metadata, and TikTok playback-failure caption loss. Explicit selection retains precedence. S014 now reads the requested CNN pancreatic-cancer caption. S021 now reads its actual multi-claim NEJM post; it remains review because several unrelated claims cannot form one treatment.

S026 was incorrectly labelled as a suzetrigine report: the readable caption profiles Vertex. Telegram S027 points to message 10951, a health-roundup continuation, while the suzetrigine text belongs to neighbouring message 10940. The URLs were retained and their expectations corrected.

S049 exposed a further overly strict identification rule: its explicit PP405 hair-growth target was rejected for lacking a formal diagnosis. The follow-up identifies PP405 for hair growth, still rejects S043 when only a drug and trial start are named, still rejects N003–N005 and the unrelated S021 roundup, and still identifies S028 suzetrigine. The pipeline's corresponding reading instructions were kept consistent.

## Evidence and limitations

The corrected service was run locally using the actual current handler and provider, live trial/research sources, refresh requests, no shared result cache, and five-per-minute pacing. Thirty-six readable cases received HTTP 200.

Browser collection uses the actual extension collector, either directly in live Chrome 157 or replayed on public DOM captured that day. TikTok cases were re-collected live with matching addresses and canonical metadata. S047 also used the actual visible-media inspector and one bounded current video frame. Its caption and frame did not identify the treatment sufficiently. No full video, audio transcription, signed-in content or installed-popup run is claimed.

S037 remains blocked because public YouTube navigation repeatedly failed to complete in the test browser. S046 identified the USAG-1 claim but found no likely registry candidate and is partial. The 17 review rows retain concrete reasons: ambiguous multiple claims, incomplete captions, vague agents, trial-start framing or conflicting source content. Candidate scores do not verify a reported study's identity or clinical truth.

Only structured result summaries, timestamps, build fingerprints and adjudications are retained in the repository. Source text, DOM and screenshot inputs were temporary outside it. The durable corpus cache was backed up before updating its structured responses.

## Checks and Sheet update

- 265 extension/service regression checks passed.
- 15 pipeline lookup checks passed.
- 9 corpus cache/assembly checks passed, including preservation of a blocked rerun over an older successful cache answer.
- Extension build succeeded; OpenSpec strict validation and whitespace checks passed.
- The existing Google Sheet was updated in place. Its 37 target rows, Findings and Key were read back and matched exactly. Untargeted row values, status dropdowns and Summary formulas were preserved.
- AA:AD record last-tested time, tested build, deployed-site result and extension reading method. Status color rules now compare text correctly; workbook generation preserves the same comparison semantics.
- Direct browser preview was unavailable; native values, formulas, dropdowns, wrapping, header formatting and conditional-format metadata were checked instead.

Sheet: https://docs.google.com/spreadsheets/d/15DclgztI5Pbh-wOpHzi7ITtOFSCgke2yrba7LRzcoxA/edit

Per-row results: `extension/test-corpus/reruns.json`. Structured run evidence: `extension/test-corpus/runs/2026-11-15.json`.
