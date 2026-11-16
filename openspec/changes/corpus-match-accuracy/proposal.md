# Proposal

## Why

Released corpus checks found a trial match accompanied by a knowledge card for a different condition, and an Instagram carousel whose hidden first slide supplied the screenshot boundary. The operator has asked for continued fixes, production releases and an accuracy/efficiency audit of every article and social URL in the Sheet.

## What Changes

- Show separate matches and cards for each identifiable independent claim on a page, as the operator chose on 2026-11-16; keep genuine combination regimens together and retain uncertainty for unidentified claims.
- Narrow ambiguous study acronyms once by the reported condition, preserving candidate limits, per-claim query identity and full clinical scoring.
- Revalidate the extension's published card index when its popup opens, using conditional requests to avoid transferring an unchanged index and retaining bounded offline fallback. Newly published exact-source cards must precede saved clinical answers.
- Require the same condition and complete intervention when associating a live answer with an existing card; uncertainty must not become a positive association.
- Respect explicit patient populations and treatment settings when scoring registry trials, including a separately linked first-line trial in an article about previously treated patients.
- Capture the currently visible slide within an identity-bound carousel, respecting ancestor clipping and the existing consent/privacy limits.
- Record trial matching, card identity, release and method separately for all corpus rows, including legitimate negatives and inaccessible content.
- Preserve accurate background-card scope for complete regimens, and prevent unpublished claims with an unknown evidence stage from being labelled preclinical. Confirm a sufficiently confident recorded stage by rule while preserving human decisions.
- Reuse exact published address mappings and completed eligible results before paid work, and measure fresh/reused work without weakening accuracy.
- Reassociate reused clinical answers with the available publication index, so newly published cards appear and removed or corrected associations are not retained in old answers.
- Preserve completed background-card work and provider usage when a later source operation fails.
- Keep extracted alternate names within the complete intervention's scope and correct known overbroad unpublished aliases before publishing new cards.
- Preserve registry intervention descriptions and arm membership for route and regimen comparisons within the existing scoring limit.
- Request those details in registry searches as well as individual records, include study type and arm roles, and distinguish comparator/background use, combination-only trials and expanded access from a trial of the claim's complete intervention.
- Recover from an explicitly refused registry condition with the existing bounded discovery fallback, while preserving full clinical scope for scoring and keeping treatment-name refusals explicit.
- Compare claim summaries even when names are equal, record unresolved identity collisions without repeated work, and retain specific product names supplied by articles.
- Reduce optional substance-source outage waits while preserving source-declared retry delays, successful-response reuse and explicit failure reporting.

## Capabilities

### New Capabilities

- `live-lookup`: adds a strict card-association requirement to the capability being introduced by the active `live-lookup` change. Its name-only association requirement is superseded by this change's intervention-and-condition requirement.
- `lead-reading`: adds summary-aware identity checks to the capability in the active `social-link-backfill` change, superseding its exact-name join shortcut.

### Modified Capabilities

- `paper-facts`: identify human/animal indexing terms as subject headings, without implying a trial in living participants.
- `source-clients`: permit one existing condition-keyword fallback after an explicit condition-field parse refusal, without rewriting treatment names or expanding candidate limits.
- `knowledge-cards`: keep component cards from representing complete regimens; include verified vocabulary entry-name evidence in term checks and support explicit, bounded rereads of undecided terms.
- `llm-usage`: commit incurred provider usage independently of the caller's transaction.
- `claim-extraction`: instruct exact-scope alternate names and exclude explicit regimen components before storing new synonyms.
- `claims`: allow evidence-stage confirmation by the separately specified rule.
- `review`: confirm eligible recorded evidence stages by rule without repeated model calls.
- `status-derivation`: unknown evidence stage gives no trial record found, not preclinical only.
- `site-publishing`: no-trial explanations and summaries do not infer a human study from an unknown stage.
- `browser-extension`: bound current-slide capture and clipping.
- `extension-test-corpus`: separate, reproducible card and trial accuracy evidence across the complete corpus.

## Impact

Public lookup index, Worker and Python lookup matching, extension collector/capture/cache, corpus tooling and existing Google Sheet. No additional provider call for card matching, no new permissions, no video/audio download, and no fabricated positive results or medical advice. Deployment continues through reviewed CI; Safari updates preserve signing and rollback.
