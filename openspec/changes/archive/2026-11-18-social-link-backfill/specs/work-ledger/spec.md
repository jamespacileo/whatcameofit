# Spec Delta

## ADDED Requirements

### Requirement: A step that asks no source
A step SHALL be able to declare that it asks no source. Such a step SHALL need no allowance, and the plan SHALL show no requests and no hours for it.

#### Scenario: Planning a step that only reads the database
- **WHEN** the plan is run with 50,000 records due for a step that asks no source
- **THEN** it shows 50,000 due and zero requests, and does not ask for an allowance

### Requirement: A step that spends model budget
A step SHALL be able to declare that it calls a model, with an estimate of the input and output tokens one record needs. The plan SHALL show the estimated cost of its due records at the configured prices beside what is left of the month's ceiling, and how many records the remainder covers. The plan SHALL refuse to give a cost while the prices are not configured.

#### Scenario: Planning a model step
- **WHEN** the plan is run with 100,000 records due for a step estimated at 40 input tokens a record
- **THEN** it shows the estimated cost, the ceiling remaining this month, and whether the due records fit

#### Scenario: Prices not configured
- **WHEN** the plan is run for a model step and no price is configured
- **THEN** the plan names the missing setting and gives no cost for that step

### Requirement: The spend ceiling stops a model step
When the month's recorded model cost reaches the ceiling during a run of a step that calls a model, the run SHALL stop, the records not yet processed SHALL stay due, and no attempt SHALL be counted against them.

#### Scenario: Ceiling reached during a run
- **WHEN** the month's recorded cost reaches the ceiling while a model step is running
- **THEN** the run stops and says why, and the unprocessed records are still due with their attempt counts unchanged

### Requirement: Several records in one call
A step SHALL be able to process a declared number of records in one call. The records of one call SHALL be held together, and their results and ledger entries SHALL be saved together or not at all. When a call fails, its records SHALL be processed one at a time in the same run, so that only a record that fails alone has a failure recorded.

#### Scenario: A batch of twenty
- **WHEN** a step that takes twenty records a call runs over 100 due records
- **THEN** five calls are made and 100 ledger entries are written

#### Scenario: One bad record in a batch
- **WHEN** one record of a batch of twenty gets no answer
- **THEN** the other nineteen are finished, and only that record's entry records a failure

#### Scenario: Two runs and batches
- **WHEN** two processes run the same batch step over 200 due records
- **THEN** each record is processed once
