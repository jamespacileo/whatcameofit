# daily-run

## Purpose

The once-a-day job on the operator's machine that brings in work and stops at the audit. Only what the change `daily-trial-refresh` touches is specified here.

## ADDED Requirements

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
