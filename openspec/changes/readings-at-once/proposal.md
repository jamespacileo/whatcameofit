# Proposal

## Why

`thenwhat prepare` is the ceiling on how fast claims are published, and the readings step is its largest part. On the fifteen claims prepared on 2026-11-15 the steps took 1,039 seconds in all: readings 413 (39%), fetch 392 (37%), resolve 229 (22%). Readings asks the model about one trial at a time and waits for each answer: 128 seconds for a claim with 33 trials, about four seconds a trial, although no answer depends on another.

## What Changes

- The readings step asks the model about several trials at a time (`READINGS_AT_ONCE`, 6 unless set, 1 to 16) and keeps the answers in the trials' order. Each call's cost is recorded as before, and a call that fails is reported while the others of its group stand.
- The monthly spend ceiling is looked at before each group, not before each trial. A run can therefore pass the ceiling by the cost of one group's calls at most; with the default that is five calls more than before, well under a cent at the prices recorded so far.
- `Llm.run_many` is the model client's door for this: the refusals of a single call made once for the group, then the calls together on the loop the single calls use.

Out of scope: the fetch step, which downloads each approved trial's whole record again and is the next largest part; starting a process for every step of `prepare`; batching several trials into one model call, which would change what the model is shown.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `record-readings`: trials are read several at a time; the spend ceiling is looked at before each group.

## Impact

- `pipeline/src/thenwhat/llm/client.py`: `run_many`. It reaches the event loop through `pydantic_ai._utils.run_until_complete`, which is not part of the library's public interface; a library upgrade that moves it fails at import, in every test.
- `pipeline/src/thenwhat/readings/service.py`: `read_trials` takes `at_once`; `store_read` keeps one answer.
- `pipeline/src/thenwhat/config.py`, `.env.example`, `README.md`: `READINGS_AT_ONCE`.
