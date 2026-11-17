# Spec Delta

## MODIFIED Requirements

### Requirement: Registry trial record
A registry trial SHALL be stored once per registry and registry identifier, with its title, official title, acronym, the sponsor's own study identifier and its secondary identifiers with their kinds, conditions, interventions with their types and other names, phases, overall status, start date, primary completion date, completion date, each date's kind as the registry marks it (actual or estimated), the date the registry first posted the record and the date it last changed it, whether the record holds posted results and the date they were first posted, the enrolment count and its kind, the reason the registry gives for a stopped trial, the lead sponsor's class and name, its collaborators' names and classes, the paper index numbers of the papers the record lists with the kind the registry gives each, the links the record gives with their labels, the raw payload as the registry returned it, and the time it was fetched. The name of a lead sponsor the registry classes as an individual SHALL NOT be kept outside the raw payload.

#### Scenario: A trial is loaded
- **WHEN** a trial is loaded from the registry
- **THEN** it is stored with its identifier, the fields above, its raw payload and its fetch time

#### Scenario: A trial is loaded again
- **WHEN** a trial already stored is loaded again
- **THEN** its record is updated in place and no second record is created

#### Scenario: A trial stored before the wider load
- **WHEN** a trial stored with ten fields is loaded again by the wider load
- **THEN** the same record gains the new fields and no second record is created

#### Scenario: A record that lists papers
- **WHEN** a loaded trial's record lists one paper of the kind result and two of the kind background
- **THEN** the three paper numbers are stored with their kinds, and no citation text is

#### Scenario: A sponsor-investigator the registry classes as other
- **WHEN** a loaded trial's lead sponsor is classed "OTHER" and the record's responsible party is a sponsor-investigator
- **THEN** no name is stored for the sponsor, in the column or in the stored record, and of the responsible party only its type is stored

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

### Requirement: A load says which cited trials changed
A load SHALL report, beside how many trials were new and how many already stored, how many of the trials it changed are cited by a claim and how many claims that made due for their registry refresh.

#### Scenario: A day's changes
- **WHEN** a changes-only load stores 900 changed trials, 4 of them cited by 6 published claims, with a change of state, phases, dates or posting of results
- **THEN** the report says 4 cited trials changed and 6 claims are due for their registry refresh

#### Scenario: No cited trial changed
- **WHEN** a load changes only trials that no claim cites
- **THEN** the report says no claim became due

### Requirement: A load starts nothing
A load SHALL store records and mark work due, and SHALL start no step: no model call, no request to the page reader, no news search, no claim, no match or approval, no failure flag, no archive or its undoing, no release from audit and no message to a reader. Work a load makes due SHALL run only when the operator runs it. The one exception is the daily run's existing registry refresh of published claims, which MAY take first the claims a load made due, within its own limit and spend guard.

#### Scenario: A changed trial with a telling name
- **WHEN** a load adds a trial whose name is telling and stored leads would be strongly linked to it
- **THEN** the trial is due for the offline linking, no lead is read, no article is fetched and no usage is recorded

#### Scenario: A trial due for the news search
- **WHEN** a load makes 900 trials due for the news search
- **THEN** no search is sent until the operator runs the step

#### Scenario: A day with no operator
- **WHEN** loads run daily for a week with no command from the operator
- **THEN** no lead was read, no article fetched, no news search sent and no claim created because of them, and no run refreshed more claims than its limit

#### Scenario: A cited trial changes state
- **WHEN** a load stores a new state for a trial a published claim cites
- **THEN** the claim's status is unchanged until its registry refresh has run, and changes then only through events the existing rule approves
