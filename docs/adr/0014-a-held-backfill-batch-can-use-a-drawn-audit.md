# 14. A held backfill batch can use a drawn audit

Date 2026-11-18. Status accepted. Amends [ADR 0007](0007-a-read-batch-waits-for-its-audit.md) through `openspec/changes/archive/2026-11-19-registry-drafted-claims`.

## Decision

The pipeline draws and records the audit sample for a held batch using a reproducible seed. The operator configures the sample size and the tolerated share of wrong claims. The pipeline uses each claim when the batch is smaller than the configured sample. Each judgment records its reviewer, including assistant judgments. The operator can spot-check a drawn share.

An entire batch remains held when the sample is incomplete or above the configured error tolerance. The release command requires the configured threshold and a complete sample. Its result records which batch and judgments support the release.

## Continuing rules

Every export excludes held claims and reports the held count. Match and claim approvals use the existing rules. A release changes publication eligibility alone. A released claim carries a human-reviewed label only when the underlying review was actually done by a person. A report added to an already published claim follows the established export path for that claim.
