# 4. An uncertain reading is shown with its score; it is not held for review and never sets a status

Date: 2026-11-15. Status: accepted. Change: `openspec/changes/archive/2026-11-18-social-link-backfill`. Extends ADR 0001.

## Context

ADR 0001 decided that items are approved by rule and published without waiting for a person, with every match's confidence shown. Two things were left between its lines. A trial match in the middle of the score range was already exported as a candidate, shown apart and counted for nothing. An evidence stage had no such middle: it was confirmed by rule at the review threshold or it was not shown at all, and the project's guardrail said the *reviewed* stage decides between "preclinical only" and "no trial record found".

The first batches of claims drafted from link leads made the gap visible. 109 claims were approved by rule; 42 of them had a stage reading under the threshold. The choices offered were to have a second session review each one or to leave them empty.

The operator decided on 2026-11-15: "we never really want human review, only for cleanup after flagging by admin. surfacing confidence bands/scores should help the user make an informed decision." And, on the lower band: the claim is published, the low-band item is shown with its score and reasons, and it cannot set the status.

## Decision

- A reading a model gives with a score has **two bands**, set by two thresholds in settings.
  - **Sure band**: confirmed or approved by rule. Only items in this band are inputs to a status.
  - **Lower band**: published with the claim, shown apart, marked with its score and what else the reading weighed. Never an input to a status, a count or the open data file.
- Under the lower threshold an item is not shown.
- No band waits for a person or for a reviewing session. A person's part is to archive or correct what is wrong after it is flagged.
- This holds for the evidence stage from this change on. Trial and paper matches already work this way ("approved" and "candidate" in the export).
- There is one path: the same reading, the same thresholds and the same display for every claim. A lower-band reading is never promoted because nothing better was found.

## What does not change

Status is derived only by the pure rules in `pipeline/src/thenwhat/status`, from approved events and the confirmed stage. A claim with no approved trial and no confirmed stage reads "no trial record found". A confirmed stage is never overwritten by a rule. No verdict wording, no medical advice.

## Consequences

- A reader sees more uncertain material than before, each piece labelled. The label is the safeguard, so the site must show the score wherever it shows the item.
- A stage reading that is wrong but sure is confirmed and decides between the two no-trial statuses until someone archives or corrects it. The threshold for the sure band is the control on how often.
- The guardrail in `CLAUDE.md` now says "confirmed", not "reviewed".
- A reading is exported only while the stage is empty, and with an empty stage and no trial the status is "no trial record found". So a page never shows "preclinical only" beside a low-confidence reading of a study in people: "preclinical only" needs a confirmed stage, and a confirmed stage has no reading beside it.
- Neither number was measured. The show probability (0.5) is "the reading's first choice has a majority"; the floor for listing another stage (0.05) only keeps noise off the page. Both are settings or constants to revisit once readings have been audited against their articles.
