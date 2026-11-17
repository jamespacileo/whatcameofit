# Spec Delta

## ADDED Requirements

### Requirement: A registry search leaves a record
Each search of a registry for a claim SHALL leave a record of the source, the term sent, the condition it was narrowed by if any, the time, the number of records the source reported, the number kept, and whether a limit left records out. A term that was not sent SHALL leave a record saying why. The records of a claim's latest search SHALL replace those of the search before.

#### Scenario: A search that found trials
- **WHEN** a claim's intervention is searched and the registry reports 37 records
- **THEN** a record holds the term, the time, 37 reported and 37 kept

#### Scenario: A search that found none
- **WHEN** a term is searched and the registry reports no record
- **THEN** a record holds the term, the time and zero reported

#### Scenario: A limit left records out
- **WHEN** a name is still broad once narrowed by the condition and its records are not taken
- **THEN** a record holds the term, the number reported, zero kept and that a limit left them out

#### Scenario: A term that is not sent
- **WHEN** a name is refused as no search term
- **THEN** a record holds the name and the reason it was not sent

### Requirement: A lookup that failed is not a finished search
A claim's search SHALL be finished only when the lookup of its substance and every search of the registry for its names ran to an answer. When one of them could not be asked or failed, the search SHALL be unfinished, SHALL be reported with the claim and the lookup that failed, and SHALL be due again. A lookup that answered that it knows nothing SHALL count as an answer.

#### Scenario: The registry of substances is down
- **WHEN** the lookup of a claim's substance fails on every attempt
- **THEN** the claim's search is unfinished and due again, and the claim is not decided on it

#### Scenario: The substance is not known
- **WHEN** the registry of substances answers that it has no record for the name
- **THEN** the lookup is finished, and the claim has no substance record

#### Scenario: Papers could not be searched
- **WHEN** the registry searches finished and the literature index failed
- **THEN** the claim's search of registries is finished, and its search for papers is due again by itself

### Requirement: A claim never searched is told apart from one searched
The pipeline SHALL be able to say of any claim whether its registries were searched, when, and with what terms, from the records its searches left. A claim with no such record SHALL be reported as never searched by `thenwhat prepare` and by the audit list, whatever status it holds. The rule that derives a status SHALL be unchanged.

#### Scenario: A claim with no search record
- **WHEN** a claim holds the status given when no trial is found and has no record of a search
- **THEN** it is listed as never searched, and its registry search is due

#### Scenario: A claim searched with no result
- **WHEN** a claim's searches each left a record reporting no trial
- **THEN** it is not listed as never searched
