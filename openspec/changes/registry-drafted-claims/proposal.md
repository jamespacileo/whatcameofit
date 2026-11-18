# Proposal

The [rollout handoff](handoff.md) records current evidence and the outstanding gates for this change.

## Why

A claim exists today only when a news article reported it. On 2026-11-17 the production database held 467,064 registry trials and 2,041 claims, and 1,741 of the 102,053 trials that are under way or ended in 2026 were cited by a claim: 1.7%. Searching for news cannot close that, because most trials have no report (`headline-funnel`, `design.md`).

The operator decided on 2026-11-17 that every named trial is to be cited by a claim, and that where no report exists the claim is drafted from the registry record itself. The answers, given to twelve questions that day, are recorded in `design.md` under "What the operator decided". This supersedes the decision of 2026-11-16 that a trial no article links to has only a plain registry page with no claim (`trial-first-route`), and it changes what a claim is: one intervention for one indication, reported or not.

## What Changes

- **A claim can be drafted from registry records, with no source article.** **BREAKING** for `claims`: a claim no longer needs a source article, and its first reported date may be empty. The glossary line for Claim and an ADR say so.
- **One claim per intervention or full regimen and indication.** Grouping starts with the trial's registered treatment arms and full condition labels. A trial whose regimen and indication an existing claim is verified to hold is cited by that claim.
- **The registry can establish a primary topic.** Cancer is the primary topic when the same MeSH disease descriptor supports Cancer and an anatomical topic. Competing disease descriptors go to topic review.
- **A registry-drafted claim is prepared like any draft.** `thenwhat prepare` searches the registries for it and approves by rule. The trial it was drafted from is a candidate, scored for the claim's indication, and is not approved for having led to it. A draft whose own trial is not approved is not approved.
- **Its wording is fixed.** The claim page says, in one fixed line, that no news report is linked to the claim yet. Its headline and summary are worded by the site from the intervention and the indication, never by a model. It is never worded as a treatment a reader can get.
- **Lists can be narrowed to reported claims.** Wherever claims are listed, a reader can show only claims a report is linked to, and counts say how many of each there are.
- **When a report arrives, the claim is an ordinary claim.** The same-claim decision attaches the article, the first reported date is set, and the fixed line goes.
- **A batch is cleared on a drawn sample.** **BREAKING** for the audit of ADR 0007: a held batch may be released when a sample the pipeline draws is judged and its share of wrong claims is at or below a figure the operator sets. A new ADR amends 0007.
- **All active Phase 2 or 3 interventional trials and Phase 2 or 3 trials completed in 2026.** Include all sponsors, intervention kinds and results states. Plan the named set in batches. Trials that need further identity or indication evidence remain visible in the coverage gap and are resolved before linking.
- **Every trial keeps its own page.** The trial page of `trial-first-route` stays, and leads with the claims that cite the trial, as it already does.

Not in this change:

- A name or condition invented by a model. An optional review step selects verbatim registry evidence for a reviewer to check.
- Any route that looks for news. That is `headline-funnel` and `trial-first-route`; with this change those routes attach reports to claims that exist.
- A sponsor's release as a source article. Decided as yes on 2026-11-17 and specified in `headline-funnel`.
- A change to how status is derived. A registry-drafted claim's status comes from its approved trial events by the rules that exist.
- Serving claim pages on request. They stay built (`cloudflare-source-of-truth`, decision 8); what the build can hold is measured here before a set is published.

## Capabilities

### New Capabilities

- `registry-drafted-claims`: how a claim is drafted from stored registry trials: which trials, how they are grouped, when an existing claim is joined, what a draft holds, how it is prepared and decided, and what happens when a report arrives.
- `sampled-audit`: releasing a held batch on a sample the pipeline draws: the sample, the figure, who judges, and what happens when the figure is passed.

### Modified Capabilities

- `claims`: a claim's source articles and first reported date, for a claim drafted from registry records.
- `site-publishing`: the fixed line on a claim with no report, its worded headline and summary, narrowing lists to reported claims, and counts.

## Impact

- **Pipeline**: a drafting step over stored trials, by set; `prepare` and the rules for drafts take a draft with no article; the audit commands gain a sample. New migrations.
- **Database**: a claim records what it was drafted from; a batch records its sample and judgements.
- **Export**: each claim says whether a report is linked and what it was drafted from. `site/export.schema.json` is regenerated and the schema version rises.
- **Site**: wording for claims with no report in the site's own files; a filter and counts on lists; build time and size measured for the first set before it is published. The extension's `lookup.json` grows and is measured too.
- **Documents**: `GLOSSARY.md` (Claim, Source article, a term for a claim with no report linked), `CLAUDE.md` and `PRODUCT.md` where they say what a claim is, a new ADR for the claim, a new ADR amending 0007, `docs/backfill-loop.md`.
- **Other changes**: `trial-first-route` (its plain page for an uncited trial stays, and its "no claim" line is superseded for named trials); `headline-funnel` (its routes attach reports; what makes a trial due changes).
- **Spend**: preparation asks the registries within their allowance and calls the decision step to score candidates. The plan prints both before a set is drafted.
