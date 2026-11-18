# Design

## Context

See `proposal.md` for why. Figures were counted on the production database on 2026-11-17, read-only.

### What the operator decided

On 2026-11-17 the operator answered twelve multiple-choice questions. The answers that shape this change:

| Question | Answer |
| --- | --- |
| What closing the gap means | A claim for every trial |
| What a claim is drafted from when no report exists | The registry record itself |
| The unit | One claim per treatment and condition, listing its trials |
| Trials with no usable treatment name | Out for now; a plain registry page |
| How a claim with no report appears | The same claim page, with a fixed line that no report is linked, and a way to show only reported claims |
| The plain trial page of `trial-first-route` | Keep both: a trial keeps its page and links to its claim |
| Release of held batches | Keep the hold; audit a drawn sample |
| Which trials first | Industry-sponsored, phase 2 and 3 |

The answers on sponsor releases, spend, the subscription and the second headline corpus belong to `headline-funnel` and are recorded there.

Three figures were not given and are the operator's: the share of wrong claims a sample may hold, the sample's size, and the monthly ceiling for model spend.

### The first set

The operator broadened rollout on 2026-11-18 to all active Phase 2 or 3 interventional trials and all Phase 2 or 3 interventional trials actually completed in 2026, across sponsors and results states. The named set is `active-phase-2-3-or-completed-2026`. Combined phases qualify when they include Phase 2 or 3. Trials with unresolved identities stay in the denominator.

The 2026-11-18 coverage check found 25,898 active and 1,800 completed trials in the local snapshot. The live export linked 735 and 96 respectively.

### Original pilot estimates

Uncited trials that are under way, not yet started, or completed or terminated in 2026, with a stored search name.

| | Industry, phase 2 and 3 | Other named |
| --- | --- | --- |
| Trials | 8,755 | 34,027 |
| Distinct names | 5,017 | 14,762 |
| Name and indication pairs | 7,341 | 29,031 |
| Trials whose name an existing claim's intervention holds | 532 (123 names) | 2,950 (186 names) |
| Trials with no stored indication | 129 | 1,012 |
| Trials listing more than one condition | 2,295 | 15,225 |

The store held 2,041 claims, each with one intervention. About 20,000 of the 60,928 distinct stored search names are made only of ordinary words ("first", "more", "home", "women"), measured in `headline-funnel`.

### What exists that this rests on

- A claim needs a source article, and its first reported date is the earliest article's (`claims`).
- A duplicate claim is refused on the same indication and an intervention equal by name or synonym (`claims`, "No duplicate claims"). Two claims for one pair are merged, never archived (`claim-merge-and-rename`).
- A draft a read makes waits for `thenwhat prepare --pending`, which searches the registries and decides it by the rule for drafts, and is then held awaiting audit (ADR 0007).
- A trial matches a claim only when it tests the intervention for the claim's indication, and a candidate scored without the indication is never approved on its score.
- A registry trial in the corpus is not an evidence event (`registry-corpus`). Events come from approved matches.
- A vertical is one of a configured set; `approach-and-vertical-by-rule` compares a claim's group with the groups its trials' condition terms point to.
- The site owns all wording and the export carries codes.

## Goals / Non-Goals

**Goals:**

- Every active Phase 2 or 3 interventional trial and every Phase 2 or 3 interventional trial actually completed in 2026 is cited by a production claim that is browsable and searchable.
- A registry-drafted claim is as true as a reported one: its trials test its treatment for its condition, by the rules that already decide that.
- No claim says more than its records. A claim with no report has no words but the site's fixed ones.
- A reader can always tell a reported claim from one with no report, and can leave the latter out.
- Release keeps pace with batches of thousands without ending the hold.

**Non-Goals:**

- A claim per trial.
- Claims for trials with no usable name.
- Any judgement of how a trial turned out.
- Finding reports. Other changes do that; this one gives them claims to attach to.

## Decisions

### 1. A claim is one treatment for one condition, reported or not

The glossary's "as reported in the news" goes, and a claim records what it was drafted from: an article, registry records, or an operator's entry. That record never changes, so a reader and an auditor can always see how a claim began.

*Instead of* a second kind of record beside claims (offered to the operator, not chosen): two kinds would need two pages, two lists and a rule for turning one into the other when a report arrives.

An ADR records this, since it changes the first line of the product's description and supersedes the 2026-11-16 decision for named trials.

### 2. The drafting trial is a candidate, not an approved match

It would be simple to approve the trial a claim was drafted from, since the claim was made from it. That would be approval by construction, and the grouping rule is exactly what might be wrong: the indication the rule read may not be the one the trial tests. So the trial goes to preparation like any candidate, is scored for the claim's indication, and is approved by rule only in the high band. A draft whose own trial is not approved stays pending and is listed.

This reuses preparation whole, which also finds the other trials of the same treatment and condition outside the set, so a registry-drafted claim lists its trials as fully as a reported one.

*Instead of* making events straight from the stored record: the stored record is the bulk load's reduced one, and the claim path keeps the full payload and fetch time each event needs.

### 3. Grouping starts from registered arms and full indications

The 50-group dry run used existing news search names and indication keywords. The audit found 15 correct groups and documented the lost regimen components, flattened formulations and truncated indications. Five groups had an existing claim confirmed for all or part of their scope.

The read-only planner takes arm membership from the current registry projection and preserves formulation, complete combination components, full condition labels and the study purpose. A shared component cannot establish a regimen match. A record listing multiple conditions needs evidence that each proposed regimen actually addresses the corresponding indication. For older records with missing arm details and crossover or sequential designs with several assigned interventions, the plan records what needs review. Trials with missing short names can use a verified intervention description from the registry.

An existing claim is a candidate when its complete identity or a documented alias matches. Verify the regimen, clinical use and indication before reusing it. The plan also surfaces current published links, including links whose scope still needs review.

Use a treatment or prevention title to refine a named indication when it gives an explicit subtype or treatment target. Keep the stated patient context when another registered condition qualifies that target. A more detailed title naming several targets overrides abbreviated wording. When distinct tested arms name distinct cohorts for the same regimen, the planner can propose a pair for each cohort. Explicit measurements can be removed from a treatment regimen while diagnostic trials retain their diagnostic intervention.

For cases that need review, `thenwhat backfill registry-claim-plan --reviewed-scopes <file>` accepts a versioned JSON record of explicit regimen and indication pairs. Each pair carries verbatim registry evidence for both parts. Each review records the reviewer and the SHA-256 of the stored record. A changed record requires a fresh review. Applying a receipt changes the plan only. Match scoring, preparation, and publication audit still apply.

### 4. An ordinary-word name drafts nothing, and the fault is fixed first

A third of stored names would each draft a claim for "first" or "home". The rule that works out a search name is corrected before any drafting (the same defect `headline-funnel` task 2.12 records), and the drafting step refuses such a name itself and lists it, so a real treatment with a common name ("aspirin", "insulin") is seen and can be entered by the operator.

### 5. A vertical by rule, or no draft

A claim must have one vertical and a model chooses it today from an article. A registry-drafted claim has no article. The vertical is the general vertical of the group its trials' condition terms point to, by the mapping `approach-and-vertical-by-rule` builds. When the terms point to no group or to two, no claim is drafted and the group is listed.

*Instead of* asking a model to place it: that would be a second, weaker way of setting the same field, which that change already declined for the approach.

This makes this change depend on that one's mapping, and on the stored record carrying condition terms (task 2.2).

### 6. Words come from the site, and the export carries none

A claim's headline and summary are columns that may not be empty today. For a registry-drafted claim the export carries no headline or summary, only the codes, the intervention and the indication, and the site makes both from fixed phrases. The build's check for verdict wording gains the phrases for these claims and a list of words that offer a treatment to a reader.

In the store, the two columns become empty-allowed for a claim drafted from registry records, in a new migration; a claim drafted from an article still needs both.

### 7. A report that arrives changes nothing but what is shown

The same-claim decision already attaches an article to a claim that exists. A registry-drafted claim is one more claim for it to find, which is the point: the routes of `headline-funnel` tie a headline to a treatment and a condition, and now the claim is there to tie to. A published claim that gains its first article is not held again, as ADR 0007 already says for any published claim.

### 8. A sample the pipeline draws, a figure with no default

Reading every claim of a batch of thousands is not possible, and releasing without reading ends the hold. A sample keeps the hold honest only if the judge cannot choose it, so the pipeline draws it and records the seed. The figure has no default: until the operator sets it, batches are released only by judging every claim, as today.

A sample over the figure holds the whole batch. That is deliberate: a batch that is wrong at six in a hundred has a defect in a rule, and the fix is to the rule and a fresh sample, not to the six.

An ADR amends 0007. What 0007 says does not change otherwise: the audit is not a review gate, records no review decision, and decides only when a batch goes out.

### 9. Lists show every claim, and can be narrowed

The operator chose the same page and lists with a way to show only reported claims. Lists whose subject is a report (report rows, promises, reported statements) cannot hold a claim without one, so the home page's day-by-day list changes little. Lists of claims and topic pages will be dominated by claims with no report once a set is published: 7,341 pairs against 2,041 claims. That is the operator's choice; the counts say how many of each there are, and task 4.6 shows the operator a preview of the first set's effect on the home page and one topic before anything is published.

### 10. The build is measured before a set is published

Claim pages are built, not served on request. The first set could add several thousand pages, the status card images that go with them, and rows to the extension's lookup file. Task 4.7 builds the site from an export that holds the first set and records the time, the size of the output and the size of `lookup.json`. If the build does not fit, that is reported to the operator and to `cloudflare-source-of-truth` before any release.

### 11. Order of building

1. The decisions, the ADRs and the glossary.
2. The dry run, with nothing written.
3. Drafting and preparation for 200 claims, audited whole.
4. The site's wording, filter and counts, behind the export's new codes.
5. The sampled audit.
6. The first set.

Each step ends with figures shown to the operator.

## Risks / Trade-offs

- **Duplicates from conditions worded differently.** → The dry run judges fifty groups; the first 200 are audited whole; merges use the command that exists; the fault sheet gets each case.
- **A draft whose trial preparation does not approve.** → It stays pending and is listed with its score; the plan after the first 200 says what share that is.
- **Thin pages by the thousand.** A page with a status and a list of trials and no report is slight. → It states only registry facts, is marked, and can be left out of every list. Whether such pages are offered to search engines was asked and the operator chose the same page; it can be revisited without a change to the store.
- **A registered treatment read as an option.** → Fixed phrases only; the build fails on words of advice; "a trial is not presented as open to join" already holds for trial entries.
- **Preparation's cost at this size.** → The plan prints registry requests against the allowance and the decision step's cost before a set is drafted; sets are drafted in slices.
- **The vertical rule leaves many groups unplaced.** → Counted in the dry run. If the share is large, the operator decides whether to wait for a better mapping; no model is asked meanwhile.
- **An assistant's sample is the only check.** → The operator spot-checks a drawn share, and the differences are recorded with the batch.
- **Two changes touch what a trial with no report shows.** → `trial-first-route`'s plain page stays for every trial; its line "no news report is linked to this record yet" stays true; for a named trial the page also leads with its claim, which that change already specifies for a cited trial.

## Open Questions

The operator's. Each is a task in section 1.

1. The share of wrong claims a sample may hold, and the sample's size.
2. The monthly ceiling for model spend while sets are prepared.
3. Whether the home page's lists open on every claim or on reported claims when a reader has made no choice. The answer given was the same lists with a filter; the preview in task 4.6 is the time to confirm it.
4. Whether a real treatment with an ordinary name is entered by hand or waits.
