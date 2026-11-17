# Tasks

## 1. Scripts

- [x] 1.1 `--since-days N` in `scripts/fetch_link_files.py`: one windowed query, merged into each month's file. Verify: a stand-in client over an archive-shaped and a fetched month file; one live count query.
- [x] 1.2 `scripts/daily-run.sh`: fetch the window (`DAILY_RUN_FETCH_DAYS`, default 3), load each month's file it touched. Verify: `scripts/tests/daily-run.test.sh`.
- [x] 1.3 `docs/daily-run.md`, `docs/sources.md`, `.env.example`.
