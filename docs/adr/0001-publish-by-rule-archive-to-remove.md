# 1. Publish by rule; the operator takes pages down by archiving

Date: 2026-11-13. Status: accepted. Change: `openspec/changes/auto-publish`.

## Context

From the start, nothing reached the public site until a person approved it: every draft claim, every trial match and every event below a confidence threshold. That kept the site accurate and kept it small. By 12 November 2026 it tracked 104 article addresses, all entered and checked by hand. The live lookup already showed readers automatic results with a match score and its reasons, and readers were told plainly how sure the software was.

On 13 November 2026 the operator decided that publishing must be automatic. The admin's work is to take wrong items down, and the pipeline must be good enough to be trusted with little human help.

## Decision

- Items are approved by deterministic rules and published without waiting for a person: validated drafts, candidate matches scored for the claim's indication at or above `MATCH_ACCEPT_ABOVE`, and events at or above their confidence threshold.
- Every match the site shows carries its score as a word and a percentage, with its reasons. Pages carry no "unreviewed" marking: the score is the disclosure.
- A source with no single confident claim is published as a ranked list of up to five candidates.
- The operator removes an item by archiving it. Its address answers 410, and the database keeps the record.

## What does not change

Status is derived only by the pure rules in `pipeline/src/thenwhat/status`, from approved events. No model decides a status. No verdict wording, no medical advice, no article text. A failure flag is set only by a person with a source. A registered trial is never presented as a treatment option.

## Consequences

- The site grows with the pipeline rather than with review time.
- Mistakes will be public until archived. The visible score is meant to make readers expect them, and archiving has to be quick: a CLI first, then a private web admin.
- `MATCH_ACCEPT_ABOVE` becomes the most important setting in the project. It is unset by default, which turns rule approval off, and it is chosen from the lookup's measured agreement with past human approvals.
- The assistant decider no longer holds claims back, and the preview mode is removed.
- The first export after this change publishes every approved claim in the database, including ones an assistant decided.
