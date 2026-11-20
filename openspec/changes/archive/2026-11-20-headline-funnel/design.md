# Design

## Context

See `proposal.md` for why. This section records what was measured, so the decisions below can be checked against it. Everything here was measured on 2026-11-17. Queries on the production database were read-only. Samples were judged by an assistant from the headline and address alone; no page was opened, so whether an address exists was never checked. No real address or headline is recorded here.

### The gap

Counted on the production database against ClinicalTrials.gov's own totals, which matched for every state.

| | Registry, interventional | Cited by a claim |
| --- | --- | --- |
| Under way or not yet started | 91,003 | 1,590 |
| Completed or terminated in 2026 | 11,050 | 151 |
| Both | 102,053 | 1,741 (1.7%) |

Of the 100,312 uncited: 42,782 have a stored search name, which is 18,208 distinct names; 57,530 have none. 44,166 article leads are stored for 2,889 trials and no step reads an article lead.

### One day of a public article list

GDELT's article list for 10 November 2026: 197 files, 132 MB, fetched in 25 seconds. Rows carry a description and an author beside the address and title; both were dropped as the files were read and the files were deleted after counting.

| Stage | Headlines | Of English |
| --- | --- | --- |
| All | 482,387 | |
| English | 149,934 | 100% |
| One per address | 146,634 | 98% |
| Hold any stored name, code or acronym | 60,895 | 41% |
| Same, names made only of dictionary words dropped | 6,327 | 4.2% |
| Same, inflected dictionary words dropped too | 3,193 | 2.1% |
| Also hold a word of the trial's condition | 218 | 0.15% |

Of the 3,193: 3,034 are on outlets on no list, 69 on general news, 66 on trade press, 24 on press release wires. Eight terms kept about two thirds of them: "women" 841, "Diwali" 563, "Davidson" 183, "lifestyle" 126, "Johnson" 125, "metro" 102, "Novartis" 88, "NASCAR" 69.

Outlets present that day, against the pipeline's own lists: 47 of 76 general news, 9 of 47 trade press, 4 of 11 press release. Absent: STAT, Fierce, Endpoints, BioSpace, MedPage Today, Reuters, AP, GlobeNewswire, Business Wire.

### A decision step on those headlines

The 3,193 hits are 2,588 distinct headlines. A small model was given 40 at a time, the headline only, no search, and asked for the three labels the lead labels already use.

| Label | Distinct headlines | Judged |
| --- | --- | --- |
| Treatment report | 243 | 34 or 35 of 40 right |
| Other health | 570 | 0 of 25 were a missed report |
| Not health | 1,775 | 0 of 25 were a missed report |

Of the 243, only 85 also held a word of the trial's condition, and of the 195 distinct headlines that did hold one, 110 were not treatment reports. Twelve of the forty judged reports were one event told by twelve outlets. Fifty-two of the 243 were on trade press.

### A search by a model, one trial a task

A small model with a search tool that answers from an index, started once per trial with the registry record's fields and nothing else, on a subscription.

| | First run | Second run |
| --- | --- | --- |
| Trials | 30 | 200 |
| With a lead | 23 | 87 (63% of 60 with a known article, 35% of 140 uncited) |
| Leads | 63 | 198 |
| News, not a release | 21 | 93 |
| With no date | 45 | 134 |
| On an outlet on no list | not counted | 154 |
| Judged right treatment and condition | 60 of 63 | 42 of 50, 2 unsure |
| Known article recovered | 2 of 15 | 2 of 60 |

The second run's prompt asked for news first and one address a story. Six workers took 36.6 minutes for 198 tasks, about 325 an hour; four workers had reached 327 an hour, so more workers did not help. A task used about 56,000 input tokens for a few hundred of answer. The mode that searches live and the mode that answers from an index found the same amount, and neither opened a page. The agent's own mark that a lead was about the trial's own study was wrong on five of the six wrong leads.

### Routes read about and not built here

Read by research tasks on 2026-11-17; prices and limits are as the pages said that day.

| Route | What was found | Why not here |
| --- | --- | --- |
| A search interface over a search engine's results | About 1 US dollar per 1,000 queries, 50 a second | Paid; coverage of trade press not tested |
| A regulator's filings index, by registry number | Free; 34 filings for one trial, 29 of them releases filed as exhibits; about 12% of industry phase 2 and 3 trials in a sample of 58 | A hit has a date and a company and no headline, so triage has nothing to score |
| A mentions index | Key needed since November 2025; review up to 30 business days | Already "not now" in `trial-first-route`, question 11 |
| News interfaces | Daily caps, or thirty days of history | Do not cover the period |
| A second headline corpus, built from a public news crawl | 2025 whole, 2026 to April; press release wires in volume | Its files also hold article text; see Open questions |

## Goals / Non-Goals

**Goals:**

- Every headline in a loaded file that names a tracked treatment becomes a lead, at no charge per trial and with no request to a news outlet.
- The existing triage and read stay the only judges of a lead. Nothing new approves anything.
- One story costs one or two reads.
- The slow free search fills what the files leave empty, and can do no harm if an agent misbehaves.
- The 44,166 stored article leads stop being a dead end.

**Non-Goals:**

- Closing the gap. Most trials have no report; these routes find the reports that exist.
- Tying a headline to one trial. A headline names a treatment and sometimes a condition (`trial-first-route`, measurement 1). The tie stays a candidate for preparation to score.
- Raising throughput of the page reader. It stays the pace of everything after triage.
- Covering STAT, Fierce and Endpoints. Neither headline corpus holds them.

## Decisions

### 1. A kept headline is a link lead, not an article lead

The path from a link lead to a claim is built and measured: screening, triage, the read, the same-claim decision, preparation, the audit hold. No step reads an article lead. So a headline that is kept, an address an agent reports, and a stored article lead all become link leads with a reason, and nothing downstream is new.

*Instead of* a second reading step for article leads: two steps would have to keep the same rules for the page reader, dates, titles and the same-claim decision, and would drift.

This needs a link lead that no person shared. `trial-first-route` task 8.5 already plans one ("store a link the record gives on a listed outlet as a link lead"), and its wire requirement stores hits as link leads. A lead's reasons become a list: shared in a community, kept from a headline file on a term, returned by the news search for a trial, reported by a search for a trial.

### 2. The keep rule is separate from the link rule, and looser

`trial-report-links` makes a name telling only when it is a development code, and a link strong only with a word of the condition. Those rules decide what is read first, and were set after forty links were judged. They stay as they are.

Whether to store a headline is a different question with a different cost of error: a wrongly kept headline costs one triage call, and triage was right on about 86% of what it passed and missed none of 50 it turned away. A wrongly dropped headline is gone. So the keep rule takes any intervention name that is not ordinary words, and does not ask for a condition word, which would have dropped 158 of 243 reports.

*Instead of* widening what is telling: that would change reading order for every stored lead on evidence from one day.

### 3. Two rules cut the noise before the model: a word list and a share

The word list with inflected forms took hits from 41% of English headlines to 2.1%. What is left is dominated by a few names that are people, festivals and companies. A ceiling on the share of headlines a term may hold removes those without a list of them, and the load's report shows the operator which terms are near it. The ceiling has no default: a load with none set counts and keeps nothing.

On the measured day the eight terms above each kept 69 or more headlines of 150,000, and "Ozempic", a real treatment in the news, kept 39. A ceiling between the two would have separated them that day, but the margin is narrow, so the figure is the operator's to choose from the report. That is task 2.6.

*Instead of* asking the substance registry about each name first (`trial-first-route` tasks 3.2 to 3.4): that work makes names telling for links and should go on. It is not needed to decide what to store, and the headline load gives task 3.2 the large sample of titles it asks for.

### 4. No embedding before triage on this route

A day leaves about 2,600 distinct headlines after the rules, and about 1,000 with a share ceiling. Triage takes twenty a call. The stored 409,058 triage scores were made inside this month's recorded model cost of 24.24 US dollars, which also paid for reads, so January 2025 to November 2026, perhaps 0.7 to 1.8 million headlines, is estimated under 100 US dollars. A cheaper stage in front would save little and add a threshold to keep honest.

The headlines that name no tracked treatment, about 143,000 a day in English, are where a cheap stage is needed. That is `lead-prefilter` in `work-reuse-and-metrics`, and it is not built here.

### 5. Story groups use a measure of titles, and only order reads

Twelve of forty reports being one event means the read, the slowest stage, would spend much of its time on repeats. The existing rule "enough articles for one claim" stops reads only after a claim exists and only for leads already tied to it. Grouping before the read lets that rule act on leads no read has tied yet.

The measure is a model that turns a title into numbers, run on the writer's own machine, named in the settings, versioned. The threshold has no default and comes from judged pairs. A group never rejects: a lead left unread keeps its score and is due again when the setting or the version changes.

*Instead of* grouping by shared term and date alone: one treatment has several events in a month, and the measured twelve shared a drug class, not one name.

### 6. The search service takes addresses and nothing else

An agent's output is model output, and search results can carry instructions meant for a model. So the service has two actions, accepts only fields it names, refuses anything that could hold article text, and writes link leads and ledger entries only. The worst a misled agent can do is report bad addresses, which triage and the read reject and the failed-address register records.

It is one process on the writer's machine, on the loopback address. Holds live in that process's memory, with a time limit; a restart makes held trials due again, which costs a repeated search and nothing else. No migration is needed for holds.

*Instead of* giving agents the command line or the database: both would let a model write claims, which no rule allows.

### 7. One trial a task, the index-only search mode

Search fees or quotas are per search, not per task, so batching trials saves little and risks pinning an address to the wrong trial. The index-only mode found as much as the live mode and opens no page, which keeps the rule that a news page is fetched only by the page reader. The agent's mark that an address is about the trial's own study is stored and decides nothing: it was wrong on five of six wrong leads.

Whether several trials in one session lower the fixed cost of about 47,000 tokens a start, without lowering accuracy, is measured in task 4.6 before any long run.

### 8. Where files live

Headline files are staged outside the repository, in a folder a setting names. The full period is about 42 GB as published and far less once reduced to the five fields. The external drive may hold the staged files; the loader reads through the setting and tests nothing on the drive directly, and the database, the service and every runner stay on the internal disk, as the workspace rules require.

### 9. Order of building

Phase 1 is the carry of article leads and the headline route for one source, since they are free, deterministic and need no new service. Phase 2 is story groups, which need phase 1's leads to judge pairs from. Phase 3 is the search service. Each phase ends with a sample judged and shown to the operator, and a stop if fewer than half of what triage passed are reports.

## Risks / Trade-offs

- **One day measured.** Every headline figure is from one weekday. → Task 2.7 loads a week before any long span and compares.
- **Judged by an assistant, from titles.** → Phase samples are recorded as an assistant's and a share is spot-checked by the operator, as lead labels are.
- **Most kept headlines are on outlets on no list.** → They go on to triage under decision 10; counted by outlet kind in task 2.8 before any read, with the hosts that kept the most leads listed so a mirror or an aggregator is seen.
- **Trade press is thin in both corpora.** → Stated in the load's report by outlet kind; no claim of coverage is made.
- **A file's description field reaching disk.** → The fetch script drops it as rows arrive, and a test fails if a staged file holds any field but the five.
- **A subscription's terms on automated use.** → The operator decided on 2026-11-17 to use it at modest volume. The terms as read are noted in `docs/sources.md` with that decision before the service hands out a trial, and the route runs under a daily allowance.
- **A service-side limit near 325 tasks an hour.** → The route is planned as weeks of background work, with a daily allowance, not as a run.
- **Invented addresses.** Public tests put them at 3 to 13% of what such tools cite. → Nothing is checked at report time; the read fails them and they are counted by route.
- **The share ceiling drops a real treatment that is in the news.** → The report lists terms near the ceiling; a dropped term is a setting change and a reload, since loads can be run again.
- **Triage cost grows with the period loaded.** → The plan prints it against the route's share before a span is loaded.

## What the operator decided

On 2026-11-17, after this change was first drafted, the operator answered twelve multiple-choice questions. The answers that shape this change:

| Question | Answer |
| --- | --- |
| May a sponsor's, an investor page's or a university's own release be a source article? | Yes, marked as a release |
| May the second headline corpus be used? | Yes, with the five fields asked for by name and the text never read |
| May the subscription run the search route? | Yes, at modest volume, as the operator's own decision on its terms |
| What may finding articles cost? | The provider's free monthly credit; no cash |
| Which trials first? | Industry-sponsored, phase 2 and 3 |
| What closing the gap means | A claim for every named trial, drafted from the registry record where no report exists (`registry-drafted-claims`) |

The 2026-11-18 decision in `registry-drafted-claims` broadened the rollout to all active Phase 2 or 3 interventional trials and all Phase 2 or 3 trials actually completed in 2026. Registry evidence can establish a claim before a report exists. The headline funnel finds reports for these claims and the same-claim decision attaches each matching report. A trial is due for a news route while none of its citing claims has a linked report. A report that establishes a new treatment and condition can still start an article-drafted claim through the existing route.

Decisions 10 and 11 follow from the first answer.

### 10. A lead a trial route found goes on though its outlet is on no list

Screening stops a lead on an outlet that is on no list, and that is right for links people shared: most such domains are not news. A lead these routes found is different: it was kept because it names a tracked treatment, or was returned for a trial. Most are a sponsor's or an institution's own page (154 of 198 in the second search run). So a lead whose reasons include one of these routes goes on to triage with its outlet kind unknown, and triage and the read decide as for any lead. A lead that was only shared is stopped as before.

*Instead of* adding each sponsor's domain to the outlet list: thousands of sponsors, and a list of them would call them outlets.

### 11. A release is marked by rule, from the sponsor's own website

The site already says when a report is on the website of one of a claim's organisations. Today that mark is set when a read finds it. For these routes it is also set by rule: a source article whose domain is the website an organisation record gives for the lead sponsor of one of the claim's approved trials is marked as on that organisation's website. A release on a domain no organisation record gives is shown with its outlet's name as the page gives it and no mark, and its outlet kind is unknown; the mark is never guessed.

## Open Questions

The operator's. Each is a task in section 1.

1. The daily allowance for the search route.
2. The monthly ceiling for model spend, within the free credit.
3. Whether the filings index is wanted, which first needs a decision on how a lead with no headline is triaged.
