# Proposal

## Why

A source client kept to its source's rate only inside its own process. `thenwhat prepare` starts a process for every step of every claim and works on four claims at once by default, so four processes could ask ClinicalTrials.gov at once, each at the full rate: up to four times the configured rate, and above what the registry publishes. The `resolve` command also built two clients of the registry that did not take turns with each other. Measured on 2026-11-15 with four processes and an interval of half a second: twenty requests left in about three seconds, fifteen of them less than half a second after the one before.

The requirement was already that requests to a source do not exceed its configured rate. It did not say across what, and the code met it per process only.

## What Changes

- Every client of a source takes turns with every other client of that source, in every process, through the source's row in the allowance table. A client takes the next free time, writes it in a short transaction of its own, and waits for it with nothing held.
- A client that is handed a pacer keeps to that pacer alone, as before. No command hands one any more.
- The row is the one `source-allowances` already keeps, so a backfill step that claims a request and a client that asks the same source wait out the same times. Only the time of the latest turn is written here: no request is counted against an allowance.

Out of scope: counting the requests of `resolve`, `fetch` and `terms` against a source's allowance; running the steps of `prepare` in one process; the outlets' own spacing, which `lead-reading` covers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `source-clients`: the rate of a source holds across every client and every process that asks it.

## Impact

- `pipeline/src/thenwhat/sources/base.py`: `SharedTurns`, the default for every `Source`.
- `pipeline/src/thenwhat/cli/outlets.py`: no longer shares a pacer by hand.
- `source_allowance_use.last_request_at` can now hold a time a moment ahead of now: the turn a client has taken and is waiting for. `Allowances.claim` already waits correctly on such a time.
- One short transaction on a second connection for every request that is not answered from the cache.
