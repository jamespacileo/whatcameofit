# Spec Delta

## ADDED Requirements

### Requirement: The runner measures every step it runs
Every record a step handles through the work ledger's runner SHALL be measured by the runner itself, for lead steps and claim steps alike, so that no step can be run unmeasured and none measures itself. The measurement SHALL hold, beside what every measurement holds, the run it belongs to, the class of its outcome and its reason code.

#### Scenario: A step added later
- **WHEN** a new step is declared and run, and its code says nothing about measuring
- **THEN** each record it handles has a measurement with its time, waits, requests, cost and outcome

#### Scenario: A record put off
- **WHEN** a lead is put off because its site answered 503
- **THEN** its measurement says it was put off, with that reason's code

### Requirement: Every wait is given its cause
Time a record spends not being worked on SHALL be measured as waiting, under the one cause that held it: a source's pacing, a source's pause, an outlet's turn or gap, a place among the page reader's requests in flight, a delay before a retry, the turn that settles which claim an article reports, or a row another run holds. Time that is none of these SHALL be measured as running.

#### Scenario: A read that waits for the claim turn
- **WHEN** a read waits 12 seconds for another read to finish settling its claim, and then takes 2 seconds
- **THEN** its measurement gives 12 seconds waiting on the claim turn and 2 seconds running

#### Scenario: A retry
- **WHEN** a registry answers too-many-requests and the request succeeds 8 seconds later
- **THEN** the measurement gives 8 seconds waiting on a retry for that registry, and two requests

### Requirement: What happens to a run is recorded as it happens
A run SHALL record, with the time of each: that it started, with its step, its limit and its workers; that it ended, with why (nothing due, the limit, a provider that cannot be asked, the spend ceiling, stopped by the operator) and its counts; that a source was paused and until when; and that records were made due, with the step, the reason and how many.

#### Scenario: A run stopped by a quota
- **WHEN** a model's quota is used up during a run
- **THEN** an event records that the run ended for that cause, at that time, with how many records were finished and how many stay due

#### Scenario: A source is paused
- **WHEN** a registry states a wait longer than the ceiling
- **THEN** an event records the source and the time it is paused until

### Requirement: A run can be watched while it works
`thenwhat measure --live` SHALL show, refreshed at least every five seconds from another process while runs are at work, for the last one, five and fifteen minutes: for each step, records finished a minute by outcome, the share of time running and waiting by cause, cost a minute and cost a record; the records in hand and how long the oldest has been; the sources paused; and the month's spend against its ceiling. It SHALL name the cause most time was spent waiting on. It SHALL change nothing and ask no source.

#### Scenario: Reads held up by one outlet's pacing
- **WHEN** four workers read leads and most of their time goes to waiting for outlets' turns
- **THEN** the view shows the read's waiting share by cause and names the outlet's turn as the largest

#### Scenario: Nothing is running
- **WHEN** no run has recorded anything in the last fifteen minutes
- **THEN** the view says so, and shows the last run's ending and why it ended

#### Scenario: A measurement reaches the view
- **WHEN** a record finishes
- **THEN** the view counts it within five seconds

### Requirement: Measuring costs the work almost nothing
Recording a measurement SHALL send no request, call no model and make no statement to the database. A worker SHALL hand a finished measurement on and continue: writing it SHALL be done apart from the work, several at a time. With measuring on, a step that asks no source SHALL handle at least 95 of every 100 records it handles with measuring off, over the same records.

#### Scenario: Screening a large backlog
- **WHEN** screening handles 500,000 leads with measuring on
- **THEN** no statement to the database is made for any measurement, and the run takes no more than a twentieth longer than with measuring off

### Requirement: A measurement is never lost without being said
Measurements SHALL NOT be dropped to keep up: when they cannot be written as fast as they are made, the work SHALL wait for them. When a measurement cannot be written at all, the run SHALL go on, SHALL count what was not written, and SHALL say so when it ends, in an event, and in the live view. A report over a span of time with measurements not written SHALL say how many.

#### Scenario: The folder cannot be written
- **WHEN** measurements cannot be written during a run
- **THEN** the run finishes its work, reports how many measurements were not written, and the day's report says the same

#### Scenario: A burst of finished records
- **WHEN** records finish faster than their measurements are written
- **THEN** every measurement is written, and none is left out
