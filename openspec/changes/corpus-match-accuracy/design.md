# Design

## Context

See proposal.md and the released evidence in the visible-content-lookup change.
The unit of identity remains one intervention for one indication. Current main
already has bounded source retrieval/reuse, shared pacing and concurrent pipeline
reading; those systems must be measured and reused, not duplicated.

## Goals / Non-Goals

Correct false card associations and current-slide capture, then audit every row
against released behavior. This does not make unavailable video or ambiguous
claims positive, grant additional permissions, or change clinical status rules.

## Decisions

- Add explicit indication to the public lookup entry. Compare normalized condition
  and whole-intervention aliases deterministically in both lookup implementations.
  Combination names compare their complete component set; a component alias cannot
  stand in for the full regimen. Unknown condition equivalence is left unconfirmed.
  Model-based card ranking would add expense and another uncertain association.
- Bind an Instagram carousel through its unique metadata image and its containing
  slide list, bounded by its clipping viewport. Only one visible media item in that
  list can be selected. Check overflow clipping again when computing screenshot
  bounds. Broad ancestor/main fallbacks would admit recommendations.
- Preserve exact source-address mappings and local/shared reuse. Invalidate prior
  answer versions once for this release; no per-row fresh paid reruns when identity
  can be verified from the index and current evidence.
- Separate structured trial/card evidence in the corpus and append precise Sheet
  columns. Keep original rows and formulas; verify edits by read-back.
- Live signed-in checks exposed LinkedIn sidebars and Bluesky replies in the generic
  reader. Bind each platform's post container through its own permalink before
  collecting text or pixels; missing/ambiguous identities remain unread. Invalidate
  local answers from the broader reader while retaining correct independently public
  shared article results, avoiding unrelated paid rereads.

## Risks / Trade-offs

- Conservative condition comparison can miss synonymous descriptions → record
  absence explicitly and add evidence-backed aliases or coverage only when proven;
  never silently broaden one indication into another.
- Social layouts can change → synthetic boundary regressions plus current live DOM
  and installed Safari checks; missing structure fails closed.
- Model readings vary → confirm the affected boundaries with real provider checks,
  retain exact builds/methods and avoid presenting a caption-only test as a video test.

## Migration Plan

Add the index field compatibly, bump result-cache versions and Safari build, pass
protected tests and independent review, deploy through CI, install the signed app
with a rollback copy, and rerun affected URLs against production. Complete the
full-sheet audit in batches while recording remaining uncertainty. Roll back with
the previous release/app if a new issue prevents reliable reading.
