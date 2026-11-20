# Spec Delta

## Purpose

Records how long each step of processing an address took, how long it waited, what it cost and how it ended, for every writer, so that time and cost can be reported by step and end to end and the pipeline tuned from evidence.

## ADDED Requirements

### Requirement: Every step is measured
Each step that handles an address or a batch of addresses SHALL record: the step and its version; the writer; when it started; how long it ran; how long it waited before running and on what; how it ended; whether a stored result answered it; model tokens in and out and their cost; the requests it sent, by source; and the rows it wrote. A step that fails SHALL be measured like one that succeeds.

#### Scenario: A read that waited on the page reader
- **WHEN** a lead waits 40 seconds for the page reader and its read then takes 6 seconds
- **THEN** its measurement gives 40 seconds waiting on the page reader, 6 seconds running, one request to the reader, the model's tokens and cost, and the read's outcome

#### Scenario: A step answered from stored work
- **WHEN** triage finds a stored score for a lead at the current version
- **THEN** its measurement says a stored result answered it, with no tokens, no cost and no request

#### Scenario: A step that fails
- **WHEN** a model call is refused
- **THEN** the measurement gives the time it took and the kind of failure

### Requirement: An address can be followed end to end
The measurements of one address, from when it was first seen to when it was published, dropped or left waiting, SHALL be linked, across devices, the store-side consumer and a reader's lookup.

#### Scenario: Scored on a device, read store-side
- **WHEN** a lead is scored in a run on a device and later read by the store-side consumer
- **THEN** one account of that address shows both steps in order, with the time between them

#### Scenario: Asking about one published claim
- **WHEN** the operator asks what a published claim took
- **THEN** the answer gives the time from its article first being seen to its publication, the time spent working, the time spent waiting by cause, and the cost

### Requirement: Nothing about a reader is measured
A measurement SHALL hold the step and the article and SHALL NOT hold a network address, an identifier of a reader, a user agent, or anything a reader's browser sent. A measurement of a reader's lookup SHALL be kept by the article's address only as long as measurements by address are kept, and afterwards only in totals.

#### Scenario: Measurements of a lookup
- **WHEN** a reader's lookup is measured
- **THEN** its measurements name the steps, their times and costs and the article, and nothing else

### Requirement: Totals are kept, detail is kept briefly
Totals by day, step, step version, writer and outcome SHALL be kept in the store. Measurements of single steps SHALL be kept where they were made for a set number of days, with no default, and then removed. A run's measurements SHALL reach the store as totals when the run is pushed.

#### Scenario: A million leads in a month
- **WHEN** a month's backfills process a million leads
- **THEN** the store gains totals for each day, step, version, writer and outcome, and no row for each step of each lead

#### Scenario: Looking into yesterday
- **WHEN** the operator asks which addresses waited longest yesterday
- **THEN** the answer is given from the measurements still kept for that day

### Requirement: Reports
`thenwhat measure` SHALL report, for a range of days: time running, time waiting and cost, by step and by writer; how many leads each step settled; the share of each kind of work answered from a stored result; cost and time for each published claim as a median and a worst case; and the sources waited on longest. It SHALL say plainly when a range has no measurements.

#### Scenario: A week's report
- **WHEN** the operator asks for the last seven days
- **THEN** the report gives each step's share of time and of cost, and the cost of a published claim

#### Scenario: Before anything is measured
- **WHEN** the range holds no measurements
- **THEN** the report says so and gives no figures

### Requirement: A saving is claimed only from measurements
A change to a step made to save time or cost SHALL be recorded with the measured figures before and after, on the same leads where that is possible. The plan a step prints before it spends SHALL use measured cost for a record where a week or more of measurements exist.

#### Scenario: A reshaped triage call
- **WHEN** a new shape of the triage call is adopted
- **THEN** the change records tokens and cost for a headline before and after, measured on the same sample
