# Tasks

## 1. Pipeline

- [x] 1.1 `load_trials` ends with a `stopped` reason on a source stop, keeping what it stored and not recording the load as completed; verify "The allowance runs out part way" with the recorded pages
- [x] 1.2 `load-trials` prints the counts and a `Stopped:` line and exits 0 on that stop; verify with `--trials interventional --changes-only` and an allowance of one request

- [x] 1.3 A "too many requests" that outlasts the client's retries raises `SourceThrottled`; `load-trials` records the pause through the shared allowance and stops with exit 0; verify "The registry asks the load to wait" with a 429 on the second page

## 2. Daily run

- [x] 2.1 Add the `trials` step before `refresh`, its line and any `Stopped:` line in the summary; verify order, command and summary with the stand-in
- [x] 2.2 Never start `news_search`; verify in every case of `make scripts-test`
- [x] 2.3 Take the database address from `DATABASE_URL`, `DAILY_RUN_DATABASE_URL` or `.env`, stop when there is none, never log it; verify "No database address"
- [x] 2.4 `plist` writes `DAILY_RUN_DATABASE_URL` as `DATABASE_URL`, escaped for XML, and leaves the entry out with a warning when unset; verify with `plutil -lint`
- [x] 2.5 The summary names where the database address came from; `plist` says to install it mode 600, and the documented install line does (`umask 077`)
- [x] 2.6 Document the minimum allowance for the first full load (about 470 requests in one period)
- [x] 2.7 `docs/daily-run.md` (step, what becomes due, prerequisite) and `.env.example`

## 3. On the Mac mini, by the operator

- [ ] 3.1 After migration 0027 is applied, run the changes-only load once by hand and read its counts
- [ ] 3.2 Put `DAILY_RUN_DATABASE_URL` in `.env`, write the property list again mode 600, and load it again in place of the hand-edited one (mode 644 now)
