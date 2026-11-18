# Tasks

## 1. Turns shared across processes

- [x] 1.1 Add `SharedTurns` to `sources/base.py`: the next free time taken under a lock on the source's allowance row, written in its own transaction, waited for with nothing held; verify with a test that two clients of one source that share nothing but its name keep to its rate between them
- [x] 1.2 Make it the default for every `Source` and stop `outlets measure` sharing a pacer by hand; verify with a test on two connections that two sessions' clients keep to the rate together, and that the existing burst test still spreads ten requests over three seconds
- [x] 1.3 Measure with four real processes against a test database, before and after, and record the figures below

## 2. Integration

- [x] 2.1 Run `ruff`, `ty` and `pytest` for the pipeline

## Measured on 2026-11-15

Four processes, five requests each, an interval of half a second, on a test database of this branch's own while the shared server was busy with a backfill run.

| | 20 requests took | smallest gap | gaps under 0.5 s |
|---|---|---|---|
| a pacer per process (before) | 3.1 s | 0.000 s | 15 of 19 |
| shared turns (after), run 1 | 10.2 s | 0.488 s | 1 of 19 |
| shared turns (after), run 2 | 10.3 s | 0.495 s | 0 of 19 |

A first version held the row's lock while it waited and wrote the time after waiting. Its turns were the interval apart, but a request left only when the transaction had been committed, and on the busy server a commit took up to a third of a second: 6 of 19 gaps were under half a second, the smallest 0.008 s. Taking the time first and waiting with nothing held removed that.
