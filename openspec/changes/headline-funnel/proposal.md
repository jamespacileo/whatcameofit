# Proposal

## Why

On 2026-11-17 the production database held every interventional trial on ClinicalTrials.gov (467,064) and 2,041 claims. Of the 102,053 trials that are under way or ended in 2026, 1,741 are cited by a claim: 1.7%. The routes that look for news from a trial's end (`trial-first-route`, capability `trial-coverage`) are bounded by one source, a news index that allows 4,000 requests a week, and the two routes that would widen it (a full-text news search and a mentions index) were decided "not now" that day because they cost money.

Five measurements taken the same day, all read-only, show two free routes that the existing order does not have (`design.md`, Context):

1. **Public headline files hold the reports.** One weekday of a public article list is 482,387 headlines in 132 MB, fetched in 25 seconds. Matching it by rule against the stored trials' names left 3,193 headlines. A decision step given the headline alone labelled 243 of the 2,588 distinct ones as treatment reports, and about 86% of a judged sample of those were.
2. **Rules alone are not enough, and one of them is wrong for this job.** Before the decision step, about 15% of the rule's hits were treatment reports. Requiring a word of the trial's condition in the headline kept only 85 of the 243 reports.
3. **A model with a search tool finds reports for a trial at no charge, slowly.** One trial a task, on a subscription: 87 of 200 trials got a lead, about 85% of a judged sample named the right treatment for the right condition, at about 325 trials an hour whatever the number of workers.
4. **Most of what both routes find is on no outlet list.** 78% of the search route's leads and 95% of the headline hits are on outlets the pipeline does not list, many of them a sponsor's own release.
5. **A third of the stored search names are ordinary words.** "First", "more" and "women" are stored as the names of interventions, and the news search sends them.

So the work is not another search per trial. It is to take in headlines in bulk, keep the few that name a tracked treatment, let the existing triage and read do what they already do, and add the slow free search as the last route for what stays empty.

## What Changes

- **Headline files become a source of leads.** A file of headlines published by a third party is loaded as addresses, outlets, titles and dates only. A headline is kept when it names a tracked treatment by a rule, and becomes a link lead with the reason it was kept. A headline that names none is counted and not stored.
- **The keep rule is its own rule, looser than a link.** It decides only whether a headline is stored. It does not link a lead to a trial: that stays with `trial-report-links`, unchanged. A word of the trial's condition is not required to keep a headline.
- **Kept headlines go through the path that exists.** Screening, triage, the page reader, the same-claim decision, drafting or joining, `thenwhat prepare --pending`, the audit hold. Nothing in this change approves, publishes or sets a status.
- **Leads that tell one story are grouped before they are read.** A group orders the reading so that one story costs one or two reads, not one for each outlet that ran it. A group drops nothing and decides nothing.
- **A search by a model is a route, the last one.** A service on the pipeline's own machine hands a trial to an agent and takes back addresses. The agent searches and opens no page. What it reports becomes link leads. It can create or change no claim, match, event or status.
- **Article leads the news search already stored enter the same path.** 44,166 article leads sit in the store and no step reads them. Each is carried into the lead path once, as a link lead with its reason.
- **Two routes join the fixed order of `trial-coverage`**: headline files after the stored leads matched on a fingerprint, and the search by a model last.

Not in this change:

- A regulator's filings index asked by registry number. It was measured and is recorded in `design.md`, and is left out because a filing has no headline for triage to score.
- Any paid search. The prices read on 2026-11-17 are recorded in `design.md` and nothing here needs them.
- A classifier for headlines that name no tracked treatment. That is `work-reuse-and-metrics`, capability `lead-prefilter`.
- A change to what makes a name telling or a link strong (`trial-report-links`), to triage's thresholds, to the outlet list, or to the audit hold.
- Whether a sponsor's own release may be a source article. It is the operator's decision and is asked before any build (`tasks.md`, section 1).
- Lighter publishing for claims these routes draft.

## Capabilities

### New Capabilities

- `headline-files`: what a headline file is, what is read from it and what is never read, the rule that keeps a headline, what a kept headline becomes, and what the load reports.
- `lead-story-groups`: grouping stored leads that tell one story, by a versioned measure of their titles, and what a group may and may not change.
- `agent-search`: the service that hands trials to a searching agent and takes back addresses: what it hands out, what it accepts and refuses, what it stores, and what it never exposes.

### Modified Capabilities

- `trial-coverage`: two routes are added to the fixed order. This capability is created by `trial-first-route` and is not yet synced; the requirements here are added beside that change's and apply after it.
- `article-leads`: an article lead is carried into the lead path once, and is still not a source article.

## Impact

- **Pipeline**: a new loader and a script that fetches headline files; one step that keeps headlines; one step that groups leads; one step and one small service for the search route; a one-time carry of article leads. No change to triage, the read, preparation or the export.
- **Database**: link leads gain a reason for leads that no person shared; a store of story groups; ledger entries for the new steps. New migrations, not a regenerated one.
- **Sources**: `docs/sources.md` gains entries for the headline files and for the search tool, each written before its client.
- **Machines**: everything runs on the one writer. The service listens on the loopback address only. Headline files are staged outside the repository.
- **Spend**: the headline route adds triage calls, estimated under 100 US dollars for January 2025 to November 2026 from this month's recorded cost. The operator sets the share before a run.
- **Glossary**: headline file, kept headline, story group and agent search are added to `GLOSSARY.md`.
- **Unchanged**: the site, the export's shape, the extension, status rules.
