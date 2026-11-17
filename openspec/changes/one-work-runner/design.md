# Design

## Context

See `proposal.md` for the motivation and the figures.

What exists, as read on 17 November 2026:

- `backfill/ledger.py`, `runner.py`, `steps.py`: a step declares a scope, a version and its inputs; an entry per record holds done, nothing found or failed; `take_due` uses `FOR UPDATE SKIP LOCKED`; one record is one transaction. A step returns a `WorkOutcome`, a `Failed`, or a `Deferred` (no entry, skipped for the run), or raises a `SourceStop` (the run ends, no attempt).
- `backfill/link_read.py`: every refusal ends in `_finish(record, ReadOutcome, text)` and returns nothing found, which is final. The reason lives as prose in `link_lead.read_detail`.
- `cli/prepare.py`: a thread per claim, a process per step (`subprocess.run([sys.argv[0], ...])`), each step one transaction. A claim is decided when every step but `terms` exited 0. `cli/resolve.py` catches every exception of its sub-lookups in `_step` and still exits 0.
- `sources/base.py`: four attempts, backoff `max(2^n, Retry-After)` with no ceiling, a `Retry-After` given as a date ignored, backoff per process. `source_allowance_use.paused_until` is read by the backfill only.
- `llm/decisions.py`: plain `httpx`, no retry. `decide/core.py` marks a failed call `unreachable`; only `link_triage.py` acts on it.

Constraints: no article text is stored anywhere; approval is by deterministic rule; one way of doing each thing, with no looser path standing in when the first cannot run; migrations are added, not regenerated, and run on the writer only; no hosted service is added.

## Goals / Non-Goals

**Goals:**

- One place decides what a failure means, for leads and for claims.
- Every record that can still be completed comes back by itself or by one command, and none comes back that cannot.
- A run that meets a throttled or exhausted provider leaves everything it did not finish due, at no cost to those records.
- Fewer shapes: one outcome type, one runner, one call policy, one reason vocabulary.

**Non-Goals:**

- Any rule in `extract/names.py`, `claims/entry.py`, `status/`, any prompt, any threshold.
- Reuse of paid results under a shared key, or keeping a read's draft across a failure. The seams for both are left: see decision 9.
- A workflow engine, a queue library, or an asyncio rewrite.
- The reader's-lookup queue of `docs/adr/0009`.

## Decisions

### 1. A new package `thenwhat/work`, and the ledger moves into it

`work/outcome.py`, `work/reasons.py`, `work/ledger.py`, `work/runner.py`, `work/calls.py`, `work/pause.py`. The step protocol keeps its shape (`scope`, `inputs`, `version`, `run`), so existing steps change their return values and little else. `backfill/` keeps only what is about leads.

Alternative considered: a second pipeline package built beside the first and switched over at the end. Rejected: 44 changes are open against the present code, the rules are the larger part of it and are not in question, and two pipelines would each need every fix until the switch.

### 2. One outcome type with five values in three classes

```
Done | NothingFound(reason) | Later(reason, not_before) | NeedsFix(reason) | Failed(error)
```

`Later` and `NeedsFix` count no attempt. `Deferred` is removed: an outlet's pacing gap becomes `Later` with a short `not_before`, which also ends the present behaviour where a deferred lead is dropped for the rest of the run even after its gap has passed. A raised exception stays a `Failed` with its writes undone. `SourceStop` stays an exception, renamed `CannotAsk`, and is the only thing that ends a run early.

Alternative considered: keep three outcomes and add a `retryable` flag to nothing found. Rejected: the due rule would then read a flag and a time on an outcome whose name says the record is finished.

### 3. Reasons are declared by the step, stored as a code with values

Each step declares an enum of reasons and the class each belongs to. The entry stores `reason` (text code) and `reason_values` (JSON, for example `{"status": 403, "outlet": "nature.com"}`). The words a person reads are made from the code in one place, so the funnel report and `link_lead.read_detail` cannot drift from the code. A reason's class is fixed where it is declared, so a step cannot return `Later` with a reason declared as final.

`link_lead.read_outcome` stays: it is the domain's answer (added to a claim, new claim, cannot be read, ...) and other code reads it. `read_detail` becomes a rendering of the reason.

### 4. Schema

`work_entry` gains `reason text null`, `reason_values jsonb null`, `not_before timestamptz null`, `first_put_off_at timestamptz null`; its outcome check gains `later` and `needs_fix`. New table `registry_search` (claim, source, term, condition, ran_at, reported, kept, cut, not_sent_reason), replaced per claim and source by each finished search. One migration for the columns and table; one data migration that maps stored `read_detail` text to codes and fails if any lead is left without one.

The 2,195 leads with a stored detail fall into the reasons the funnel report already lists, so the mapping is a closed table. Leads recorded as unreadable for a status that is now "later" are migrated to `Later` with `not_before` at migration time, so the next run asks for them.

### 5. Requeue is the one way to bring records back

`thenwhat work requeue <step> --reason <code> [--where key=value] [--dry-run]` marks matching entries stale and zeroes their attempts. `thenwhat backfill retry-outlet <outlet>` stays as a name and calls it with the refusal reason and the outlet. A version bump stays for what it is for: the step's logic changed for every record.

### 6. Claim steps, and what the decision waits for

| Step | Record | Depends on | Asks |
| --- | --- | --- | --- |
| `claim_articles` | claim | none | page reader, model |
| `claim_substance` | claim | none | registry of substances |
| `claim_trials` | claim | `claim_substance` | trial registry, decisions |
| `claim_papers` | claim | `claim_trials` | literature indexes, decisions |
| `claim_fetch` | claim | `claim_trials` | trial registry |
| `claim_readings` | claim | `claim_fetch` | model |
| `claim_terms` | claim | none | subject indexes, decisions |
| `claim_named_records` | claim | none | trial registry, literature indexes |
| `claim_decide` | claim | `claim_substance`, `claim_trials`, `claim_fetch` | nothing |

`resolve` is split in three because its parts fail apart and are needed apart: the substance record is what the twin rule reads, the trial search is what a status rests on, papers are neither. Each part is all or nothing, so `_step`'s catch-everything goes. `claim_decide` is `decide_prepared_lead_claim` unchanged, run as a step that asks no source.

Inputs (what makes a claim due again): for substance, trials and terms, the intervention's names, the indication and `registry_search_due_at`; for fetch, the set of approved matches; for readings, the stored trial records' hashes; for named records, the registry numbers and identifiers kept with the claim's articles.

`thenwhat prepare` runs these through the runner in one process, several claims at a time by the runner's workers. The per-step commands (`thenwhat resolve <slug>` and the rest) stay for a named claim and call the same step.

Dependencies are a join on `work_entry` in the step's scope, written once in `work/ledger.py`. Alternative considered: one `claim_prepare` step with parts recorded inside its result. Rejected: a failed part would make the whole claim due and redo the parts that finished, which is the present fault.

### 7. One call policy

`work/calls.py` wraps every outbound call that is not to the page reader: source clients and both model backends. It retries transport errors, 408, 429 and 5xx, with `tenacity`, a bounded count, backoff with jitter, `Retry-After` read as seconds or as a date, and a ceiling on any single wait. A wait above the ceiling, exhausted retries on 429, a refused key or an exhausted quota raise `CannotAsk` with the time, and write it to `source_allowance_use.paused_until` through `work/pause.py`, which every caller checks before sending. Counting against the allowance moves into the same wrapper, so `prepare` is counted too.

The page reader keeps its own rules (`docs/adr/0006`): the pipeline acts on its answers and does not retry around it.

Alternative considered: keep the hand-written loop and add the missing cases. Rejected: three loops exist (`sources/base.py`, the reader's busy retries, none in `llm/decisions.py`) and the cases missing differ in each.

### 8. The lock covers the decision and the write, nothing else

In `LinkRead._read`, `_named_on_the_page` leaves the locked section and becomes `claim_named_records`. The page's registry numbers and identifiers are kept with the source article (they are identifiers, not article text) for that step to read. What stays inside the lock: finding candidates, the same-claim decision, the vertical choice, and the write. Those two decisions stay inside because their answer depends on what another read has just written.

### 9. Seams left for the two open changes

A step's `run` may return a staged result with its outcome; the runner saves it with the entry. `work-reuse-and-metrics` 4.3 and `idempotent-runs-and-one-address` 5.3 and 5.5 can then key and keep partial results without another change to the runner. Nothing is staged by this change.

### 10. Acceptance without replaying pages

No article text is kept, so a read cannot be replayed against stored data. Acceptance is therefore three checks:

- Characterisation tests written first against the present code at the agreed seams, then run unchanged against the new code: for each step, one record per outcome.
- The data migration maps every stored lead outcome to a code, and the funnel report before and after gives the same counts per line.
- On the writer, the claim steps are run for fifty approved claims whose answers are in `http_cache` and `decision_log`; their matches, events and status must equal what is stored. Any difference is reported before the old path is removed.

## Risks / Trade-offs

- [Leads once final come back and cost page requests and reads] → Only reasons declared as later or needs a fix can come back, a requeue has a dry run that counts them, and the spend ceiling and allowances apply as to any run. The first requeue is by one reason at a time.
- [A record put off for ever] → After thirty days of one reason it becomes needs a fix and is listed in the plan.
- [A claim that would have been decided now waits, because a substance lookup that failed silently now blocks] → That is the intended change; the plan shows how many wait and for which source, and the lookup is due on every run.
- [Splitting `resolve` changes what one command does] → `thenwhat resolve <slug>` runs the three steps in order and reports each.
- [The data migration meets a detail text it has no code for] → It fails and names the text; no lead is given a catch-all code.
- [Other open changes edit the files this one moves] → The move of `backfill/ledger.py`, `runner.py` and `steps.py` is its own commit with no behaviour change, landed first, so later rebases are mechanical.
- [`claim_decide` as a step could decide a claim twice] → Its scope is claims awaiting review, as `decide_prepared_lead_claim` already checks.

## Migration Plan

1. Land the move into `work/` with no behaviour change.
2. Land the outcome model, the columns and the call policy behind the existing steps; `Deferred` and the old outcomes still accepted.
3. Move `link_read`, then `link_triage`, `link_screen`, `news_search`; run the data migration on the writer; compare the funnel report.
4. Add the claim steps beside `cli/prepare.py`; run the fifty-claim comparison on the writer.
5. Point `thenwhat prepare` and the daily run at the claim steps; remove the process-per-step runner, `Deferred` and `_step`.

Rollback: steps 1 to 4 revert by commit, the new columns being unused by the old code. After step 5, reverting the code leaves the columns and the search table in place and harmless; the data migration of lead reasons is not reversed, and `read_detail` still holds readable words.

## Open Questions

- The wait before a site that answered 5xx is asked again when it stated none: six hours is a first value, to be set from what the first runs show.
- Whether `registry_search` should later be shown on a claim's page ("searched on"). Not needed for this change and would be a change to `site-publishing`.
