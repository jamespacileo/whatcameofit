# Spec Delta

## Purpose

Records which step has been completed for which record, so that large runs can stop, resume and grow new kinds of processing without doing finished work again.

## ADDED Requirements

### Requirement: Step declaration
Each step SHALL declare a name, a version, the kind of record it applies to, the condition a record must meet to be in scope, the source it asks, and the number of requests one record needs. The pipeline SHALL refuse to start when two steps share a name.

#### Scenario: Listing steps
- **WHEN** the operator lists the steps
- **THEN** each step is shown with its name, version, record kind, source and requests per record

#### Scenario: Two steps with one name
- **WHEN** two steps are declared with the same name
- **THEN** every backfill command fails and names the duplicate

### Requirement: Ledger entry
The ledger SHALL hold at most one entry per record, step and step version. An entry SHALL record the outcome (done, nothing found, or failed), the number of attempts, the time of the last attempt, the number of requests used, a fingerprint of the record's input, and the error text when it failed.

#### Scenario: A record is processed
- **WHEN** a step finishes a record
- **THEN** one ledger entry exists for that record, step and version, with its outcome, attempt count, time and requests used

#### Scenario: A record is processed twice
- **WHEN** the same step at the same version is run again for a record that failed
- **THEN** the existing entry is updated and its attempt count rises by one, and no second entry is created

### Requirement: Due work
A record SHALL be due for a step when it is in the step's scope and has no ledger entry for that step at its current version with the outcome done or nothing found. A record whose input fingerprint differs from the one in its entry SHALL also be due.

#### Scenario: Finished records are skipped
- **WHEN** a step is run and 900 of 1,000 records in scope have an entry with the outcome done or nothing found
- **THEN** only the other 100 records are processed

#### Scenario: A record changed
- **WHEN** a record's input differs from the fingerprint in its ledger entry
- **THEN** that record is due again for that step

#### Scenario: A record out of scope
- **WHEN** a record does not meet a step's condition
- **THEN** it is never due for that step and gets no ledger entry

### Requirement: A new step leaves other steps alone
Adding a step SHALL make every record in its scope due for that step only. Entries of other steps SHALL NOT change.

#### Scenario: Adding a step
- **WHEN** a second step is added after the first has finished 1,000 records
- **THEN** the second step has 1,000 records due and the first has none

### Requirement: Step version
Raising a step's version SHALL make every record in scope due for that step. Entries from earlier versions SHALL be kept.

#### Scenario: Version raised
- **WHEN** a step at version 1 has finished every record and its version is raised to 2
- **THEN** every record in scope is due for that step, and the version 1 entries remain

### Requirement: Result and entry are saved together
A step's stored result for a record and that record's ledger entry SHALL be saved together or not at all.

#### Scenario: Stopped between records
- **WHEN** a run is stopped while it is working
- **THEN** every record either has both its result and its entry, or has neither

### Requirement: Failed records
A failure on one record SHALL be recorded in its entry and SHALL NOT stop the run. A failed record SHALL stay due until its attempts reach the configured limit, after which it is skipped and reported.

#### Scenario: One record fails
- **WHEN** a step fails on one record of ten
- **THEN** the other nine are processed and the run reports one failure with its error

#### Scenario: Attempt limit reached
- **WHEN** a record has failed as many times as the limit allows
- **THEN** it is no longer due, and the plan lists it as needing attention

### Requirement: Several runs at once
Two runs of the same step at the same time SHALL NOT process the same record.

#### Scenario: Two processes
- **WHEN** two processes run the same step over 100 due records
- **THEN** each record is processed once, and the two processes' counts add up to 100

### Requirement: Plan before a run
`thenwhat backfill plan` SHALL report, for each step, the number of records in scope, done, nothing found, failed and due, the requests the due records need, the source's remaining allowance, and the time the due records take at the source's rate. It SHALL send no request and change nothing.

#### Scenario: Planning
- **WHEN** the operator runs `thenwhat backfill plan` with 43,000 records due for a step that needs one request per record at one request every five seconds
- **THEN** the output shows 43,000 due, 43,000 requests and about 60 hours, and no request is sent

#### Scenario: More work than allowance
- **WHEN** the due records need more requests than the source's allowance has left
- **THEN** the plan says how many records the remaining allowance covers

### Requirement: Running a step
`thenwhat backfill run <step>` SHALL process due records for the named step until none is due, a given limit of records is reached, or the source's allowance is used up. It SHALL finish by reporting how many records were done, found nothing, failed and remain due.

#### Scenario: Limited run
- **WHEN** the operator runs a step with a limit of 200 records
- **THEN** at most 200 records are processed and the report shows how many remain due

#### Scenario: Unknown step
- **WHEN** the operator names a step that does not exist
- **THEN** the command fails, lists the steps that do exist, and processes nothing

#### Scenario: Restart
- **WHEN** a run is stopped and started again
- **THEN** it continues with the records still due and repeats none that finished
