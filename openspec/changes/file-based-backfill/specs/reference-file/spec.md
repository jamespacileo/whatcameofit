# Spec Delta

## Purpose

Gives a device, as one file, what the truth store already tracks and has already paid for, so a run screens against the same claims and addresses and repeats no scoring or reading.

## ADDED Requirements

### Requirement: Reference file
`thenwhat backfill reference pull` SHALL fetch from the truth store one file holding: each claim's slug, intervention, indication and state; the address keys of source articles by claim; the registry trials without their payloads; entity names; for each link lead the store holds, its address key, its triage version and score, and its read outcome where it has one; the work slices; and the month's model usage by writer. The file SHALL state an identifier and the time it was made.

#### Scenario: An article that is already a source article
- **WHEN** a run's lead has the address key of a source article in the reference file
- **THEN** screening gives it the outcome already tracked, with the claim

#### Scenario: A lead the store has read
- **WHEN** a run's lead has the address key of a lead the reference file gives a read outcome for
- **THEN** screening gives it the outcome already read elsewhere, and it is never scored or read

### Requirement: What a reference file never holds
A reference file SHALL hold no raw payload, no decision log, no title of a lead, no subscriber data and no credential.

#### Scenario: Reading its contents
- **WHEN** a reference file is pulled
- **THEN** it holds only the records named above

### Requirement: A run names its reference file and warns when it is old
A run SHALL record the reference file it was started with. `thenwhat backfill runs start` SHALL pull a new one unless told to use the one present. A stage SHALL refuse to run in a run with no reference file, and SHALL warn when the file is older than seven days.

#### Scenario: Starting with no network
- **WHEN** a run is started with no connection and told to use the reference file present
- **THEN** it starts, and its record says which file it used

#### Scenario: No reference file at all
- **WHEN** screening is run where no reference file has ever been pulled
- **THEN** it refuses and names the pull command

### Requirement: A stale reference file cannot make a wrong record
Nothing in a reference file SHALL decide what the truth store holds. A lead the reference file did not know to be tracked SHALL be resolved by the merge against the store as it is when the run is pushed.

#### Scenario: A claim was added after the pull
- **WHEN** a run drafts a claim that another writer added to the store after the reference file was made
- **THEN** the push's report counts the claim as matched, and the run's article is added to the existing claim
