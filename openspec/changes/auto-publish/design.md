# Design

## Decisions taken by the operator (2026-11-13)

| Question | Decision |
| --- | --- |
| What must a claim pass before it goes live? | Nothing beyond the pipeline's own checks. A source with several candidates and no confident single match is published too, as a list. |
| Mark automatic pages? | No. Every match shows its confidence instead, for automatic and reviewed matches alike. |
| Confidence form | Word and percentage, "High match · 92%", reasons one tap away. |
| Low-score sources | Published. Up to five candidates. With none above low: "No close match found", then the list. |
| Where a source lives | Its own page, `/source/{outlet}-{slug}`. |
| What archive does | The address answers 410 with a short note; feeds, sitemap, lookup and data file drop it; the database keeps it. |
| How the admin archives | CLI first, then a private web admin behind Cloudflare Access. |

## Decided by rule

Approval stays a review state, so the status rules, the export and the history keep working unchanged. What changes is who decides:

- **Draft claim:** with `APPROVE_DRAFTS_BY_RULE` on, approved by rule when extraction output passes validation, the claim is not a duplicate and the intervention it names is a name. A draft naming a description is rejected by rule and kept. Output that never validates saves nothing, as before. Off by default.
- **Candidate match:** approved by rule when it was scored with the claim's indication and its score is at or above `MATCH_ACCEPT_ABOVE`. Candidates scored without the indication are never approved by rule. Under `MATCH_REJECT_BELOW` it is rejected by rule as today. Between the two it stays pending: it does not count toward the status, and the claim page and its source page show it as a candidate with its score.
- **Event:** the existing confidence threshold (`REVIEW_CONFIDENCE_THRESHOLD`, 0.95) now applies to follow-up paper events too. A follow-up showing both signs scores 0.9, so it is approved by rule only once the threshold is lowered to 0.9. Manually entered events are a person's own entry and are approved as entered.
- **Failure flag:** still only a person, with a source URL.

`MATCH_ACCEPT_ABOVE` has no default in code. It is set in `.env` from the lookup's measured agreement with the reviewer's past approvals (`live-lookup`'s measurement), and `0` or unset turns approval by rule off, so nothing is approved by score until the operator sets it.

## Confidence words

The site owns the words. The export carries the score and its reasons. Bands, from the score: high at 0.8 and over, medium from 0.5, low under 0.5, set in `site/src/lib/confidence.ts` with the rest of the site's confidence wording. A reviewed match keeps its score; a person's approval does not raise it. This replaces the live-lookup line "Reviewed claims SHALL NOT acquire model confidence scores"; that change is not archived yet and is corrected when it is.

## Source pages

A source is an article or post the pipeline read: its address, outlet, title and date, never its text. It links to one claim when exactly one candidate claim is approved for it, else to up to five candidates ranked by score. The slug is the outlet's short name and a slug of the title, made unique with a number. Source pages are in the sitemap and archivable like claims.

## Archive

A claim or source carries `archived_at` and `archive_reason`. The export leaves archived items out of everything and adds a list of archived slugs with their dates. The build writes that list for the Worker, which answers those addresses with 410 and a short page: "This page was taken down on {date}." The reason stays in the database. Unarchiving clears the fields; the next export restores the page.

## The assistant decider

Assistant decisions no longer hold a claim back, since rules now publish. `checked_by_person` stays in the export and the data file. The preview mode loses its purpose: `export --preview` is removed and the export's `preview` is always false. The site's preview band stays in code for exports made before the change, and never shows on a current one.

## Open questions

0. **Evidence stage.** A claim with no trial takes its status from the confirmed evidence stage, which today only a person confirms. Until the suggested stage is confirmed by rule too, a rule-approved claim with no trial has no stage. Proposed: confirm the suggestion by rule when its probability is at or above the event threshold.

1. **Reader lookups.** Should an address a reader looks up become a source page? It would grow the site fastest, but the privacy page promises that a pasted link is not tracked. Not in this change; it needs the operator's decision and a privacy page change.
2. **The threshold's first value.** Proposed: the lowest score at which the lookup's past answers agreed with the reviewer at 95% or better.
3. **Archive notice wording.** Proposed above; the reason is not shown publicly.
