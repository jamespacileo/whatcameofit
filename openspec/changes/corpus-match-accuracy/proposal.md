# Proposal

## Why

Released corpus checks found a trial match accompanied by a knowledge card for a different condition, and an Instagram carousel whose hidden first slide supplied the screenshot boundary. The operator has asked for continued fixes, production releases and an accuracy/efficiency audit of every article and social URL in the Sheet.

## What Changes

- Require the same condition and complete intervention when associating a live answer with an existing card; uncertainty must not become a positive association.
- Capture the currently visible slide within an identity-bound carousel, respecting ancestor clipping and the existing consent/privacy limits.
- Record trial matching, card identity, release and method separately for all corpus rows, including legitimate negatives and inaccessible content.
- Reuse exact published address mappings and completed eligible results before paid work, and measure fresh/reused work without weakening accuracy.

## Capabilities

### New Capabilities

- `live-lookup`: adds a strict card-association requirement to the capability being introduced by the active `live-lookup` change. Its name-only association requirement is superseded by this change's intervention-and-condition requirement.

### Modified Capabilities

- `browser-extension`: bound current-slide capture and clipping.
- `extension-test-corpus`: separate, reproducible card and trial accuracy evidence across the complete corpus.

## Impact

Public lookup index, Worker and Python lookup matching, extension collector/capture/cache, corpus tooling and existing Google Sheet. No additional provider call for card matching, no new permissions, no video/audio download, and no fabricated positive results or medical advice. Deployment continues through reviewed CI; Safari updates preserve signing and rollback.
