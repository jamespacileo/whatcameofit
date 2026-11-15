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
Bulk loads SHALL identify the client with the configured contact address, stay within the registry's allowance, and send no request while the contact address is empty.

#### Scenario: No contact address
- **WHEN** a load is started with no contact address configured
- **THEN** no request is sent and the command says the contact address is missing
