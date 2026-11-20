# Spec Delta

## ADDED Requirements

### Requirement: Claims citing a changed trial are refreshed first
The daily run's registry refresh of published claims SHALL take first the claims that the trials load made due because a trial they cite changed. It SHALL refresh no more claims in a run than its limit, and SHALL stay under the run's spend guard as it does today. A claim it does not reach SHALL stay due for the next run. A claim's status SHALL change only through events the existing rule approves.

#### Scenario: A cited trial was terminated overnight
- **WHEN** the trials step stores that a trial cited by a published claim was terminated
- **THEN** the same run's refresh takes that claim before any claim that is only next in turn, its events are approved by the existing rule, and its status is derived again

#### Scenario: More claims due than a run refreshes
- **WHEN** the trials step makes 400 claims due and a run refreshes 150
- **THEN** 150 of them are refreshed, 250 stay due, and the summary says how many are left

#### Scenario: No cited trial changed
- **WHEN** the trials step changes no trial that a claim cites
- **THEN** the refresh takes claims in turn as it did before

#### Scenario: The spend guard stops the run
- **WHEN** the month's spend reaches the run's margin while claims made due by changed trials are still waiting
- **THEN** the refresh stops as it does today, those claims stay due, and the summary says how many

### Requirement: The summary names cited trials that changed
The daily run's summary SHALL give, with the trials step's counts, how many cited trials changed and how many claims are due for their registry refresh because of it. The daily run SHALL still write no export.

#### Scenario: Four cited trials changed
- **WHEN** the trials step changes four trials that six published claims cite
- **THEN** the summary says four cited trials changed and how many of the six claims are still due after the refresh
