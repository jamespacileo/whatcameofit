# Design

## Claim identity after a read

The source-reading seam joined different vaccine products when both were extracted as
COVID-19 vaccine for COVID-19: literal equality bypassed the same-claim decision. Remove
that shortcut. Offer the same maximum eight candidates and add each side's existing
summary, capped at 500 characters with marked truncation, to the one identity decision.
Prioritize the exact name-and-condition pair before applying the eight-candidate limit;
other conditions of the same intervention must not crowd that candidate out.
Preserve complete intervention and explicit patient-setting restrictions in its prompt.
Use the existing extraction call to prefer a specific product name or code when supplied.

An identity refusal can leave the literal names already occupied. Record that lead as
`identity_unresolved`, with the overlapping slug, rather than attaching it anyway or
failing duplicate creation repeatedly. This is a completed, visible outcome, not an
additional publication approval step. Off-topic business news that reaches identity
comparison records the same unresolved collision before its no-claim fallback.
Migration 0023 expands the existing read-outcome
constraint. Include the new outcome and identity/treatment-kind costs in the funnel.
Already-tracked URLs and completed leads still require no model calls; only a new read
that formerly took the shortcut gains one bounded decision. Existing acceptance
thresholds, source pacing and automatic publication rules remain unchanged.

## Context

See proposal.md and the released evidence in the visible-content-lookup change.
The unit of identity remains one intervention for one indication. Current main
already has bounded source retrieval/reuse, shared pacing and concurrent pipeline
reading; those systems must be measured and reused, not duplicated.

## Goals / Non-Goals

Correct false card associations and current-slide capture, then audit every row
against released behavior. This does not make unavailable video or ambiguous
claims positive or grant additional permissions. Publication auditing also requires correcting the unknown-stage fallback described below.

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

Facebook's numeric detail URL and rendered pfbid permalink can differ. Require the
public preview URL to match the current post/video identity, then use its caption
prefix to select a unique visible message. Read that message only, never its parent
post or comment tree. Bind media through the preview image's origin/path, ignoring
CDN rendition parameters. Missing or ambiguous media refuses capture. Explicit
combination instructions preserve all named components when comparison arms are
also discussed. This correction advances the shared answer cache to six and the
local reader cache to seven; public registry/source caches remain reusable.

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

## Background-card boundary found during coverage work

The normal prepare/terms workflow approved bimagrumab and semaglutide separately as exact intervention vocabulary terms for the combined regimen. The term classifier had received component names as aliases. A drug source containing only one known component could similarly produce a false whole-regimen drug link. Exclude explicitly named components from whole-name candidates and registry-filed intervention terms before paid classification; describe the complete regimen in the model prompt. Keep whole-regimen aliases eligible. Apply the same boundary when exporting legacy approved vocabulary/drug cards and omit a suppressed component drug's derived target. Preserve original review decisions and clinical status. No broad class-membership or clinical equivalence is inferred by this string boundary.

## Evidence-stage gap found before publication

The private export contained 110 prepared claims with no confirmed evidence stage, including reports explicitly describing studies in people. Twenty-six therefore inherited `preclinical_only` despite the absence of a confirmed laboratory/animal stage. This resolves the evidence-stage open question in the auto-publish design: a stored valid suggestion can be confirmed by rule only while the claim stage is empty and both its chosen-stage probability and recorded confidence meet the existing review threshold. Respect the draft-rule switch, preserve confirmed stages and human labels, and reuse the existing decision instead of paying for another reading. A low-confidence or unavailable stage stays unknown. With no approved trial, unknown now means `no_trial_found`; only confirmed animal/in-vitro evidence means `preclinical_only`. Approved trial, regulatory and retraction precedence stays unchanged. No model directly chooses a clinical status.

## Vocabulary evidence omitted from term checks

The daraxonrasib candidate was found through the vocabulary's verified entry name, but the classifier saw only the older preferred label RAS Inhibitor A122 and no definition. Include the recorded entry-name evidence in the existing candidate prompt. An entry name may denote a narrower concept, so it is evidence for the existing classifier, never an automatic exact approval. Keep ordinary scored-term reuse. An explicit `terms SLUG --rescore-pending` rechecks undecided subject terms for named claims only, using the same thresholds and decision logs. It never changes approved/rejected links or past labels; a failed recheck retains the earlier fit and score. The component boundary still runs before paid work. This adds no routine model calls and does not widen claim/card identity matching.

## Explicit trial populations

Corpus A041 describes daraxonrasib for previously treated metastatic pancreatic cancer but also links RASolute 303 (NCT07491445) as a separate first-line study. The released answer retained the correct primary indication yet scored that first-line record as a full match. Trial number discovery is valid; its mention is not evidence that it matches the primary claim. Tighten the existing bounded scoring question in both implementations: explicit prior-treatment, disease-stage, biomarker and age restrictions belong to the indication; incompatible settings use `other_indication`. Missing compatibility remains uncertain. A claim without a restriction must not acquire one. Preserve the existing source-number ranking and show the more accurate different-condition/patient-group/setting explanation. No model calls, input budgets or retries are added. Advance shared answers to version seven and local answers to eight, leaving registry/paper/source caches unchanged, and release Safari 0.9.9.

## Background batch checkpoints and incurred usage

The missing-background run completed many claims before a MeSH outage on the vagus-nerve claim. One transaction covered the entire command, so the failure discarded earlier terms, decisions, cached responses and model usage. Commit each completed claim before starting the next. Preserve the command's non-zero source failure; do not imply every selected claim succeeded. Ordinary repeats reuse earlier scored terms. Commit model usage independently after each provider call because incurred cost cannot be undone by rolling back claim work. Use the existing engine/session and connection-bound savepoint pattern already used for source turns. Shared source pacing, spending limits, scores and retry counts remain unchanged. The failed historical run's usage cannot be reconstructed from its console output; record this accounting gap without inventing token counts or costs.

## Alternate-name scope before publication

The unpublished snapshot contains individual weight-loss medicines as synonyms for the class, ketamine as a synonym for esketamine, and components as synonyms for complete regimens. Such aliases can turn a literal name comparison into a wrong card association. Tighten the existing extraction field instructions: an alternate name must retain the complete intervention's scope, including explicit stereochemistry, route and regimen. Reuse the existing component boundary before storing new synonyms, including brands with an explicit regimen alias. This adds no model step. Correct proven older aliases separately with a before/after audit; do not infer clinical equivalence or silently rewrite trial decisions. Broader, related and ambiguous names still need evidence; string parsing is not a general equivalence classifier.

## Intervention details in trial scoring

An unpublished inhaled-interferon claim included NCT04324463, whose recorded intervention description specifies subcutaneous injection. Both scorers previously omitted descriptions and arm membership. Include these existing registry fields, with conditions and the brief title first, before the less essential duplicate official title. Keep the 1,500-character record limit; cap individual titles at 240 and descriptions at 350 characters, marking every shortened field and any shortened record. Explicit route, formulation, stereoisomer and regimen conflicts mean `not_a_match`. Separate A and B arms do not establish A-plus-B treatment. Missing or truncated compatibility evidence retains uncertainty; broad claims gain no unstated restriction. No additional source/model request or retry is introduced. Shared answers advance to eight and local answers to nine; Safari advances to 0.9.10. Independently public source caches remain reusable. The proven wrong-route private association is rejected as assistant, preserving its original record and decision history.

## Origin start timestamp

A production-CI regression measured paper-source starts 119 ms apart against a 120 ms minimum. The timestamp was taken just before invoking fetch, so synchronous request setup could cross a clock tick before the request began. Take the timestamp immediately after invoking fetch without awaiting its response. Subsequent starts remain serialized and paced, while response bodies still overlap. Preserve source limits, cancellation and deadlines; the regression includes synchronous setup rather than weakening the spacing assertion.


## Native Safari presentation correction

Native Safari 0.9.10 exposed a presentation defect on corpus A041: the scorer correctly assigned zero confidence to a cited first-line study, but the shared presenter promoted every explicit citation into possible matches and retained source-first order. Separate citation provenance from compatibility. Valid match decisions at the existing 0.5 display threshold lead in descending score order; other directly or paper-cited records remain in a collapsed, explicitly unestablished section with their own score and explanation. Share the ten-record cap across groups. Existing cached raw answers are re-presented correctly without invalidation or another paid call. This supersedes the earlier decision to preserve source-number priority in the possible-match list. Safari 0.9.11 uses the same presenter.

## Historical background gathering reasons

A correction can remove an approved trial after a vocabulary term was gathered. Keep the original stored gathering counts and reading date, but word the public registry-filing reason in the past tense and explicitly say when the term was gathered. This preserves provenance without presenting a historical trial set as the current set. No new scoring or source request.

## Registry condition-query refusal

ClinicalTrials.gov refused the precise first-line nonsquamous lung-cancer condition as too complicated. The client already tries a condition's telling words after a valid empty response, but a parser refusal skipped that bounded fallback. Distinguish an explicitly named condition-field refusal from treatment and unknown-field refusals, and share the existing two-wording search between broad-name and search-phrase discovery. Try a distinct fallback at most once; retain the hundred-candidate cap and source pacing. If no usable query remains, report the refusal rather than claiming a successful empty search. Only candidate discovery wording changes: the stored claim and full indication used by scoring remain unchanged. No model call or additional ordinary-success request is introduced.
