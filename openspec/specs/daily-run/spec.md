# daily-run Specification

## Purpose
The once-a-day job on the operator's machine that brings in work (new links, registry changes and refreshes) and stops at the audit.

## Requirements

### Requirement: Links fetched for a rolling window
Each daily run SHALL fetch linked Hacker News stories since one day before the end of its last complete fetch, advancing its record after writing every month file. With no fetch record it SHALL start at midnight UTC `DAILY_RUN_FETCH_DAYS` days ago (default 3, range 1 to 28). It SHALL reject an invalid setting before its first step. Catch-up SHALL proceed oldest first in windows of at most 20 days and report when it is still behind.

#### Scenario: A night after a night
- **WHEN** the last window ended at 04:31 on 16 November and the run starts on 17 November
- **THEN** it sends one request for the stories since 15 November, merges them into November's file, records the new end, and loads November's file

#### Scenario: No record yet
- **WHEN** there is no record of a fetch and the run starts on 2 November with the default setting
- **THEN** it asks for the stories since 30 October, merges each into its own month's file, keeping the rows October's file already held, and loads October's file, then November's

#### Scenario: Missed nights
- **WHEN** the last window ended on 1 October and the run starts on 17 November
- **THEN** it asks for 30 September to 20 October only, loads September's and October's files, records 20 October, and the summary says the fetch is still behind; the next runs go on from there until the record reaches the day of the run

#### Scenario: A window too wide
- **WHEN** `DAILY_RUN_FETCH_DAYS` is 40
- **THEN** the run stops before its first step and says the setting must be 1 to 28

### Requirement: Monthly files are merged and imported
The fetch SHALL merge stories into the file for each month touched, replacing any older copy of the same story and preserving all other rows. A manual window starting after the fetch record SHALL leave the record in place. The month form with `--merge` SHALL fetch and merge an existing month. The daily run SHALL persist the months it owes before advancing the fetch record, import each month once in date order, and clear each pending mark only after that import succeeds.

#### Scenario: A fetched month still needs to be loaded
- **WHEN** an import fails or the job stops between fetching a month and importing it
- **THEN** that month remains pending across restarts, including after the fetch window advances
- **AND** the next run imports each pending or newly fetched month once, oldest first, and clears its pending mark only after its import succeeds
- **AND** a dry run includes pending months in its plan and preserves their marks

#### Scenario: A past month filled by hand
- **WHEN** the operator runs the month form for October with `--merge` and October's file exists
- **THEN** October is asked for again and merged in, and no row the file held is dropped

### Requirement: Stored trials kept current
Each daily run SHALL load the trials the registry updated since the last completed load of every interventional study, before reading the registries for published claims, and SHALL report how many were new and how many already stored.

#### Scenario: A day's changes
- **WHEN** the registry updated trials since the last completed load
- **THEN** the run asks only for those, stores each in place with its payload and fetch time, and the summary gives the number new and already stored

#### Scenario: The allowance is used up
- **WHEN** the registry's allowance runs out during the load
- **THEN** the load stops, the summary says so, the step is not listed as failed, and the steps after it run

### Requirement: Nothing started over changed trials
The daily run SHALL NOT start a step over the trials it loads.

#### Scenario: Trials due for the news search
- **WHEN** the load adds trials or changes a trial's searched name or indication
- **THEN** those trials are due for `news_search`, and the run starts no `news_search`

### Requirement: Database address
The daily run SHALL reach the database at an address given to it for the host, and SHALL NOT start when none is set. The address SHALL NOT appear in its log or summary; the summary SHALL name the setting it came from. The property list that carries it SHALL be installed readable by its owner alone.

#### Scenario: No database address
- **WHEN** neither `DATABASE_URL` nor `DAILY_RUN_DATABASE_URL` is set in the environment or the settings file
- **THEN** no step starts and the summary says which setting to add

#### Scenario: The property list carries it
- **WHEN** the property list is written with `DAILY_RUN_DATABASE_URL` set
- **THEN** it gives the job `DATABASE_URL` with that address, and says to install it mode 600

#### Scenario: Where the address came from
- **WHEN** a run ends
- **THEN** its summary names the setting the database address came from, and not the address
