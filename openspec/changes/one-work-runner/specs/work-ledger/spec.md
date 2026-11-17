# Spec Delta

## MODIFIED Requirements

### Requirement: Ledger entry
The ledger SHALL hold at most one entry per record, step and step version. An entry SHALL record the outcome (done, nothing found, later, needs a fix, or failed), the number of attempts, the time of the last attempt, the number of requests used, a fingerprint of the record's input, and the error text when it failed. An entry whose outcome is nothing found, later or needs a fix SHALL record a reason code from the step's declared reasons, with any values the reason carries. An entry whose outcome is later SHALL record the time before which the record is not to be tried.

#### Scenario: A record is processed
- **WHEN** a step finishes a record
- **THEN** one ledger entry exists for that record, step and version, with its outcome, attempt count, time and requests used

#### Scenario: A record is processed twice
- **WHEN** the same step at the same version is run again for a record that failed
- **THEN** the existing entry is updated and its attempt count rises by one, and no second entry is created

#### Scenario: A record to be tried later
- **WHEN** a step answers that a record cannot be worked on before a time, for a reason
- **THEN** its entry holds the outcome later, that reason's code and that time

#### Scenario: A reason the step did not declare
- **WHEN** a step answers with a reason code it has not declared
- **THEN** the run fails for that record with an error naming the code, and no entry holds it

### Requirement: Due work
A record SHALL be due for a step when it is in the step's scope and has no ledger entry for that step at its current version with the outcome done, nothing found or needs a fix. A record whose input fingerprint differs from the one in its entry SHALL also be due. A record whose entry holds the outcome later SHALL be due once the time it records has passed, and not before.

#### Scenario: Finished records are skipped
- **WHEN** a step is run and 900 of 1,000 records in scope have an entry with the outcome done or nothing found
- **THEN** only the other 100 records are processed

#### Scenario: A record changed
- **WHEN** a record's input differs from the fingerprint in its ledger entry
- **THEN** that record is due again for that step

#### Scenario: A record out of scope
- **WHEN** a record does not meet a step's condition
- **THEN** it is never due for that step and gets no ledger entry

#### Scenario: A record whose time has not come
- **WHEN** a record's entry says later with a time one hour ahead
- **THEN** a run now does not take it, and a run two hours from now does

#### Scenario: A record that needs a fix
- **WHEN** a record's entry says it needs a fix
- **THEN** no run takes it until its input changes or it is made due by its reason

### Requirement: Failed records
A failure on one record SHALL be recorded in its entry and SHALL NOT stop the run. A failed record SHALL stay due until its attempts reach the configured limit, after which it is skipped and reported. An outcome of later or needs a fix SHALL count no attempt. A record at the limit SHALL be made due again, with its attempts at zero, when it is made due by the operator.

#### Scenario: One record fails
- **WHEN** a step fails on one record of ten
- **THEN** the other nine are processed and the run reports one failure with its error

#### Scenario: Attempt limit reached
- **WHEN** a record has failed as many times as the limit allows
- **THEN** it is no longer due, and the plan lists it as needing attention

#### Scenario: A record put off three times
- **WHEN** a record has been answered later three times and the limit is three
- **THEN** its attempt count is zero and it is due when its time has passed

#### Scenario: A record at the limit is made due
- **WHEN** the operator makes due a record that reached the attempt limit
- **THEN** it is due, and it may fail as many times again as the limit allows

## ADDED Requirements

### Requirement: An outcome says whether the record comes back
Every outcome a step gives SHALL be one of three classes. Final: done or nothing found, and the record is finished. Later: the cause is expected to pass, and the record comes back by itself. Needs a fix: the cause will not pass until something outside the record changes, and the record waits. A step SHALL NOT record as final a cause that it cannot tell from one that passes.

#### Scenario: A source that is down
- **WHEN** a step cannot get an answer for a record because its source failed
- **THEN** the outcome is later or failed, never nothing found

#### Scenario: A record nothing can be done with
- **WHEN** a step establishes that a record holds nothing for it
- **THEN** the outcome is nothing found, with the reason

### Requirement: A record put off too long is said to need a fix
A record answered later for the same reason over a configured span, thirty days unless set, SHALL be recorded as needing a fix with that reason, so that it is listed and not asked for without end.

#### Scenario: An outlet that never comes back
- **WHEN** a record has been put off for one reason on every try for more than the span
- **THEN** its entry says it needs a fix for that reason, and no run takes it

### Requirement: Records are made due by step and reason
`thenwhat work requeue <step> --reason <code>` SHALL make due every record of that step whose entry holds that reason, and SHALL say how many. It SHALL take further conditions on the values the reason carries. It SHALL ask no source and no model. With `--dry-run` it SHALL change nothing and report the same count.

#### Scenario: A parser was fixed
- **WHEN** 64 leads were refused because their page gave no publication date, and the operator requeues that reason
- **THEN** those 64 leads are due for the read and no other lead is

#### Scenario: One outlet
- **WHEN** the operator requeues the reason for a site's refusal with a condition naming one outlet
- **THEN** only that outlet's leads are due

#### Scenario: An unknown reason
- **WHEN** the operator names a reason the step has not declared
- **THEN** the command is refused, lists the step's reasons, and changes nothing

### Requirement: Reasons are counted in the plan
`thenwhat backfill plan` SHALL show, for each step, the records waiting by class and reason: how many are put off and until when the first is due, and how many need a fix for each reason.

#### Scenario: Planning with records waiting
- **WHEN** 300 leads are put off for a site that cannot serve now and 64 need a fix for a missing date
- **THEN** the plan shows both counts under the read, each with its reason

### Requirement: A provider that cannot be asked stops the run
When a source, the page reader or a model cannot be asked at all, for an outage, a refused key, an exhausted quota or the spend ceiling, the run SHALL stop. The record in hand and every record not yet processed SHALL stay due, and no attempt SHALL be counted against any of them. This SHALL hold for every step and for every call a step makes, whichever part of the step made it.

#### Scenario: The model goes away during a read
- **WHEN** the model cannot be reached while a step is reading its fifth record of fifty
- **THEN** the run stops and says why, four records are finished, and the other forty-six are due with their attempt counts unchanged

#### Scenario: The ceiling is reached inside a decision
- **WHEN** the month's ceiling is reached by a decision a step asks after its first model call
- **THEN** the run stops as for any ceiling, and the record is not recorded as failed

### Requirement: A step can depend on another step
A step SHALL be able to declare the steps that must have finished for a record before it is due. A record SHALL be due for it only when each of those steps has an entry of done or nothing found for the record at that step's current version and for the record's current input.

#### Scenario: A step waiting for another
- **WHEN** a claim's registry search has not finished
- **THEN** the claim is not due for the step that decides it

#### Scenario: The earlier step is due again
- **WHEN** a claim's intervention is renamed after it was searched and decided
- **THEN** the claim is due for the search, and not for a later step until the search has finished again
