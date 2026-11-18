# work-ledger Specification

## Purpose
Records which step has been completed for which record, so that large runs can stop, resume and grow new kinds of processing without doing finished work again.

## Requirements

### Requirement: Step declaration
Each step SHALL declare a name, a version, the kind of record it applies to, the condition a record must meet to be in scope, the source it asks, and the number of requests one record needs. The pipeline SHALL refuse to start when two steps share a name.

#### Scenario: Listing steps
- **WHEN** the operator lists the steps
- **THEN** each step is shown with its name, version, record kind, source and requests per record

#### Scenario: Two steps with one name
- **WHEN** two steps are declared with the same name
- **THEN** every backfill command fails and names the duplicate

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

#### Scenario: A waiting claim is backed up and restored
- **WHEN** the bulk store is built or updated with a claim whose step is put off or needs a fix
- **THEN** the stored entry retains its outcome, reason and reason values, the first time it was put off and its retry time where present, so restoring it preserves when and why the claim is due

#### Scenario: A reason the step did not declare
- **WHEN** a step answers with a reason code it has not declared
- **THEN** the run fails for that record with an error naming the code, and no entry holds it

#### Scenario: A manually attached historical lead is upgraded

- **WHEN** a lead was manually attached to a claim after an earlier unresolved read and migration 0037 sees added_to_claim beside a nothing_found work entry
- **THEN** the upgrade keeps the claim, article and audit detail on the lead. The earlier read stays terminal with outcome `nothing_found` and reason `already_tracked`. Genuinely unmapped legacy states are still reported

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

#### Scenario: Adding a paper changes the lookup inputs

- **WHEN** a prepared claim gains a paper entity with a new DOI and is prepared again
- **THEN** the responsible lookup becomes due, asks Crossref about the new DOI and becomes current after success

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

#### Scenario: A limited run puts a record off
- **WHEN** a run limited to one record works on a record and receives a temporary refusal
- **THEN** that record is put off with zero attempts and the run ends at its limit, across all workers

#### Scenario: A hold is known before a read starts
- **WHEN** a limited read finds an existing outlet hold before asking for a lead
- **THEN** it puts that lead off and can use its remaining limit on another lead

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

### Requirement: Records a step wants first
A step MAY name a condition for the records it wants before every other. A run SHALL take the due records that meet it first and fill what is left of a pick with the other due records. Once fewer of them are due than a pick asks for, the run SHALL stop asking for them: a record that meets the condition later in the same run takes its turn among the rest. The condition SHALL change only when a record is processed, never whether.

#### Scenario: A topic lead among older leads
- **WHEN** twenty-five older leads and one newer lead that names a topic are due, and a pick takes twenty
- **THEN** the lead that names a topic is in the first pick

#### Scenario: Fewer topic leads than a call takes
- **WHEN** twenty-five older leads and two that name a topic are due, and a pick takes twenty
- **THEN** the first pick holds both topic leads and the eighteen oldest of the rest, the second holds the other seven, and each lead is processed once

### Requirement: An outcome says whether the record comes back
Every outcome a step gives SHALL be one of three classes. Final: done or nothing found, and the record is finished. Later: the cause is expected to pass, and the record comes back by itself. Needs a fix: the cause will not pass until something outside the record changes, and the record waits. A step SHALL NOT record as final a cause that it cannot tell from one that passes.

#### Scenario: A source that is down
- **WHEN** a step cannot get an answer for a record because its source failed
- **THEN** the outcome is later or failed, never nothing found

#### Scenario: A record nothing can be done with
- **WHEN** a step establishes that a record holds nothing for it
- **THEN** the outcome is nothing found, with the reason

#### Scenario: A cited paper awaits a configured source

- **WHEN** an article explicitly cites a DOI and OpenAlex is unconfigured during named-record preparation
- **THEN** the citation stays identifiable as unfinished. After configuration and the normal recovery or requeue step, the DOI is looked up and the step can complete

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

#### Scenario: A successful retry races with requeue

- **WHEN** requeue selects a site_busy record and a worker commits a successful retry before requeue updates it
- **THEN** the completed entry and successful lead outcome survive. Requeue counts only entries it actually changed

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

#### Scenario: One worker reports a provider-wide outage

- **WHEN** one of two workers reports a source-wide stop while its sibling is handling a record and more records remain due
- **THEN** the run stops taking new records across workers. The triggering and unprocessed records remain due with no attempts charged for the outage

#### Scenario: The model budget is exhausted during non-model work

- **WHEN** the monthly model ceiling is reached and a registry fetch or rule-only decision is due
- **THEN** both can proceed without a model call. A step that actually needs the model respects the ceiling and keeps the affected record due

### Requirement: A step can depend on another step
A step SHALL be able to declare the steps that must have finished for a record before it is due. A record SHALL be due for it only when each of those steps has an entry of done or nothing found for the record at that step's current version and for the record's current input.

#### Scenario: A step waiting for another
- **WHEN** a claim's registry search has not finished
- **THEN** the claim is not due for the step that decides it

#### Scenario: The earlier step is due again
- **WHEN** a claim's intervention is renamed after it was searched and decided
- **THEN** the claim is due for the search, and not for a later step until the search has finished again

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
