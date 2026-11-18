# Tasks

## 1. Rules kept by the database

- [x] 1.1 Migration `0030`: one intervention entity a claim, a row's article and event of its own claim, counts and costs not negative; verify that the working database holds no row that breaks one
- [x] 1.2 Index the foreign keys that had no index
- [x] 1.3 Compare the models' checks and column defaults with the migrations' in a test; verify that it fails when a model's check is changed and `alembic check` still passes

## 2. Expired cached answers

- [x] 2.1 `forget_expired` and `thenwhat cache-prune`; verify with one expired and one fresh answer, and the refusal without `DATABASE_URL`

## 3. The next due records

- [x] 3.1 `take_due`: a step's first records asked for on their own, then the rest by id; verify with fewer topic leads than a call takes
- [x] 3.2 Measure on a copy of the working database, before and after, and record the figures in the proposal

## 4. Integration

- [x] 4.1 Run `ruff`, `ty` and `pytest` for the pipeline
