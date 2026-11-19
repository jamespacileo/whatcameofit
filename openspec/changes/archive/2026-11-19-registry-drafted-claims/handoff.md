# Registry-drafted claims handoff

## Scope and release status

Link every active Phase 2 or 3 interventional trial and every Phase 2 or 3 interventional trial completed in 2026 to a browsable, searchable production claim. Create claims from registry evidence. Each claim covers one complete tested regimen and one indication. Reuse an existing claim when it covers the verified pair. [Proposal](proposal.md) · [Requirements](specs/registry-drafted-claims/spec.md)

The November 18, 2026 verification linked **831 of 27,731 eligible trials (3.0%)**. That leaves 26,900 unlinked. The registry-drafting rehearsal made zero production writes. [Coverage verification](tasks.md#2-the-dry-run-with-nothing-written)

## What is ready

| Area | Verified state |
| --- | --- |
| Registry scope | The planner handles tested arms, full regimens, clinical settings, topic placement, and reviewed scope receipts. It can check cached arm descriptions against the exact stored trial version. |
| Existing claims | The existing-only preview surfaces pending match states and scores. One verified match was taken through local approval, evidence fetch, export, search and browsing. |
| Drafting and release | Local rehearsals exercised drafting, preparation, audit holds, release, registry-only presentation, search and split-build staging. The first actual draft batch and a build from the audited real cohort remain open. |

See the [design](design.md) and [implementation and evidence log](tasks.md) for the acceptance criteria, baseline figures and checks.

## Resume here

1. **Improve grouping under tasks 2.4–2.5.** Use the detailed protocols to resolve alternatives, conditional additions, treatment sequences, background therapies and enrolment restrictions. The earlier detailed diagnostic supported five of 50 groups. The later targeted sample supported 19 of 20 added treatment settings and four complete pairs. The fresh sample of 100 combination trials surfaced five cases where an apparent combination needed review. Use these as development evidence. [Grouping tasks and results](tasks.md#2-the-dry-run-with-nothing-written)
2. **Run the independent grouping audit.** Draw 50 fresh groups outside the trials already reviewed or used to develop rules. Verify the whole regimen and indication against the protocol for every group. At least 45 must pass before drafting. Record holds, duplicate risks, elapsed time, registry requests and model spend. [Grouping design](design.md#3-grouping-starts-from-registered-arms-and-full-indications)
3. **Rehearse and audit the first 200 actual drafts.** After the grouping gate passes, run the reviewed preview, preparation and full first-batch audit. Validate the real export build and preview. The operator still needs to set `REGISTRY_SCOPE_MONTHLY_BUDGET_USD` for paid scope extraction and `AUDIT_SAMPLE_SIZE` and `AUDIT_MAX_WRONG_SHARE` for later sampled releases. [Drafting and release runbook](../../../docs/backfill-loop.md#batches-drafted-from-registry-records)
4. **Release sequentially and verify coverage.** Verify each batch on the production site before starting the next. Check the claim and trial links through browsing and search. Recount distinct eligible trials with a published claim after each release and retain unresolved trials in the denominator. [First-set tasks](tasks.md#6-the-first-set)

## Evidence locations

The Mac's external NVMe holds the frozen cohort and batch receipts in `registry-drafted-claims-dry-run-20261118`. Start with `topic-placement-audit/live-coverage.json`, `detailed-drafting-gate-audit/diagnostic-receipt.json`, `title-treatment-setting/protocol-audit-receipt.json`, and `described-regimen-choices/result.json`. The [evidence log](tasks.md) records which runs used a frozen cohort and which made registry requests.
