# Proposal

## Why

The no-signal note counted from the claim's latest approved event, and from the first report only when there were no events. The first dental run (2026-11-11) showed the result: a treatment reported in the news in September 2018, whose only approved record is a trial registered in March 2013, read "No signal for 13 years". The report is itself the latest thing known about the claim; the claim cannot have been quiet for longer than it has been reported.

## What Changes

- The quiet period runs from the later of the first news report and the latest approved event.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `status-derivation`: where the no-signal period starts.

## Impact

- `status/rules.py`, one rule. Pure: no database, network or clock.
- Claims whose records all predate their report show a shorter quiet period, or none. No other status changes.
