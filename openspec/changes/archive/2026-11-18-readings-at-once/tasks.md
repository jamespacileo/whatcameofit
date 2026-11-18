# Tasks

## 1. Several trials at a time

- [x] 1.1 Add `Llm.run_many`: the configuration and ceiling refusals made once, the calls made together, each call's cost recorded, a failed call returned in its place; verify through the readings tests below
- [x] 1.2 Have `read_trials` ask about `at_once` trials at a time and keep the answers in order; verify with tests that two calls wait on the model together and never three in groups of two, that every trial's read and cost are stored, and that a call that fails in a group is reported while the other stands
- [x] 1.3 Look at the ceiling before each group; verify with a test that a run of three trials in groups of two stops after the first group and leaves the third unread, and that the existing ceiling test at one trial at a time is unchanged
- [x] 1.4 Add `READINGS_AT_ONCE` (6 unless set, 1 to 16) to the settings, `.env.example` and the README, and have the command pass it

## 2. Integration

- [x] 2.1 Run `ruff`, `ty` and `pytest` for the pipeline
- [ ] 2.2 For the session that runs `prepare`: after a run on the real database, record here the readings step's seconds a trial before and after. Not measured yet: the figure in the proposal is from before the change, and no run with the change has asked a real model.
