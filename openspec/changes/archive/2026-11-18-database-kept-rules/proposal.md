# Proposal

## Why

An audit of the database on 2026-11-16 found rules that only the code kept, lookups that read whole tables, and a test that could not see a changed check. The stored data broke none of the rules, so the database can keep them from here on.

- A value added to an enum is a change to a check, and `alembic check` does not compare checks or column defaults. A model could gain a value with no migration and every test passed.
- 13,786 of 48,094 cached answers had expired, 205 MB of them. An expired answer is never used again: the request is sent afresh and the new answer replaces it. Nothing deleted one.
- With topic words set, triage picked its next twenty headlines in 8.9 seconds: every due headline, 145,000 of them, was matched against the words and sorted before each pick. 616 headlines in scope named a topic.

## What Changes

- The database refuses a second intervention entity for a claim, a promise, reported statement or link lead that names another claim's article, a failure flag that names another claim's event, and a negative count or cost. An article moved to another claim, as a duplicate's articles are, takes its promises, statements and leads with it.
- Foreign keys that had no index have one.
- A test compares every check and column default the models give with those the migrations give.
- `thenwhat cache-prune` deletes the cached answers that have expired and says how many.
- A step that wants some records first has them asked for on their own, and the rest by id. Once fewer are due than a pick asks for, the run stops asking for them: one that becomes due later in the same run takes its turn by id. Measured on a copy of the working database: 8.9 seconds a pick before; after, 6.5 and 2.6 seconds for the two picks that held topic headlines, then 8 ms a pick.

Not checked: that a published claim is approved. `published_at` records when a claim was first published and stays when the claim is later rejected, so the rule would refuse a rejection.

Out of scope, each a decision for the operator: how long the decision log is kept (485,000 rows in five days, and triage reads its own decisions back from it); a registry record's payload being stored with the cached answer, the registry trial and each evidence event; source and platform names kept as free text.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `source-clients`: expired cached answers can be deleted.
- `work-ledger`: the records a step wants first are taken first, without weighing every due record at each pick.

## Impact

- `pipeline/migrations/versions/0030_rules_the_code_kept_alone.py`, `pipeline/src/thenwhat/db/models.py`.
- `pipeline/src/thenwhat/sources/base.py`: `forget_expired`. `pipeline/src/thenwhat/cli/cache.py`: the command.
- `pipeline/src/thenwhat/backfill/ledger.py`: `take_due`, used by the runner. `link_triage.py` and `link_read.py` name their first records with `first()`.
- `pipeline/tests/test_migrations.py`: the comparison of checks and defaults.
