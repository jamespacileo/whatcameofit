# Spec Delta

## MODIFIED Requirements

### Requirement: Registry trial record
A registry trial SHALL be stored once per registry and registry identifier, with its title, conditions, interventions with their types and other names, phases, overall status, start date, primary completion date, completion date, each date's kind as the registry marks it (actual or estimated), the date the registry first posted the record and the date it last changed it, whether the record holds posted results and the date they were first posted, the enrolment count and its kind, the reason the registry gives for a stopped trial, the lead sponsor's class and name, the raw payload as the registry returned it, and the time it was fetched. The name of a lead sponsor the registry classes as an individual SHALL NOT be kept outside the raw payload.

#### Scenario: A trial is loaded
- **WHEN** a trial is loaded from the registry
- **THEN** it is stored with its identifier, the fields above, its raw payload and its fetch time

#### Scenario: A trial is loaded again
- **WHEN** a trial already stored is loaded again
- **THEN** its record is updated in place and no second record is created

#### Scenario: A trial stored before the wider load
- **WHEN** a trial stored with ten fields is loaded again by the wider load
- **THEN** the same record gains the new fields and no second record is created

#### Scenario: A trial sponsored by a person
- **WHEN** a loaded trial's lead sponsor is classed as an individual
- **THEN** the sponsor's class is stored and no sponsor name is

### Requirement: Changed trials become due
A trial whose stored fields change on a load SHALL become due again for the steps that use those fields, and for no other step. A trial that a claim cites and whose state, phases, dates or posting of results changed SHALL make that claim due for its registry refresh. A trial that is new, or whose names or conditions changed, SHALL be due for the offline linking. A trial in a named set whose record newly says results are posted SHALL be due for the full-record step.

#### Scenario: A trial gains an intervention name
- **WHEN** a load updates a trial's interventions
- **THEN** that trial is due again for the news search and for the offline linking

#### Scenario: Nothing a step uses changed
- **WHEN** a load updates only a field no step uses
- **THEN** the trial does not become due for any step

#### Scenario: A cited trial is completed
- **WHEN** a load stores that a trial a published claim cites is now completed
- **THEN** that claim is due for its registry refresh

#### Scenario: An uncited trial is completed
- **WHEN** a load stores that a trial no claim cites is now completed
- **THEN** no claim becomes due, and the trial's page states the new state from the stored record

### Requirement: Registry trials are not evidence
A registry trial in the corpus SHALL NOT be an evidence event and SHALL NOT be attached to a claim by a load. It SHALL appear in the export of claims only where a claim's approved events cite it. It MAY be shown on its own trial page and in the trial listing, as registry facts only.

#### Scenario: Export after a load
- **WHEN** 467,000 trials are loaded and the export of claims is produced
- **THEN** the claims in the export are identical to those produced before the load

#### Scenario: A stored trial in the listing
- **WHEN** the trial listing is produced for a named set
- **THEN** it holds each trial of the set with registry facts and no claim, status or score

## ADDED Requirements

### Requirement: Daily change load
A load of changes SHALL be runnable each day with no input from a person. It SHALL ask the registry only for interventional studies changed since the last completed load, in pages, within the registry's allowance, and SHALL store each changed or new trial once. It SHALL report how many trials changed, how many were new, how many cited trials changed, and which claims became due.

#### Scenario: A day's changes
- **WHEN** the registry has changed 900 interventional studies since the last completed load
- **THEN** one page is requested, 900 records are updated or added, and the report gives the counts

#### Scenario: A load that stops part way
- **WHEN** a daily load stops after its first page
- **THEN** the next load asks again from the last load that completed, and every changed trial is stored once

#### Scenario: The registry does not answer
- **WHEN** the registry cannot be reached
- **THEN** nothing is changed, the last completed load stands, and the report says the load did not run

### Requirement: What a load may start without a person
A load SHALL start, without a person, only work that sends no request or asks only the registry, and that calls no model: the offline linking, the registry refresh of a claim that cites a changed trial, and the full-record step for a trial in a named set. Refreshes started this way SHALL be capped at a configured number a day, and what is left SHALL stay due.

#### Scenario: A cited trial changes state
- **WHEN** a daily load stores a new state for a trial a claim cites
- **THEN** the claim's registry refresh runs, its events are approved by the existing rule, and its status is derived again, with no model call

#### Scenario: More refreshes than the cap
- **WHEN** a load makes 5,000 claims due and the cap is 500
- **THEN** 500 are refreshed, 4,500 stay due, and the report says so

### Requirement: What a load never starts
A load, and anything a load makes due, SHALL NOT by itself start: a model call of any kind; a request to the page reader; a news search; the creation of a claim; a match or its approval; a failure flag; an archive or its undoing; a release from audit; or a message to a reader. A claim's status SHALL change after a load only through the approved registry events of a trial it already cites. The news search for a changed trial SHALL become due and SHALL run only when the operator runs it.

#### Scenario: A changed trial with a telling name
- **WHEN** a daily load adds a trial whose name is telling and stored leads are strongly linked to it
- **THEN** the links are recorded, no lead is read, no article is fetched and no usage is recorded

#### Scenario: A trial due for the news search
- **WHEN** a daily load makes 900 trials due for the news search
- **THEN** no search is sent until the operator runs the step

#### Scenario: A day with no operator
- **WHEN** daily loads run for a week with no command from the operator
- **THEN** the month's model spend is unchanged by them
