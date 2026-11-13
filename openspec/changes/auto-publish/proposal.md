# Proposal

Status: decided by the operator on 2026-11-13. Not built. See `tasks.md`.

## Why

Every claim, match and event now waits for a person before it reaches the site. The operator's answer on 2026-11-13: "data that gets published on the site needs to be fully automated, as an admin I want the opposite aka archiving/removing published items. the pipelines need to be good enough so that we have high confidence in the results with little human assistance."

The review gate made the site accurate, but it also made it small: 104 tracked addresses on 2026-11-12, all entered and checked by hand. The live lookup already shows readers automatic results with a score and reasons. This change makes that the whole site's way of working: publish what the pipeline finds, say how sure it is, and let the operator take down what is wrong.

## What Changes

- **Decided by rule, published by default.** A validated draft claim, a candidate match scored for the claim's indication at or above an accept threshold, and an event at or above its confidence threshold are approved by rule. Nothing waits for a person before it is published. The operator can still approve, reject or change any decision.
- **Confidence on every match.** Each match a claim page shows carries its score as a word and a percentage ("High match · 92%"), with its reasons one tap away. This holds for matches a person approved too. Pages carry no "unreviewed" marking.
- **Source pages.** Each article or post the pipeline reads gets a page at `/source/{outlet}-{slug}`: its headline, outlet and date, and either the one claim it reports or up to five candidates with their scores and reasons. With no candidate above low, the page says "No close match found" and still lists them. Article text is never shown.
- **Archive.** `thenwhat archive <slug> --reason` takes a claim or source page off the site. Its address answers 410 with a short note, the feeds, sitemap, lookup file and data file drop it, and the database keeps everything. `thenwhat unarchive <slug>` puts it back.
- **Unchanged:** status is derived only by the deterministic rules from approved events; no verdict wording; no medical advice; no article text; a failure flag is set only by a person; a registered trial is never presented as a treatment option.

Not in this change: a private web admin for archiving (its own change, behind Cloudflare Access), publishing pages for addresses readers look up (see design.md), and email alerts.

## Capabilities

### New Capabilities

- `source-pages`: a page per article or post the pipeline read, with its claim or candidates.

### Modified Capabilities

- `review`: decisions by rule publish; review is for correcting, and archive takes items down.
- `entity-resolution`: a rule may approve a candidate scored for the indication at or above the accept threshold.
- `claim-extraction`: a validated draft is approved by rule.
- `site-publishing`: the gate is "approved by anyone and not archived"; archived addresses answer 410; matches show their confidence.
- `open-data`: the data file holds every published, unarchived claim and says who decided each.

## Impact

- **Database:** a migration adds archive fields to claims and a source table with its candidates.
- **Export:** source pages, match scores and reasons, and the archived list. Schema, seed export and fixture regenerated.
- **Site and Worker:** source pages, confidence on claim pages, and a 410 response for archived addresses in `site/worker/index.mjs`.
- **Rules in `CLAUDE.md`:** the review-gate lines are replaced; ADR 0001 records why.
- **Risk:** the first export after this lands publishes every claim the database holds, including ones an assistant decided. Archiving is the only way to take one down.
