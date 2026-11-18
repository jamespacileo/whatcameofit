# record-readings Specification

## Purpose
Record readings are answers a model reads from a trial's stored registry record into fixed codes, so that the site can say in plain words what a rule cannot read. Each reading is checked by rule against the record before it is kept.

## Requirements

### Requirement: A reading is a code and the words it was read from
A reading SHALL consist of a kind from a fixed list, a value that is a code or a number with a unit from a fixed list, the registry identifier of the trial, the field of the record it was read from, and the exact words read. A reading SHALL NOT carry a sentence written by the model. The model SHALL be given only fields the trial's facts already carry: the titles and time frames of the planned primary outcomes.

#### Scenario: How long the main measure was followed
- **WHEN** a trial's main measure has the time frame "Baseline and week 4 after starting stimulation"
- **THEN** the reading of kind follow-up has the value 4 weeks and carries those words

#### Scenario: What kind of measure
- **WHEN** a trial's main measure is titled "Time Spent Using the Device Per Day of Use"
- **THEN** the reading of kind measure has the code for use of the treatment and carries that title

#### Scenario: Model returns a sentence
- **WHEN** the model's answer holds text outside the fixed fields
- **THEN** that text is not stored

### Requirement: A reading is checked by rule before it is stored
A reading SHALL be stored only when its words appear, character for character, in the named field of the trial's stored record, its kind and value are in the fixed lists, and a number with a unit can be found in its words. A follow-up SHALL NOT turn an explicit offset after a numbered or final treatment cycle, a later dose/infusion/session, or treatment completion into a duration from the start. The check SHALL inspect the full time-frame field so a short quote cannot discard that anchor. A reading that fails any check SHALL NOT be stored, and the reason SHALL be recorded. The checks SHALL be pure: no database, network or clock. These explicit boundaries do not constitute a general time-frame parser.

#### Scenario: Words not in the record
- **WHEN** the model returns a reading whose words are not in the record's field
- **THEN** the reading is not stored and the refusal names the reason

#### Scenario: Number the words do not give
- **WHEN** the model returns 12 weeks for a time frame that reads "Baseline and week 4"
- **THEN** the reading is not stored

#### Scenario: Code outside the list
- **WHEN** the model returns a kind of measure that is not in the fixed list
- **THEN** the reading is not stored

#### Scenario: Offset after a later cycle
- **WHEN** the time frame says "within 6 days after 3rd cycle" and the proposed follow-up quotes only "within 6 days"
- **THEN** the six-day reading is refused with the reason `later_event_offset`
- **AND** no total is calculated from the cycle schedule

#### Scenario: First dose or surgery as the start
- **WHEN** the time frame gives a duration after the first dose or surgery
- **THEN** the later-event rule does not refuse that duration solely because it has an anchor

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

### Requirement: Readings do not change status or trial facts
Readings SHALL NOT be inputs to a claim's status, to a match's score, or to a trial's facts. A claim's status, the events that explain it and its trials' facts SHALL be the same with and without readings.

#### Scenario: Claim with and without readings
- **WHEN** the export is built before and after the readings step is run
- **THEN** every claim's status and every trial's facts are identical

### Requirement: Readings are exported with their trial
The export SHALL carry each trial's stored readings that still pass the current pure checks and that the model gave at least `READING_ACCEPT_ABOVE` confidence (0.8 by default): kind, value, the field and words read, how sure the reading is, and the date the record was read. A reading that fails either gate SHALL NOT be exported, so the page and the data file give the registry's own words for that answer, with no looser reading in its place. A trial with no reading SHALL carry an empty list. The export SHALL be buildable with no network. Rechecking a stored reading SHALL NOT rewrite its provenance, ask a model or change the trial's facts or the claim's status.

#### Scenario: Trial with two readings
- **WHEN** a published claim's trial has a follow-up reading and a measure reading, both at or above the bar
- **THEN** the exported trial carries both, each with its words and how sure it is

#### Scenario: Reading below the bar
- **WHEN** a trial's follow-up reading was given 0.79 and its measure reading 0.9
- **THEN** the exported trial carries the measure reading only, and the page gives the registry's own time frame

#### Scenario: Export with no network
- **WHEN** the export is built on a machine with the database and no network
- **THEN** every stored reading at or above the bar that passes the current checks is present

#### Scenario: Older reading loses its later-cycle anchor
- **WHEN** an earlier read stored a six-day duration for an outcome assessed six days after the third cycle
- **THEN** export omits that duration and retains the full registry time frame
- **AND** the stored original reading remains unchanged and no model is asked
