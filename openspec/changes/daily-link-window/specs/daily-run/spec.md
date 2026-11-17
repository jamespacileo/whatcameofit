# Spec Delta

## ADDED Requirements

### Requirement: Links fetched for a rolling window
Each daily run SHALL ask the Hacker News source only for the stories with a link posted since a day before the end of the last window fetched in full, which it SHALL record once every month file is written, or, with no record, since midnight UTC a set number of days ago (`DAILY_RUN_FETCH_DAYS`, default 3, from 1 to 28). One run SHALL cover at most 20 days; a longer gap SHALL be caught up from its oldest day over the following runs, and the summary SHALL say the fetch is still behind until it has. The run SHALL merge the stories into the file of each month the window touches without dropping any row already in it, and SHALL then load each month's file the fetch wrote, oldest first. A story fetched again SHALL replace its older copy in the file. A window fetched by hand that starts after the record SHALL NOT move the record. A setting outside 1 to 28 SHALL stop the run before its first step. The month form, asked to merge, SHALL fetch a month that already has a file again and merge it in.

#### Scenario: A night after a night
- **WHEN** the last window ended at 04:31 on 16 November and the run starts on 17 November
- **THEN** it sends one request for the stories since 15 November, merges them into November's file, records the new end, and loads November's file

#### Scenario: No record yet
- **WHEN** there is no record of a fetch and the run starts on 2 November with the default setting
- **THEN** it asks for the stories since 30 October, merges each into its own month's file, keeping the rows October's file already held, and loads October's file, then November's

#### Scenario: Missed nights
- **WHEN** the last window ended on 1 October and the run starts on 17 November
- **THEN** it asks for 30 September to 20 October only, loads September's and October's files, records 20 October, and the summary says the fetch is still behind; the next runs go on from there until the record reaches the day of the run

#### Scenario: A past month filled by hand
- **WHEN** the operator runs the month form for October with `--merge` and October's file exists
- **THEN** October is asked for again and merged in, and no row the file held is dropped

#### Scenario: A window too wide
- **WHEN** `DAILY_RUN_FETCH_DAYS` is 40
- **THEN** the run stops before its first step and says the setting must be 1 to 28
