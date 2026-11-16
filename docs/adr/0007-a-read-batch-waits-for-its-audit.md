# 7. A batch of read claims waits for its audit before any export publishes it

Date: 2026-11-16. Status: accepted. Change: `openspec/changes/social-link-backfill`. Amends 0001 for claims drafted by a link lead's read.

## Context

The link backfill reads shared links in batches of a few hundred, and `thenwhat prepare --pending` approves each drafted claim by rule once its registries have been searched (ADR 0001). A second session audits each batch before it is published: it reads every approved match and archives what is wrong.

On 15 and 16 November 2026 that order broke. Several sessions and a Codex run export the whole database for their own pull requests, and an export publishes every approved, unarchived claim. Claims prepared minutes earlier went live before their audit, twice. Keeping them archived until audit was tried, but archiving means "taken down" and an unarchived claim has to be put back by hand one at a time.

The operator chose, on 16 November 2026, a mark on the claim over a separate staging database: one column set by `prepare`, skipped by every export, cleared by the audit.

## Decision

- When `thenwhat prepare` approves a claim that a link lead's read drafted, it also marks the claim awaiting audit.
- Every export leaves out a claim awaiting audit, whoever runs it, and says how many it left out. Such a claim is never published, so it gets no published time and its address never answers 410.
- `thenwhat audit clear <slug>…` releases claims whose audit passed. A claim that should not be published is archived instead. `thenwhat audit list` shows what is held.
- Unarchiving a claim does not clear its mark.

## What does not change

Claims, matches and events are still approved by rule, and an approved claim stays approved while it is held. The audit is not a review gate for a person and records no review decision: it decides only when a batch goes out. Claims entered by the operator, and claims already published, are never marked. Scores are shown as before.

## Consequences

- No export, by any session, can publish a batch before its audit.
- A new article that a read attaches to a claim already published is not held: it reaches the site with the next export, as before. The audit covers new claims only.
- Clearing is a step the auditor must not forget; `thenwhat export` reports the held count every time.
