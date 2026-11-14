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

Estimated triage size, to be replaced by the plan's own figure: about 33 input tokens a lead in batches of twenty, so a million leads is about 3.30 US dollars at the Decisions API's listed price.

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

Before a fetch the reading step claims a request against `source_allowance_use` under the name `outlet:<domain>`, with a default interval for every outlet (`OUTLET_INTERVAL_SECONDS`, 10 unless set) and no count limit. The row lock spaces processes, as it does for sources. A crawl delay in robots.txt replaces the interval when longer. Leads are taken in reading order but a lead whose outlet is not yet free is skipped for the moment, so one busy outlet does not stall the run.

### 11. Where stored data saves cost, and where it does not

Saves a fetch and a model call:

- an address that is already a source article;
- an address shared many times or on two platforms, which is one lead;
- a lead for a claim that already has enough articles.

Saves requests later: paper records are already kept once per paper with a maximum age, and registry answers are already cached by request, so a second claim naming the same paper or the same search costs nothing new. This change adds nothing there.

Improves what is found, without saving anything: registry numbers and paper identifiers on the article's page become candidates with the strongest reason there is. Links from screening order the reading, so that the monthly budget goes first to leads for which a trial is known to exist.

Does not yet save anything: `resolve` still searches the registry once per new claim. Answering from `registry_trial` would save that request, but the registry's search expands synonyms and ranks, and a local match does not. The experiment that would settle it is to run both over claims with approved trial matches and count how many approved trials each finds. It is not in this change, and a local search is not added beside the registry's as a second path.

### 12. Migration

One migration, `0016`, adds the four tables. No existing table changes.

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
2. Apply migration `0016`. It only adds tables.
3. Load Hacker News, screen, and read the screening report. Add outlets from the unlisted list where warranted and screen again.
4. Triage. Sample 200, label, read the evaluation report. Reword and re-run triage if needed. Set the thresholds.
5. Load the chosen Reddit communities; screen and triage them; label a further sample so the report's platform split has Reddit figures.
6. Read 200 leads. Show the operator the funnel and the claims made. Only on their decision, read further, always with a limit.

Rollback: the new tables can be dropped without touching claims. Claims and source articles made by reading are ordinary ones and are removed by archiving.

## Open Questions

- How long leads that are unlisted or rejected are kept. They are small and hold no text.
- Whether Reddit files newer than the per-community release (after 2023-12) are worth the size of the monthly dumps. Depends on the first run's yield.
- Whether the site should one day show that an article was widely shared. Not without a change of its own.
