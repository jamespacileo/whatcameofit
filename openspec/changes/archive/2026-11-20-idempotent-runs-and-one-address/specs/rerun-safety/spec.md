# rerun-safety

## Purpose

Says what a second run of each pipeline step does when it is given the same input, or input that overlaps what an earlier run was given.

## ADDED Requirements

### Requirement: A load can be repeated
Loading a file that was loaded before, wholly or in part, SHALL store nothing a second time, and SHALL report what it found already stored. A load SHALL send no request for what is already stored when it reads from a file.

#### Scenario: The same file loaded twice
- **WHEN** a file of shared links is loaded twice
- **THEN** the second load adds no lead and no share and counts each post as already stored

#### Scenario: Two files that overlap
- **WHEN** two files hold some of the same posts
- **THEN** each post is stored once whichever file is loaded first

### Requirement: The order of loads does not change what is stored
A link lead's title, first share time and address SHALL be those of its earliest share, whichever file was loaded first.

#### Scenario: The older file loaded second
- **WHEN** a file with an earlier share of an article is loaded after a file with a later one
- **THEN** the lead is as it would be had the files been loaded the other way round

### Requirement: A step is not paid for twice at one version
A step that calls a model or spends a source's allowance SHALL NOT do so again for a record it finished at the step's current version while what it reads of the record is unchanged. A second run SHALL skip such records.

#### Scenario: Triage run twice
- **WHEN** triage is run again with no new lead and the same step version
- **THEN** no model call is made

#### Scenario: One article, one lead
- **WHEN** an article was shared under two forms of its address
- **THEN** it is scored once and read once

### Requirement: What a failed attempt paid for is kept
When a record's attempt fails after a page was fetched or a model answered, what was paid for SHALL be kept and used by the next attempt at the same step version.

#### Scenario: A read fails after the extraction
- **WHEN** a read fails at a later decision and is attempted again
- **THEN** the page and the extraction of the first attempt are used and are not asked for again

#### Scenario: A scoring call fails part way
- **WHEN** a call that scores candidates fails after earlier calls of the same run scored some
- **THEN** the scored candidates keep their scores and only the others are asked for again

### Requirement: A request that could not be served is not repeated without limit
When the page reader answers that a site cannot be asked now, the pipeline SHALL record it and SHALL NOT ask for that lead again before the time the reader gave, in this run or a later one.

#### Scenario: Not now, then a second run
- **WHEN** the reader said a site could not be asked for an hour and a second run starts ten minutes later
- **THEN** no request is sent for that site's leads

### Requirement: The export is the same for the same data
Two exports of an unchanged database on one day SHALL differ only in the time they were made.

#### Scenario: Exported twice
- **WHEN** the export is written twice with no change between
- **THEN** the files are the same apart from `generated_at`
