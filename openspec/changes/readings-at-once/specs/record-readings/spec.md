# Record readings: changes

## MODIFIED Requirements

### Requirement: The same record gives the same readings
Readings SHALL be kept with the record they were read from, the version of the instructions given to the model, the provider and model named by the environment, and how sure the reading is. A trial whose stored record and instructions have not changed SHALL NOT be read again. Readings SHALL be recorded as decided by a model, never by a person. Trials MAY be read several at a time, up to a configured number; each trial SHALL still be read on its own, shown nothing of another trial, and the monthly spend ceiling SHALL be looked at before each group of trials.

#### Scenario: Second run with nothing changed
- **WHEN** the step is run twice and no trial's record has changed
- **THEN** the second run asks the model nothing and the readings are unchanged

#### Scenario: Record fetched again with a new time frame
- **WHEN** a trial's record is fetched again and its main measure's time frame has changed
- **THEN** the trial is read again and the earlier reading is replaced

#### Scenario: Spend ceiling reached
- **WHEN** the monthly spend ceiling is reached part way through a run
- **THEN** the run stops before the next group of trials, says so, and trials not yet read have no reading

#### Scenario: Several trials read at once
- **WHEN** three trials are read two at a time
- **THEN** two are asked about together, each call's cost is recorded, and every trial's readings are stored as they would be one at a time

#### Scenario: A call fails among several
- **WHEN** one of the trials asked about together cannot be read
- **THEN** that trial is reported and keeps what it had, and the others' readings are stored
