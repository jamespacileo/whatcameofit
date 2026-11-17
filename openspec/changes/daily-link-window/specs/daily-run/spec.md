# Spec Delta

## ADDED Requirements

### Requirement: Links fetched for a rolling window
Each daily run SHALL ask the Hacker News source only for the stories with a link posted since midnight UTC a set number of days ago (`DAILY_RUN_FETCH_DAYS`, default 3, from 1 to 28), SHALL merge them into the file of each month the window touches without dropping any row already in it, and SHALL then load each of those months' files, oldest first. A story fetched again SHALL replace its older copy in the file. A setting outside 1 to 28 SHALL stop the run before its first step.

#### Scenario: A window inside one month
- **WHEN** the run starts on 17 November with the default window
- **THEN** it sends one request for the stories since 14 November, merges them into November's file, and loads November's file

#### Scenario: A window that reaches into last month
- **WHEN** the run starts on 2 November with the default window
- **THEN** it sends one request for the stories since 30 October, merges each into its own month's file, keeping the rows October's file already held, and loads October's file, then November's

#### Scenario: A window too wide
- **WHEN** `DAILY_RUN_FETCH_DAYS` is 40
- **THEN** the run stops before its first step and says the setting must be 1 to 28
