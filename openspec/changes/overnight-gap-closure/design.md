# Design

## Context

State at 22:34 UTC on 2026-11-16, measured:

- **Site:** 708 claims published. In the working database 743 are approved and released, of which 35 were cleared tonight and are not yet published.
- **Reddit backfill:** 30,471 leads scored ($0.94); about 1,150 of 1,590 readable leads read; 434 left; 115 more are held because their publisher has banned the page reader's machine. 205 claims await audit and 113 await preparing. First audit round: 204 claims, 99 cleared, 105 archived.
- **Trials:** 467,064 interventional trials stored with listing fields only (state, phase, start date, conditions, interventions, sponsor class). Activity and results fields are not stored.
- **Database:** at migration 0026. The main branch carries 0027 (a key version on link leads, additive; after it, loading and link steps on new code refuse until `rekey-links --apply`) and 0028 (match record facts, from another session; to be read before it is applied).
- **Checkouts:** reads run from a checkout at the commit before 0027; the daily job runs at 04:30 from a checkout at the commit before 0027; no run uses current main.
- **Spend:** $23.12 this month of $100, $9.82 today. Page reader: 6,000 requests a day, 4 in flight, 30 seconds between pages of one outlet. Registry: 5,000 requests a day; a full trial load is 468.
- **Open pull requests from this work:** 268 (daily trial changes, back for two fixes), 271 (read-step fixes, back for four), 270 (trial-first specification, being extended), 273 (D1 draft, for the operator), and claim merge and rename, not yet opened.

Operator decisions already made today and binding here: audited Reddit claims publish without a further go-ahead; the rekey waits for the operator's reading of its survey counts; older leads are worked in nightly slices after tonight; "successful" is never worded, registry facts only; every trial gets a plain page once pages are served on request; the operator will write to the banned publisher; the cheaper model for deterministic token-heavy work, the stronger for design and judgement.

## Goals / Non-Goals

**Goals:**
- By morning: Reddit claims audited and published; migrations applied behind a backup with the rekey survey ready to read; every trial reloaded with activity and results fields and the two sets counted; every pull request from the delegated sessions merged or waiting only on a named blocker or on the operator.
- Spend no more than $10 of model money tonight and stay inside every source's allowance.
- Leave nothing running that the 04:30 daily job could collide with.

**Non-Goals:**
- Applying the rekey. It rewrites about 680,000 keys and merges leads; the operator reads the counts first.
- Building anything from the trial-first or D1 changes. Their specifications are reviewed, not implemented.
- Searching for articles from the trial side. That waits for the trial-first change and its batching experiment.
- Pre-2025 leads. They start with tomorrow night's slice.

## Decisions

### Three lanes, one writer

Only this session writes to the working database. Work is in three lanes that do not wait on each other:

1. **Data lane (this session, sequential):** Reddit reads end, prepare, audit, attach duplicate articles, publish; then backup, migrations, rekey survey; then the trial reload.
2. **Code lane (delegated sessions):** fixes to 268 and 271, the wider trial record, claim merge and rename. Each ends in a pull request, reviewed and merged under the delegated-work rules.
3. **Specification lane (delegated sessions):** trial-first with its batching experiment; D1 draft. Reviewed for the operator; merged as documents when coherent, since they change no behaviour.

Alternative considered: letting sessions run their own database steps to save time. Rejected: two writers on one database with a migration pending is how the night goes wrong.

### Order in the data lane, and why

| # | Step | Depends on | Time | Cost |
|---|---|---|---|---|
| D1 | Reddit reads to the end | running | ~40 min | ~$0.50 |
| D2 | Prepare what the reads drafted | D1 | ~20 min | ~$0.30 |
| D3 | Audit round 2 (about 320 claims) and overrides | D2 | ~15 min | subagent tokens |
| D4 | Attach archived duplicates' articles to their published claims | D3 | 5 min | $0 |
| D5 | Export, data pull request, merge, verify live | D4 | ~20 min | $0 |
| D6 | Pause the daily job; `pg_dump` to the external drive; check the dump restores a table | D5, no run in progress | ~10 min | $0 |
| D7 | Read migration 0028; apply 0027 and 0028 | D6 | 5 min | $0 |
| D8 | `rekey-links` survey (read only); write counts and examples for the operator | D7 | ~10 min | $0 |
| D9 | Reload all trials with the wider record | D7 and the code lane's wider-record pull request merged | ~25 min | $0, 468 requests |
| D10 | Count the two sets; resume the daily job on its existing checkout | D9 | 5 min | $0 |

The publish (D5) comes before the migration (D6 to D8) so that what the operator already agreed to is live before anything structural is touched. The daily job stays on its pre-0027 checkout until the rekey is applied: old code runs unchanged against the added column, and a lead it loads in old form is covered by the rekey when it is applied.

If D9's pull request is not merged by 02:30 UTC, D9 and D10 move to the morning and the daily job is resumed without them.

### The wider trial record

One delegated task on the cheaper model, with exact instructions: add the fields named in the registry-corpus delta to what the load asks the registry for and stores; one additive migration (numbered after whatever is on main when it is written); the two sets as selections over stored trials, not as registry queries; reloading marks nothing due unless a listing field changed. Fixtures re-recorded with the generic client name. The trial-first session is asked which fields it needs before this task starts, so the reload happens once.

### Who runs on which model tonight

| Work | Model | Why |
|---|---|---|
| Audit packs under the written brief | Opus 5.5 | Token-heavy, rule by rule |
| Deciding the auditors' flagged judgement calls, overrides | Fable 5.2 (this session) | Judgement |
| Fix rounds on 268 and 271; wider trial record | Opus 5.5 | Instructions settle the work |
| Code review of every pull request | Fable 5.2 | What a review misses is the cost |
| Trial-first specification, D1 draft, claim merge and rename | Fable 5.2 | Design |
| Running loads, migrations, exports | no model | Scripts |

### Merging fast

- A review starts when a pull request's first complete push lands, not when its checks finish.
- Clean review: bring the branch up to date, set it to merge on green. A watcher re-updates any approved branch that falls behind main, since each merge leaves the others behind.
- Blocking finding: back to its session once, with files and fixes; re-read on push; merge.
- Non-blocking findings: merge, list as follow-ups in the pull request.
- A session is archived when its pull request merges.
- Pull requests from other sessions of the operator's (267, 269 and site work) are not this plan's to merge.

### Stops

The data lane stops and leaves a note, without retrying, when: model spend tonight reaches $10; the page reader answers `ROUTER_BUSY` repeatedly or reads slow well past 7 seconds (drop to 3 in flight first); the dump cannot be verified; a migration fails; the audit archives more than 70% of a round (publish what cleared, do not start another read run); a deployment's checks fail twice.

## Risks / Trade-offs

- **Migration applied, rekey not.** New-code link steps refuse until the rekey. Accepted: nothing tonight runs link steps on new code, and the refusal is the safe direction.
- **0028 is another session's migration.** It is read before it is applied; if it is not additive it is not applied tonight and D9 waits.
- **Audit by subagents on the cheaper model.** The brief is unchanged and the flagged cases still get the stronger model's decision; the archive rate is compared with round 1 (51%) and a jump either way is reported.
- **Merging around non-blocking findings** leaves follow-ups. Accepted for momentum; each is listed where the next session will see it.
- **The 04:30 job overlaps a late step.** The job is paused from D6 and resumed at D10 or at 04:15, whichever is first; a paused day leaves one line in its log.

## Morning list for the operator

1. Rekey survey counts: apply or not.
2. The two trial sets' sizes, and the trial-first change's decisions, including whether to pay for a paper-to-news index.
3. The D1 draft's decisions (pull request 273).
4. The letter to the banned publisher.
5. A spot check of 50 of last night's published claims.
