# Design

## Context

See `proposal.md` for the motivation and the counts.

What exists today, as read in the code on 2026-11-14:

- The work ledger, steps, source allowances, `registry_trial` and `article_lead` from `backfill-work-ledger` are merged (migration `0014`; the latest migration is `0015`). That change is complete and not archived, so its four capabilities are not yet in `openspec/specs/`.
- A step is processed one record per transaction (`backfill/runner.py`). Every step names a source and a number of requests per record, and a step whose source has no allowance refuses to run. There is no step that asks nothing, calls a model, or takes several records at once.
- `article_lead` is unique on registry trial and address and cannot exist without a trial.
- `source_article` is unique on claim and address. The pipeline has no address comparison of its own; the site has one (`site/src/lib/article-key.mjs`, `source-url.mjs`) and the extension copies it.
- Extraction (`extract/service.py`) is one model call on the article's text, which is hashed and dropped. `draft_claim_from_article` takes the slug and vertical as arguments and checks them before the model is called. `extract_into_claim` refuses a claim that is no longer pending.
- `ArticleRetriever` (`extract/retrieve.py`) reads robots.txt once per site and falls back to the Wayback availability API. It has no spacing between requests to one outlet.
- A fetched page already yields, by rule, the registry numbers, DOIs and PubMed ids it gives (`extract/page.py`). Only the live lookup uses them; drafting a claim does not.
- `thenwhat resolve` asks ClinicalTrials.gov for each claim and never reads `registry_trial`.
- Decisions go through `decide_many`, at most twenty items a call, each with its own `decision_log` entry. `decision_log.human_label` belongs to one logged answer. Model cost is recorded in `llm_usage` and refused at `LLM_MONTHLY_BUDGET_USD`.
- A claim's vertical is set by a person or the seed. `suggest_groups` suggests a group from approved trials' MeSH terms and changes nothing.

Constraints: article text is never stored, including in logs and fixtures; nothing public is served from the operator's machine; tests use the real test database and fixtures with no live calls; a source's terms are read into `docs/sources.md` before its reader is written; one way of doing each thing, with an explicit empty state where it cannot be done.

## Goals / Non-Goals

**Goals:**

- No model call and no outlet request for a lead that rules or stored data can settle.
- Triage quality is a measured figure the operator has seen before any article is read.
- Every stage is a ledger step: stoppable, resumable, re-runnable alone by raising its version.
- A claim made from a lead is indistinguishable from one made with `thenwhat extract new`.

**Non-Goals:**

- No new orchestrator, queue or service.
- No change to `resolve`, `prepare`, status rules, the export's shape or the site.
- No reading of any platform's live interface in bulk. Files only.
- No per-platform tuning of triage in this change. The report splits by platform so the need for it can be seen.

## Decisions

### 1. A link lead is its own record, not an article lead

Two tables: `link_lead` (one per address key: address, key, outlet domain, outlet kind, title, first shared time, and the results of the steps below) and `link_share` (lead, platform, community, time, score, and for Hacker News the item number), unique on lead, platform, community and time. Links to stored records go in `link_lead_link` (lead, record kind, record id, reason), in the ledger's way of naming a record. Labels go in `link_lead_label`, unique on lead and labeller kind.

*Why not widen `article_lead`?* An article lead means "a search found this for a trial"; its key includes the trial, and its capability is not yet in the main specs. A link lead means "people shared this". The two meet in screening, by address.

### 2. One address key, proven equal to the site's

A Python function gives an address its key. Its test reads the same cases file as the site's test for `article-key.mjs`, moved to a shared fixture, so the two cannot drift. `source_article` addresses are compared through the same key in screening.

*Alternative:* call the site's JavaScript from the pipeline. Rejected: a Node dependency in the pipeline image for one function.

### 3. Files, one reader per platform

`load-links <platform> <file>` streams a file and upserts. A reader turns one line into (address, community, time, score, title, item number or none) or a skip reason. Idempotence comes from the unique keys, so a stopped load is simply run again.

- **Hacker News:** the monthly parquet archive (`docs/sources.md`, "Hacker News monthly parquet archive"), chosen on 2026-11-14 in the first task group. It is complete, public and under ODC-By, and only a complete file can show which unlisted domains are worth listing. The reader asks each file for eight columns (`id`, `type`, `url`, `title`, `time`, `score`, `dead`, `deleted`), so the author's username and the item's text are never read from disk. This adds one dependency, a parquet reader. The operator downloads the monthly files wanted; all of them are about 25.8 GB. BigQuery was not read, and the search interface was set aside because it can only be asked about domains already listed.
- **Reddit:** the per-community submission files (zstandard-compressed, one JSON object a line). Only `url`, `subreddit`, `created_utc`, `score`, `title` and the fields that mark a self post or a removal are read from a line; the rest is never parsed into a variable that outlives the line. The field names are checked against a real file in the first task group.

Communities are named in `LINK_LEAD_SUBREDDITS`; there is no default.

### 4. The Reddit title is kept with the lead

The limits written in `docs/sources.md` on 2026-11-14 said a submission's title would be shown to triage and dropped. That cannot hold: the operator labels a sample from the title, and a new triage version must score the same title again. The title is therefore kept on the lead, as the Hacker News title is, private and never exported. The author, the post's id and address, its text and its comments are still never kept. `docs/sources.md` is corrected in the first task group, and the operator is told.

### 5. Three steps, and what the ledger gains for them

| Step | Record | Source | Per call |
| --- | --- | --- | --- |
| `link_screen` | link lead | none | 1 |
| `link_triage` | link lead in scope | model | 20 |
| `link_read` | link lead passed | outlet and model | 1 |

The step shape gains three optional declarations: no source; model spend, with estimated tokens per record; and a batch size. The runner locks a batch with the same `FOR UPDATE SKIP LOCKED`, runs it in one transaction, and on failure rolls back and processes that batch's records one at a time. That matches the decision interface's own rule that a batch with one unanswered item fails whole.

A raised failure undoes what the step wrote. A model step must not lose a decision it logged or a cost it recorded, so a step may instead return a failure for a record, which keeps what it wrote. Triage does this: when a call leaves a headline unanswered, the answers it gave are kept from the decision log, and only the unanswered leads are asked again, each alone. Nothing is asked twice and every call stays paid for in the ledger.

*Alternative:* triage one lead per call inside the existing runner. Rejected: the instructions and options are about 150 tokens against about 25 for a title, so one lead per call costs several times more and takes twenty times as many calls.

Triage size, measured on the first live run (2026-11-14): 60,362 input tokens for 200 leads, about 300 a lead, so a million leads is about 30 US dollars at the Decisions API's listed price. The estimate written before the run, 33 tokens a lead, was nine times too low: it counted the instructions and options once per call, but the Decisions API is sent the question and each option's description with every headline. The alternative above is still right in direction, and the plan's figure now uses the measured number.

### 6. Screening is three queries and a dictionary

The outlet rule is `kind_of` on the domain. The already-tracked check is a join on the address key. Name links use an in-memory index built once per run from claims' intervention names and other names and from registry trials' search names; a title is tokenised into words and matched as whole-word sequences. A trial links only when a word of its search indication is in the title too, which keeps "aspirin" from linking to every aspirin trial.

Screening results depend on stored data that changes (new claims, new article leads, a longer outlet list). The step's fingerprint covers the lead's own fields only, so those changes are picked up by raising the step's version, which is cheap because the step costs nothing. The one check that must never be stale, already tracked, runs again inside the reading step.

### 7. Passed, held and rejected are computed, not stored

Triage stores a score. The two thresholds (`LEAD_PASS_ABOVE`, `LEAD_REJECT_BELOW`) are applied in the reading step's scope and in the reports. Changing a threshold therefore costs nothing and re-scores nothing. Neither has a default: until the operator sets them from the evaluation report, nothing is passed.

### 8. Labels belong to the lead

A label is the answer to "does this headline report a specific treatment for a specific condition", which does not depend on the triage version. Stored on the lead, 200 labels stay useful for every later wording of the question. `decision_log.human_label` is left alone: it is tied to one logged answer and would have to be copied forward on every re-score.

The sample is stratified so that rare high and low scores are labelled as well as the crowded middle. The report weights each tenth by its population, or precision and recall would describe the sample and not the leads.

### 9. Reading is the existing extraction, reordered

`draft_claim_from_article` is split so that the model call comes first and returns the draft; then one of two existing paths is taken. If a claim covers the draft's intervention and indication (`slug_of_claim_covering`), the article is added to it with its hash, archive address and reported statements, and nothing else. Otherwise the slug is made by rule, the vertical is decided, and the claim is added and decided as today. `thenwhat extract new` keeps its arguments and behavior by calling the same pieces with a slug and vertical given.

The vertical has one way: a decision among the configured verticals, shown the draft's intervention, indication and summary, accepted at `VERTICAL_ACCEPT_ABOVE` (0.8 unless set). Below it no claim is made and the lead is listed as needing a vertical. No vertical is guessed and no general vertical is used as a default.

*Alternative:* derive the vertical from a linked trial's MeSH terms where there is one, and decide otherwise. Rejected as two ways of doing one thing.

### 10. Outlet spacing reuses the allowance table

Before a fetch the reading step claims a request against `source_allowance_use` under the name `outlet:<domain>`, with a default interval for every outlet (`OUTLET_INTERVAL_SECONDS`, 10 unless set) and no count limit. The row lock spaces processes, as it does for sources. A crawl delay in robots.txt replaces the interval when longer. Whether a lead whose outlet is not yet free is skipped for the moment or simply waited for is left to task 7.4: the requirement is only the interval.

### 11. Where stored data saves cost, and where it does not

Saves a fetch and a model call:

- an address that is already a source article;
- an address shared many times or on two platforms, which is one lead;
- a lead for a claim that already has enough articles.

Saves requests later: paper records are already kept once per paper with a maximum age, and registry answers are already cached by request, so a second claim naming the same paper or the same search costs nothing new. This change adds nothing there.

Improves what is found, without saving anything: registry numbers and paper identifiers on the article's page become candidates with the strongest reason there is. Links from screening order the reading, so that the monthly budget goes first to leads for which a trial is known to exist.

Does not yet save anything: `resolve` still searches the registry once per new claim. Answering from `registry_trial` would save that request, but the registry's search expands synonyms and ranks, and a local match does not. The experiment that would settle it is to run both over claims with approved trial matches and count how many approved trials each finds. It is not in this change, and a local search is not added beside the registry's as a second path.

### 12. Migration

One migration adds the four tables. No existing table changes. It was written as `0016` and renumbered `0018` when main, which had gained its own `0016` and `0017`, was merged into the branch.

## Risks / Trade-offs

- [Publishing by rule at volume publishes more wrong items] → The gate before reading, a first reading run limited to 200 with the funnel shown to the operator, and archiving as the remedy. The reading step never runs without an explicit limit until the operator has seen that run's figures.
- [A title is a weak signal: clickbait, puns, headlines that name no treatment] → The held band exists for that. Recall is reported, so the operator sees what a threshold loses.
- [Scores are not calibrated and may differ by platform] → The report is split by platform and its figures come from labels, not from the scores' face value.
- [Reddit's dumps may disappear or be withdrawn] → Files are downloaded once by the operator and read locally. Nothing in the pipeline depends on a further download. What is kept is the article's address, which the outlet published.
- [Old links are dead] → The existing snapshot lookup. The funnel reports how many could not be read and why, so the loss is visible.
- [Outlets refuse or serve thin pages] → `docs/outlets.md` already records which do. The funnel counts refusals by outlet.
- [A common word matches as a name] → Whole words only, and trials need an indication word. A link approves nothing; its worst effect is the order of reading or one lead held that should have been read.
- [The vertical decision is wrong] → It changes only where a claim is filed. The operator can change a vertical, and a low probability creates nothing.
- [Adding an article to a published claim publishes its reported statements] → They pass the existing statement check and rule, as for any article of that claim.
- [The monthly ceiling is shared with the live pipeline] → The plan shows what triage and reading need against what is left, before a run. The reading step takes a record limit.

## Migration Plan

1. Archive `backfill-work-ledger`, so that `work-ledger` exists in the main specs before this change adds to it.
2. Apply migration `0018`. It only adds tables.
3. Load Hacker News, screen, and read the screening report. Add outlets from the unlisted list where warranted and screen again.
4. Triage. Sample 200, label, read the evaluation report. Reword and re-run triage if needed. Set the thresholds.
5. Load the chosen Reddit communities; screen and triage them; label a further sample so the report's platform split has Reddit figures.
6. Read 200 leads. Show the operator the funnel and the claims made. Only on their decision, read further, always with a limit.

Rollback: the new tables can be dropped without touching claims. Claims and source articles made by reading are ordinary ones and are removed by archiving.

## Found while applying (2026-11-14): two decisions reading waits on

Groups 1 to 6 are built. Before the reading step is written, two things the specs do not settle have to be decided by the operator, because each changes what the public site shows.

1. **The article's date when its page gives none.** A source article needs a publication date, and it sets a claim's first reported date. `extract/page.py` reads the date from the page, and `docs/outlets.md` shows it finds none on some of the most shared outlets (sciencedaily.com and eurekalert.org: none of 13 pages). The date a link was first shared is on or after publication, usually the same day, but it is not the publication date. The project's rule is one way at full quality and an explicit empty state otherwise, so the proposal is: a lead whose page gives no date is not read, its outcome says so, and the funnel counts these by outlet so the page reader can be taught their markup. The alternative, using the first shared date, would publish a date nobody published.
   **Measured on 2026-11-14.** For articles whose address holds their date, the date of the first Hacker News share was compared with it. Sample: stories found through the Hacker News search interface, 143 requests, one article counted once at its earliest share, share time in UTC.

   | Sample | Articles | Same day | Within a day | Within 7 days | Same month | Same year | Over 30 days late | Over a year late |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | Six news outlets, a health word in the address | 4,620 | 48% | 80% | 93% | 93% | 97.5% | 3.3% | 1.5% |
   | sciencedaily.com | 4,070 | 11% | 43% | 83% | 81% | 93.5% | 8.9% | 4.2% |
   | eurekalert.org, old addresses | 932 | 11% | 35% | 84% | 88% | 96% | 4.6% | 1.4% |

   The six outlets are theguardian.com, nytimes.com, statnews.com, washingtonpost.com, cnn.com and npr.org. A share is almost never earlier than the address's date (20 of 4,620 by two days or more; the rest of the early ones are one day, the time zone). So the first shared date is a sound upper bound and right to the year in 93 to 97 cases in 100. It is the wrong day in half the news articles and nine in ten press releases, and its misses are large: the late shares over 30 days have a median of about 300 days and reach 17 years. Those are old reports shared again, which are the reports this tracker most needs dated correctly.

   The same sample shows a better source for the outlets that gave the question: the address. 4,070 of 4,073 sciencedaily.com addresses hold the release date (99.9%), as do 4,620 of 4,701 of the six news outlets' (98%) and 932 of 1,034 old eurekalert.org addresses (90%). Newer eurekalert.org addresses hold a number only and were not sampled. Proposal, replacing the one above: the date is read from the page, or by rule from the address for outlets whose addresses hold it; a lead with neither is not read and is counted by outlet. The first shared date stays on the lead and is never shown as a publication date. Limits of the sample: Hacker News only, and for the news outlets only addresses that hold a health word.

   **Decided on 2026-11-14, then corrected the same day.** The operator accepted "the page or the address, else not read". Before the rule was written, the address was checked against live pages: on four sciencedaily.com releases the number in the address matched the date the page shows on two, and was one and three days before it on the others. So an address holds a date, but not reliably the publication date, and the lag figures for sciencedaily.com above are off by up to a few days for the same reason; the month and year figures stand. The same check showed that the sciencedaily.com page does show its date, in an element (`id="date_posted"`) the page reader did not read. The rule as built is therefore narrower than what was accepted: **the date comes from the page only**; the page reader now reads that element; a lead whose page gives no readable date is not read; the address is never a source of a date. eurekalert.org's markup could not be checked (its robots.txt forbade the old addresses to the checking client), so its leads will show in the funnel's list of outlets with no date until its markup is read. This is `specs/lead-reading/spec.md`, "The article's date".

2. **The outlet's name on a source article.** Entered articles carry a name a person typed ("The Guardian"). A lead knows only the domain. The choices are to show the domain as the outlet, or to add a display name to each listed outlet in `backfill/outlet_kinds.py` and refuse a lead whose outlet has none.

   **Decided on 2026-11-14: a list of display names.** `OUTLET_NAMES` in `backfill/outlet_kinds.py` names all 111 listed outlets, in the form entered articles already use; the operator reviews the names. A lead whose outlet has no name there is not fetched or read. The same reasoning settles the title: a source article's title is its page's own headline, never the title a link was shared under, which for Reddit is a person's words and stays private. They are `specs/lead-reading/spec.md`, "The outlet's name" and "The article's title".

## Decided by the operator on 2026-11-14: an assistant's labels count, and the operator spot-checks them

The gate before reading first required 200 labels given by the operator. Asked whether an assistant's 200 labels may open it with the operator spot-checking, the operator answered yes. What follows from that:

- A label is still stored as what it is, a person's or an assistant's. Nothing an assistant labels is ever recorded as a person's.
- The label that counts for a lead is the person's when there is one and otherwise the assistant's. The figures, the sample (which no longer draws a lead anyone has labelled) and the gate all use the label that counts.
- `spot-check-leads` lists, without scores, the leads only an assistant has labelled where its label and the score disagree most, and a random 30 of the rest. The random draw is there because where the assistant and triage agree, both can be wrong, and a list of disagreements cannot show that. The operator labels what they check; their label then counts, and the report says how many they checked and on how many they agreed with the assistant.
- The spot-check is the operator's to do and is not enforced by a count: the gate opens on 200 labels that count. That is the trade the operator chose: triage quality is then measured largely by one model judging another, and the report says how many labels are an assistant's so the figures can be read for what they are.
- `label-leads` records a file of labels at once, all or none, because 200 commands is no way to label.

## Found on the first reads (2026-11-15): one story became several claims

The first 52 reads in the real database made 39 claims and joined none. Four were esketamine for depression in four wordings and three more were ketamine, each from another outlet's article about one piece of news. The run was stopped and its 39 claims removed before any export; the leads are unread again.

**Why.** `slug_of_claim_covering` joins an article to a claim only when intervention and indication are equal as written. That holds when an operator feeds a claim its articles. It does not hold when several outlets report one story, which is exactly what a much-shared story is.

**The same-claim check.** After the model read, and only when no claim is equal as written, candidates are gathered by rule and one decision judges them:

- *Candidates:* claims whose intervention name or synonym equals one of the read's names, or where one sits whole inside the other, word for word ("esketamine" inside "esketamine nasal spray"; "ketamine" is not inside "esketamine"). Then the claims screening already linked to the lead by its title. At most eight, equal names first, then the oldest. The net is wide on purpose: finding candidates is cheap and deciding is the decision's job.
- *The decision:* shown the read's treatment and condition and each candidate's, never article text. It answers one of the candidates or none. The rule it is given: the same treatment, and the article's condition is the claim's condition, a narrower form of it, or a wider wording of it. A different condition is a different claim (ketamine for suicidal thinking is not ketamine for depression).
- *The rule:* the article joins the chosen claim at or above `SAME_CLAIM_ACCEPT_ABOVE` (0.8 unless set). Below it, or on "none", a new claim is drafted. The decision is logged either way, and the lead's detail records what was read and the probability.

*Not taken:* dropping formulation and dose words from names before comparing. That is a word list to maintain, and containment already catches the case. *Not available:* reaching candidates through subject terms or development codes. A claim that was drafted minutes ago has neither.

**Which wording a claim keeps.** The first article read fixes the claim's indication and headline, and reads are ordered by trial links and then by shares. So the page carries the most shared article's wording, not the best one. A join never rewrites it (task 7.6 holds that). The operator can reword a claim; nothing here does.

**Taking turns.** With four reads at once, two articles on one story could both look, find nothing and both draft. Each read therefore takes a database advisory lock after its model read and holds it until its transaction ends, so the question "which claim is this" is settled by one read at a time. Fetching the page and the model read, which are the slow parts, still run side by side.

**No claim published unsearched.** A claim the read drafts was approved by rule on the spot, with the status every new claim starts with, and the export takes every approved claim. Esketamine would have gone out as "preclinical only". Now a named claim stays pending after the read. `thenwhat prepare --pending` already searches and reads the registries for every pending claim; when every step for a read's claim has succeeded, it decides the claim by the rule for drafts. A description in place of a name is still rejected at the read, since no search would change that.

*Alternative, raised in review:* gate the export on a recorded fact (a registry search having run) for every rule-approved claim, however it was made. Sounder as an invariant, but it changes what happens to claims the operator enters by hand and needs a record of searches that does not exist yet. Proposed as its own change, not folded in here.

## Measured on the reread (2026-11-15): the join rule tests "none of these"

With the same-claim check merged, 200 leads were read again: 141 new claims, 14 articles joined to a claim, 55 could not be read, 3 needed a vertical. The decision was asked 34 times. Esketamine still made four claims and ketamine three that should be two. The 34 decisions say why, and what the rule should be.

| What the article was | Decisions | Probability given to "none of these" |
| --- | --- | --- |
| Another condition or another treatment (aspirin for three conditions, CRISPR, gene therapies) | 15 | 0.98 to 1.00 |
| Arguable: a narrower population or a named form of one treatment (psilocybin for treatment-resistant depression beside major depressive disorder; CAR-T for leukaemias beside lymphoma) | 4 | 0.55 to 0.75 |
| The same story (joined, or should have been) | 15 | 0.00 to 0.40 |

- **The first rule asked the wrong number.** It required the chosen claim's own probability to reach 0.8. The same story in doubtful wording got 0.60 to 0.71, and where two drafts of one story were both candidates the vote split 0.51 and 0.43 with "none" at 0.06. All five of those became new claims.
- **The rule now.** Join the likeliest candidate when one minus the probability of "none of these" is at or above `SAME_CLAIM_ACCEPT_ABOVE`, 0.6 unless set, and that candidate has more than half. The second test keeps two claims for two conditions of one drug from being settled by a near tie. On the 34 decisions this joins the nine that joined and the five that should have, and leaves the arguable four and the different fifteen as new claims.
- **A rejected draft is not a candidate.** Two of the four esketamine drafts were rejected by the name rule ("esketamine nasal spray") and then stood as candidates, taking votes from the claim that stands. A rejected claim is never shown, so nothing should join it by decision. An article equal to it as written still lands on it, as before.
- **What this does not settle.** 34 decisions is a small sample and the gap between 0.40 and 0.55 is narrow. The arguable group is a question of how finely the tracker divides one drug's indications, which is the operator's, not a threshold's. Each decision is logged with every probability, so the rule can be measured again on the next batch.

## Decided by the operator on 2026-11-15: a check at the read for what the tracker follows

Of the 141 claims the reread drafted, the reviewing session found about twenty that are not reports of a new treatment: an established drug in the news for its price or safety, advice and public health, an approach with no one condition. Triage passes them as it was measured to. It is shown a headline and asked whether it reports a treatment for a condition, which a price rise for a tuberculosis drug does.

The operator chose a check at the read over tightening triage or archiving by hand, and chose to keep the name rule as it is for now.

- **The decision.** After the model read and before any claim is joined or drafted, `new_treatment_report` is shown the read's own headline, summary, treatment and condition and asked whether this is a report about one treatment that is new, experimental or newly being tested for one condition. Below `NEW_TREATMENT_ACCEPT_ABOVE` (0.5 unless set) no claim is made and nothing is joined; the lead's outcome is `not_a_new_treatment` with what was read and the probability.
- **Why at the read, not in triage.** The read has the article's substance; triage has eight words of headline. And it costs one decision on a few lines of our own text for a lead that has already been paid for.
- **Measured before it was switched on.** The decision was asked about all 141 drafts from their stored headlines and summaries. 33 scored 0.10 or less, 89 scored 0.90 or more, and 19 fell between. At 0.5, 41 would not have been drafted: 28 of the 103 pending and 13 of the 38 the name rule rejected. Read against their summaries the low group is price stories (Luxturna, cycloserine), safety alerts (faecal transplants, a face transplant's complication), established treatments (proton pump inhibitors, OxyContin, the MMR vaccine), advice and public health (water fluoridation, the Heimlich manoeuvre) and features about one patient. Arguable ones sit low too: an observational study of aspirin and prostate cancer at 0.02, an unpublished insurance-claims analysis of Enbrel at 0.29.
- **What it does not do.** It does not judge whether a treatment works, and it is not a status. It does not fix indications that hold two conditions or a doubtful vertical.

## Changed by the operator on 2026-11-15, the same day: an established treatment is wanted too

The check at the read ran on its first real batch and refused 25 of the first 106 leads read. The operator asked for the refusals to be explained and then said that an article about an existing treatment is still wanted: its past trials and other records are what came of it, and are worth showing.

**What the first question refused.** It asked for a treatment that is "new, experimental or newly being tested", and the model read "a drug that already exists" as "not new", whatever the article reported:

| Refused | Leads | Fair |
| --- | --- | --- |
| Hydroxychloroquine or chloroquine for COVID-19: a trial halted, a study questioned, an authorisation | 8 | No |
| A study or trial result on a treatment in use: aspirin and a first heart attack, antiretrovirals and HIV transmission, the HPV vaccine and cervical disease | 6 | No |
| Ketamine for depression, where other ketamine articles in the same batch became claims | 3 | No |
| Safety and sceptical pieces, single-patient and lifestyle features | 5 | Arguable, and wanted under the operator's note |
| No one treatment for one condition, or a read that named the wrong treatment | 3 | Yes |

The measurement before it was switched on (the section above) saw the same pattern in the low group and called it acceptable. That was the wrong call: it weighed the price stories and missed that trial results on existing drugs sat in the same group.

**The decision now.** `treatment_kind` answers one of three: a new treatment for a condition, an established treatment for a condition, or neither. The first two both go on to join a claim or draft one. Only "neither" refuses: no one treatment (a class or an approach for many conditions, a research direction), not a treatment (a predictor, a risk factor, a test), or advice with no condition treated. The rule tests the probability of "neither": at or above `TREATMENT_ACCEPT_ABOVE` (0.5 unless set) for "one treatment, new or established", the read goes on. The lead's outcome for a refusal is `not_one_treatment` (migration `0020` renames `not_a_new_treatment`).

- **Before a join as well as before a draft.** An article that is not about one treatment for one condition is not attached to a claim either. A price rise or a recall of a tracked treatment is now attached, as an established treatment in the news.
- **New or established is recorded, not yet shown.** The record is the decision log's entry for step `treatment_kind` under the lead's reference; the lead's detail also says "an established treatment in the news", for a person reading the lead. The step has its own name because `treatment_report` is one of triage's answers. Showing that on the site, with the treatment's earlier trials and approval beside the article, is a change to the export and the site and is not in this change.
- **The default is not measured yet.** 0.5 on the first question was measured on 141 drafts; this question is a different one. It is measured on the reread of the refused leads, and the figures are recorded in tasks.md before any of them is prepared.
- **A risk for the audit.** For a treatment in use for decades the registries may hold no record of its approval, so a status derived from registry events can understate where it stands. Each such claim is checked at audit before it is published.

## Targets set by the operator on 2026-11-15, and topics

The operator set what done looks like: 1,000 processed articles on the production site with their trials, papers and background cards connected, and topics people are following now, GLP-1 drugs first, covered in full.

**Where that stood when it was set.** 105 articles on 84 published claims. Of 117 approved claims, 60 had an approved trial, 105 a paper and 70 a background card. 862 link leads named a GLP-1 drug in their title: 293 on listed outlets, 239 on outlets not listed, 330 not screened yet. Four had a triage score, because screening and triage work oldest first and nearly all GLP-1 news is from 2023 on. Five claims.

**Topics.** A topic is a name and its words, in `backfill/topics.py`: a checked-in list applied by rule, like the outlet lists. It does two things to reading and nothing else.

- *Order.* A due lead whose title names a topic word, as a whole word in any letter case, is read before every other lead.
- *Scope.* Such a lead is read when triage held it, not only when triage passed it. Triage was measured on headlines in general at 0.7; between the thresholds about two in five labelled leads are treatment reports. For a topic that is to be covered in full that is worth a read each, and the check after the read says what each article turned out to be. A lead triage rejected is still never read.

`thenwhat backfill topics` reports coverage: where the leads that name a topic stand, and each claim whose intervention names it with its articles, approved trials, approved papers and approved cards. That is the measure for "covered", in the absence of a stricter definition from the operator.

**From review, before the first topic run.**

- *Brand and generic names.* Ozempic, Wegovy and Rybelsus are semaglutide; Mounjaro and Zepbound are tirzepatide. The same-claim candidates need a shared word, so an article on Wegovy would never have been offered the semaglutide claim. The topic's list groups each drug's names, and a claim under any name of a group is a candidate for a read that names another. The decision still judges it.
- *What held leads let in, and the operator's choice.* For a much-covered drug the held leads are mostly not study results: a maker's sales, shortages, lawsuits, insurance cover. Asked whether "covered in full" means every article about the drug or only reports about its evidence, safety and approval, the operator chose the second on 2026-11-15. So the decision after the read has a fourth answer, business news about one treatment for one condition, and for a lead that names a topic an article is joined or drafted only when it is about what the treatment does. The lead's outcome is otherwise `business_news` (migration `0021`). Two points from review changed this before it merged. A link is often shared under a title that names nothing, so a lead is on a topic when its title or the treatment its read names holds a topic word. And the operator was asked whether there should be one rule or two for leads on no topic, and chose: business news never starts a claim, for any lead, because a claim should rest on something reported of the treatment (the first batch's "OxyContin for pain" rested on a marketing story); for a lead on no topic it may still join a claim that exists, marked as business news.
- *Half the leads are out of reach.* 239 of the 862 GLP-1 leads are on outlets that are not listed and are never read. The coverage report says so beside the number.
- *The measured precision does not apply.* The 0.7 figure was measured on passed leads. Held topic leads are counted apart, in the topic's coverage.

*Triage, changed the same day.* Triage was first left in its order, oldest lead first, on the estimate that it was within an hour of finishing. It was not: three hours remained and 298 of the 309 GLP-1 leads on listed outlets had no score. Triage now scores leads that name a topic first. The cost is a pattern match over the due leads for each call of twenty, which is small beside the call. *Not done here.* Screening is not reordered: it was minutes from finishing. News outlets that carry GLP-1 stories and are on no list (Axios, Vox, Business Insider, Gizmodo, El País in English) are not added: an outlet's kind is set when a lead is loaded, so adding them means setting it again on stored leads and screening them again, which is its own task. Background cards are made by `thenwhat terms`, which `prepare` does not run; for now it is run after `prepare`.

## Decided by the operator on 2026-11-15: two bands, shown not reviewed

The first batch left a question: 42 of 109 rule-approved claims had a stage reading under the threshold for confirming by rule. Three options were put to the operator, each with a review by a person or by the auditing session somewhere in it. The operator chose none of them: "we never really want human review, only for cleanup after flagging by admin. surfacing confidence bands/scores should help the user make an informed decision." On the lower band: publish, marked low confidence; it cannot set the status.

So an evidence-stage reading has two bands (ADR 0004). The sure band is the rule that `corpus-match-accuracy` added the same day: probability and confidence at the review threshold confirm the stage. The lower band is new here: a reading that did not confirm, whose chosen stage has at least `STAGE_SHOW_ABOVE` (0.5), is exported as `evidence_stage_reading` with its score and the other stages it weighed, and the claim page shows it marked low confidence. The claim's stage stays empty, so the status reads "no trial record found" and nothing counts the reading.

Trial and paper matches needed nothing: the export already carries a pending match as a candidate with its score, and only approved matches reach the status rules.

Not done here, and asked of the operator: an article the read ends as not one treatment, business news or needing a vertical gets no search for trials or papers, because the unit of the product is a claim. "Always attempt finding closest candidates" may ask for that; it is a change of its own.

## Found on the GLP-1 run (2026-11-15): 266 reads became 67 claims

The topic run read 266 leads that name a GLP-1 drug: 47 joined a claim, 75 drafted one, 35 were business news, 48 not one treatment, 59 unreadable. The coverage report then listed 67 claims for the topic. Three causes, in order of size:

- *A class read as one treatment.* Some fourteen drafts were for "GLP-1 receptor agonists", "GLP-1 drugs", "GLP-1 medications" or "GLP-1 analogs". The treatment-kind decision is told a class is not one treatment and still let them through, and the name rule let them through because "GLP-1" holds a digit and so counts as a code.
- *The condition worded as an aim or an outcome.* "Weight loss", "weight loss and weight management", "reducing the risk of heart attack, stroke and death": the same condition under five wordings is five claims, because the same-claim decision is asked about names first.
- *Two conditions in one.* "Type 2 diabetes and obesity" beside "obesity".

Two fixes, both before any decision is paid for. A checked-in rule says a name that ends in a class word, or in a plural kind of thing, is a class: run over the 212 treatments the reads had drafted it marks 19, every one a class (the GLP-1 drafts, "COVID-19 vaccines", "Weight-loss medications", "β2 agonist"), and three of them are claims the corpus work archived by hand the same day for the same reason. A lead it marks ends as not one treatment with no further call. And the read is now asked for the condition as a registry files it: the disease alone, one of them, never an aim or an outcome.

The rule is its own function, not part of the name rule, because the name rule also decides what the live lookup searches a registry for and that is not this change's to alter. The reworded field is shared with the lookup's read; that is one way of asking, on purpose, and the lookup's corpus should be run again after it.

What it costs: an article about the class as a whole ("GLP-1 drugs linked to lower dementia risk") makes no claim. That is the unit of the product; such articles are counted in the funnel as not one treatment and listed in the register.

## Open Questions

- How long leads that are unlisted or rejected are kept. They are small and hold no text.
- Whether Reddit files newer than the per-community release (after 2023-12) are worth the size of the monthly dumps. Depends on the first run's yield.
- Whether the site should one day show that an article was widely shared. Not without a change of its own.
