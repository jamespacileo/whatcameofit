# registry-corpus Specification

## Purpose
Holds trial records loaded in bulk from a public registry, independently of any claim, so that steps can work from the registry's trials towards the news that reported them.

## Requirements

### Requirement: Registry trial record
A registry trial SHALL be stored once per registry and registry identifier, with its title, conditions, interventions with their types and other names, phases, overall status, start date, lead sponsor class, the raw payload as the registry returned it, and the time it was fetched.

#### Scenario: A trial is loaded
- **WHEN** a trial is loaded from the registry
- **THEN** it is stored with its identifier, the fields above, its raw payload and its fetch time

#### Scenario: A trial is loaded again
- **WHEN** a trial already stored is loaded again
- **THEN** its record is updated in place and no second record is created

### Requirement: Bulk load
`thenwhat backfill load-trials` SHALL load trials from the registry's list endpoint in pages, not one request per trial, and SHALL accept a condition that limits which trials are loaded.

#### Scenario: Loading phase 3 drug trials
- **WHEN** the operator loads trials limited to phase 3 trials of a drug or biological
- **THEN** every trial the registry returns for that condition is stored, using one request per page of trials

#### Scenario: Interrupted load
- **WHEN** a load stops part way and is started again
- **THEN** it finishes with every matching trial stored once

### Requirement: Loading changes only
A load SHALL be able to fetch only the trials the registry has updated since the previous completed load.

#### Scenario: Second load
- **WHEN** a load completed on one day and the operator loads changes a week later
- **THEN** only trials updated in the registry since the first load are requested

### Requirement: Changed trials become due
A trial whose stored fields change on a load SHALL become due again for the steps that use those fields.

#### Scenario: A trial gains an intervention name
- **WHEN** a load updates a trial's interventions
- **THEN** that trial is due again for the news search

#### Scenario: Nothing a step uses changed
- **WHEN** a load updates only a field no step uses
- **THEN** the trial does not become due for any step

### Requirement: Registry trials are not evidence
A registry trial in the corpus SHALL NOT be an evidence event, SHALL NOT be attached to a claim, and SHALL NOT appear in the export.

#### Scenario: Export after a load
- **WHEN** 43,000 trials are loaded and the export is produced
- **THEN** the export is identical to the one produced before the load

### Requirement: Registry terms
Bulk loads SHALL identify the client with the configured contact address, stay within the registry's allowance, and send no request while the contact address is empty. A load that may not ask the registry now, because the allowance is used up or the registry asked it to wait, SHALL stop with what it stored, say why, and not be recorded as a completed load.

#### Scenario: No contact address
- **WHEN** a load is started with no contact address configured
- **THEN** no request is sent and the command says the contact address is missing

#### Scenario: The allowance runs out part way
- **WHEN** the registry's allowance is used up after the first page of a load
- **THEN** the trials of that page are stored, the command reports them and says it stopped, it exits without an error, and the next changes-only load asks from the same date as this one did

#### Scenario: The registry asks the load to wait
- **WHEN** the registry still answers "too many requests" after the client's retries
- **THEN** the pause is recorded for the registry with the wait it stated, the load stops with what it stored and exits without an error, and a load started before the pause ends sends no request

### Requirement: A stored trial carries the registry's activity and results fields
A registry trial SHALL be stored with, besides its listing fields, what the registry states of its activity and results: the date its record was last updated, its primary completion date and completion date with whether each is actual or anticipated, the date results were first posted, whether results are posted, its acronym, the other names of each intervention, and the references and links the registry lists for it. Each SHALL be stored as the registry gives it; a field the registry leaves empty SHALL be stored as empty and never inferred.

#### Scenario: A trial with posted results
- **WHEN** the registry's record of a trial has results posted on a date
- **THEN** the stored trial carries that date and that results are posted

#### Scenario: A field the registry leaves empty
- **WHEN** the registry gives no completion date for a trial
- **THEN** the stored trial has none, and no date is derived from its state or its start date

### Requirement: Sets of trials named by activity and results
Two further sets SHALL be selectable from the stored trials, by rule and without asking any source. `active-since-2025`: trials in phase 2 or 3 whose state is recruiting, not yet recruiting, enrolling by invitation, or active and no longer recruiting, and whose record the registry last updated on or after 1 January 2025. `completed-with-results-since-2025`: trials whose state is completed, whose completion date is actual and on or after 1 January 2025, and whose results are posted. A set SHALL say only which trials are in it. Neither set's name, nor anything shown of a trial in it, SHALL word an outcome: a trial in the second set is completed with results posted, and nothing more is said of how it turned out.

#### Scenario: Counting the sets
- **WHEN** every trial has been loaded with the wider record
- **THEN** the number of trials in each set can be given from the stored trials alone, with the day they were loaded

#### Scenario: A completed trial without results
- **WHEN** a trial completed in 2026 has no results posted
- **THEN** it is in neither set

### Requirement: The wider record is loaded for every stored trial
After the wider record is introduced, every stored trial SHALL be loaded again in full, within the registry's allowance, so that no stored trial lacks the new fields because it was loaded before them. A trial whose listing fields did not change SHALL NOT become due for any step because of this reload.

#### Scenario: The reload
- **WHEN** all trials are loaded again with the wider record
- **THEN** each has the new fields as the registry gives them, and no step that searches or reads for a trial has more records due than before
