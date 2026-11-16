# Spec Delta

## Purpose

Defines a backfill from bulk files as a run that lives in a folder of files on any device, with no database there: what a run records, how it is stopped and started again, how it avoids paying twice, and how its results reach the truth store.

## ADDED Requirements

### Requirement: A run is a folder and needs no database
`thenwhat backfill run start` SHALL create a run folder for one platform and the bulk files named, and every stage of the run SHALL read and write files in that folder only. No stage SHALL need a database on the device. The run SHALL record its identifier, the device's name, the code's commit, the version of each step, the outlet list's version, the triage thresholds, the reference file it uses and the input files with their sizes.

#### Scenario: A device with nothing but the repository
- **WHEN** a run is started on a device that has no database server
- **THEN** the load, screening and triage stages complete

#### Scenario: An input file changed
- **WHEN** a stage runs and an input file's size differs from the size the run recorded
- **THEN** the stage stops and names the file

### Requirement: Stages run in order and say what they did
A run's stages SHALL be load, screen, triage, read and prepare. The prepare stage SHALL only write the run's results in the form the merge takes; it SHALL NOT search a registry or approve a claim, a match or an event, which the truth store's side does after the push. A stage SHALL refuse to run before the stage it depends on has completed. Each stage SHALL report how many rows or leads it took, how many went on and how many were left out for each reason, and SHALL fail when those do not sum.

#### Scenario: Triage before screening
- **WHEN** triage is asked to run in a folder where screening has not completed
- **THEN** it refuses and names the stage to run first

#### Scenario: Counts that do not add up
- **WHEN** a stage's counts of rows on and rows left out do not sum to the rows it took
- **THEN** the stage exits with an error that names the figures

### Requirement: A stopped run is started again and pays for nothing twice
A result that cost a model call or a fetch SHALL be on disk before the next call is made. A stage started again SHALL leave out every lead the run's files already hold a result for. A file SHALL be whole or absent: a stage SHALL never leave a partly written file under its final name.

#### Scenario: Triage stopped part way
- **WHEN** triage is stopped after scoring 400 of 1,000 leads and started again
- **THEN** it scores the other 600, and usage shows 1,000 leads paid for in all, give or take the one batch in flight

#### Scenario: A read stopped part way
- **WHEN** reading is stopped while one article is being read and started again
- **THEN** every read that had finished is kept and only the one in flight is read again

### Requirement: What the store already has is not paid for again
Before triage, a run SHALL leave out every lead the reference file gives a score for at the current triage version, and SHALL take that score as the lead's. Before a read, it SHALL leave out every lead the reference file gives a read outcome for. It SHALL count both.

#### Scenario: Another device scored the month
- **WHEN** a run's leads were all scored by another device's pushed run at the same triage version
- **THEN** triage makes no model call and reports them as scored elsewhere

#### Scenario: Triage was reworded since
- **WHEN** the reference file's scores are at a lower triage version than the run's
- **THEN** the leads are scored again

### Requirement: A failed item is kept with its error
A lead whose model call or read fails SHALL be written as a result with the kind of error and how many times it was tried. A stage SHALL try it again when started again, up to a set number of times, and SHALL then leave it and count it.

#### Scenario: An outlet refuses the reader
- **WHEN** an article cannot be read on three attempts
- **THEN** the lead's outcome is unreadable, it is not tried a fourth time, and the stage's report counts it

### Requirement: A run plans before it spends
`thenwhat backfill run plan` SHALL print, for the triage and read stages, how many leads are due, the estimated cost, what the device has spent this month, and what is left under the device's ceiling. A stage that spends SHALL refuse to start while prices or the ceiling are not configured, and SHALL stop before a batch that would pass the ceiling, leaving the rest due.

#### Scenario: The ceiling is reached part way
- **WHEN** triage reaches the device's ceiling after 300 leads
- **THEN** it stops, the 300 are kept, and starting it again in the same month scores nothing

#### Scenario: No price configured
- **WHEN** triage is started with no price set for the model
- **THEN** it refuses and names the setting

### Requirement: What a run's files never hold
A run's files SHALL hold no text of an article, no text of a post, no author of a post, and no post id or address. A row that fails to parse SHALL be recorded by file, position and kind of error only.

#### Scenario: After a batch of reads
- **WHEN** a run has read 200 articles
- **THEN** its files hold each article's address, outlet, title and date and no text of any article

### Requirement: Topic leads first
Where leads are due, a stage SHALL take first those whose title names a topic word, and the read stage SHALL take a topic lead that triage held as well as those it passed. A lead triage rejected SHALL never be read.

#### Scenario: A held topic lead
- **WHEN** a lead names a topic word and its score is between the thresholds
- **THEN** it is read, before leads that name no topic

### Requirement: Push
`thenwhat backfill push` SHALL hand a run's results and usage to the truth store as one or more store runs of no more than the size the store sets, each holding the records another of its records refers to or following the store run that does. For each it SHALL register the store run, hand over its records with their counts and checksums, ask for the merge, and print the merge's report. A push that stopped after some store runs were merged SHALL be finished by pushing again, and SHALL add nothing twice. It SHALL hand over, for a lead that was scored and not read, its address key, shares, screening outcome and score. It SHALL hand over nothing for a link on an unlisted outlet. `--report-only` SHALL print the report and change nothing in the store.

#### Scenario: A run of 200 reads
- **WHEN** a run that read 200 leads and drafted or joined 60 claims is pushed
- **THEN** the report gives the claims, articles and events added, matched and in conflict, and the claims held for audit

#### Scenario: A push stopped part way
- **WHEN** a push of three store runs stops after the first is merged, and the run is pushed again
- **THEN** the first is answered as merged before, the other two are merged, and the store holds each record once

#### Scenario: Pushing twice
- **WHEN** a pushed run is pushed again
- **THEN** the store answers that it was merged before, with the time, and nothing changes

#### Scenario: Report only
- **WHEN** a run is pushed with `--report-only`
- **THEN** the report is printed and the store holds nothing new

#### Scenario: No ingest address configured
- **WHEN** `INGEST_URL` or `INGEST_TOKEN` is empty
- **THEN** push refuses and names the setting

### Requirement: A pushed run can be deleted
After a push the run SHALL be marked pushed, and deleting its folder SHALL lose nothing the truth store needs.

#### Scenario: Cleaning up
- **WHEN** a pushed run's folder is deleted and a new run is started over the same bulk files
- **THEN** the new run scores and reads nothing the first run pushed
