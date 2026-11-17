# Spec Delta

## MODIFIED Requirements

### Requirement: Preparing many claims
An operator SHALL be able to have unread articles read, registries searched and approved matches fetched for many claims with one command, several claims at a time. A step that fails SHALL be reported with its claim, and the claim's other steps SHALL still run. The command SHALL approve nothing and SHALL say how long each step took. Each part of a claim's preparation SHALL be a step of the work ledger whose record is the claim: reading its unread articles, looking up its substance, searching the registries, searching for papers, fetching its approved records, reading its trial records, and proposing its terms. A part that finished for a claim's current input SHALL NOT be done again by a later run. The command SHALL finish by saying, for each step, how many claims were done, put off, need a fix, failed and remain due.

#### Scenario: Article that cannot be read
- **WHEN** one of a claim's articles cannot be read
- **THEN** the failure is reported and the claim is still searched

#### Scenario: A run stopped half way through a claim
- **WHEN** a run is stopped after a claim's registries were searched and before its records were fetched, and is started again
- **THEN** the registries are not searched again, and the fetch runs

#### Scenario: A source is paused
- **WHEN** a registry cannot be asked during a run
- **THEN** the claims waiting for it stay due for that step, the steps that need other sources still run, and the report says how many wait and for what

#### Scenario: A publisher is temporarily unavailable
- **WHEN** the page reader reports a temporary site response (including 202, 429 or 503) for an unread source article
- **THEN** the article step is put off for the configured site wait and the next due run tries it again

#### Scenario: The ceiling is reached with free work still due
- **WHEN** the month's model spend has reached its ceiling
- **THEN** source-only work and a decision by rule can still finish, and each step requiring a model stops when it needs the paid call

#### Scenario: The model refuses its key during trial readings
- **WHEN** the model cannot be asked while reading trials
- **THEN** the step stops with its current and remaining claims due, keeps completed readings, and reports the provider's cause

#### Scenario: A source pauses after a paid part
- **WHEN** a claim's completed classifications are followed by a failed drug lookup which pauses its source
- **THEN** the step stops with the claim due and a later run reuses its completed classifications

#### Scenario: MeSH cannot resolve an entry term
- **WHEN** the vocabulary returns an entry term without the record that identifies its descriptor
- **THEN** the terms step reports the unresolved name and schedules another attempt

## ADDED Requirements

### Requirement: What a decision waits for
A claim a read drafted SHALL be decided by the rule for drafts only when its substance lookup, its registry search and the fetch of its approved records have finished for its current input. It SHALL NOT wait for its papers, its trial readings or its terms. Those SHALL stay due until they finish, for a claim that is decided as for one that is not.

#### Scenario: Terms failed and the claim is decided
- **WHEN** a claim's search and fetch finished and its terms could not be proposed
- **THEN** the claim is decided, and it is due for its terms on the next run

#### Scenario: The substance lookup did not finish
- **WHEN** a claim's registry search finished and its substance lookup failed
- **THEN** the claim is not decided, and stays pending until the lookup finishes

#### Scenario: Readings failed
- **WHEN** a claim's search and fetch finished and reading one of its trial records failed
- **THEN** the claim is decided, and that reading is due on the next run

#### Scenario: The DOI registry cannot answer about an article's paper
- **WHEN** the claim's trial search finished but the DOI registry cannot identify a paper entity
- **THEN** the trial search keeps its receipts, the paper lookup stays due, and the decision can proceed once its required steps finish

### Requirement: Unfinished parts of a published claim are completed
A run that prepares claims SHALL take, beside the claims awaiting review, every approved claim that is not archived and is due for a part of its preparation, so that a part left unfinished when the claim was decided is finished later without being asked for by name.

#### Scenario: A published claim with no terms
- **WHEN** an approved claim has no terms because proposing them failed when it was prepared
- **THEN** the next run that prepares claims proposes them

#### Scenario: A trial approved after the claim was published
- **WHEN** a trial match of a published claim is approved and its record has not been read
- **THEN** the next run reads it

#### Scenario: A paper approved after the claim was searched
- **WHEN** a related paper is approved after the last paper search
- **THEN** the next prepare looks up its stated trial numbers and considers it for origin paper

#### Scenario: The paper index is enabled after a page named a DOI
- **WHEN** the index was off when a claim was prepared and its article named a DOI
- **THEN** the unfinished lookup is reported and enabling the index makes the claim due for those identifiers
