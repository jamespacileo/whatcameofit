# 13. A claim can start with a registry record

**Superseded on 2026-11-20.** The operator removed claims and the claims pipeline that day. Nothing in this repository acts on this decision any more; it is kept as the record of why the removed code worked as it did.

Date 2026-11-18. Status accepted. Implementation is tracked in `openspec/changes/archive/2026-11-19-registry-drafted-claims`.

## Context

The [Claim](../../GLOSSARY.md#glossary) glossary entry and the product introduction in [CLAUDE.md](../../CLAUDE.md) and [PRODUCT.md](../../PRODUCT.md#product-purpose) grew out of tracking reported medical breakthroughs. The [trial-first route](../../openspec/changes/trial-first-route/design.md) gave an uncited trial its own registry page and required a published claim for the report linkage.

The operator asked to cover every active Phase 2 or 3 interventional trial and every Phase 2 or 3 interventional trial that actually completed in 2026. A registry can establish what a trial tests and why it was registered even when a news report or paper is absent.

## Decision

- A claim represents one intervention or complete regimen and one indication. A treatment, prevention, diagnostic, or other clinical use is recorded according to its evidence.
- A claim records its drafting source. Registry drafts record the exact registry trials used, with their provenance. First reported date and article wording become available when a source article is linked.
- Reuse an existing claim when the full regimen, indication, and use match. Trial-arm evidence and the condition establish the scope. Preparation verifies links through the existing match rules.
- A registry-drafted claim earns its status from approved evidence events and follows the release audit for new backfill claims.
- This supersedes the claim-creation decision of 2026-11-16 in `trial-first-route` for the registry coverage set. A trial keeps its registry page and links to its published claims. Whether a report is linked depends on the source articles those claims actually carry.

## Consequences

The Claim and Source article glossary entries, the first product-description lines in `CLAUDE.md` and `PRODUCT.md`, and the trial-page wording and report-linkage rule in `trial-first-route` must reflect the new drafting source. Rollout verifies that the claims can be browsed and found by search in production.
