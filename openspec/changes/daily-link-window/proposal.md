# Proposal

## Why

The daily run fetched the whole current month of Hacker News links each night. The public ClickHouse copy allows about 20 queries an hour and 10,000 rows a query, so the first real run spent 2 hours 34 minutes on that step. On 2026-11-17 the operator chose to fetch only the last three days each night.

## What Changes

- `scripts/fetch_link_files.py hackernews --since-days N` asks only for the stories with a link posted since midnight UTC N days ago (1 to 28), and merges them into each month's file the window touches without dropping a row already there. The month form is unchanged.
- The daily run's fetch uses that window, `DAILY_RUN_FETCH_DAYS` (default 3), then loads each month's file the window touched, oldest first.

## Capabilities

### Modified Capabilities

- `daily-run`: the nightly link fetch is a rolling window.

## Impact

- `scripts/fetch_link_files.py`, `scripts/daily-run.sh`, `scripts/tests/daily-run.test.sh`, `docs/daily-run.md`, `docs/sources.md`, `.env.example`.
- A nightly run makes one ClickHouse query (2,867 stories for three days on 2026-11-17) in place of a month's pages.
