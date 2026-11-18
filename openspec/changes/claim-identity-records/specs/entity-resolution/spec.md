# Spec Delta

## MODIFIED Requirements

### Requirement: Entities and synonyms
Each claim SHALL have entities of type intervention, paper, person, institution or company. An entity SHALL have a name and MAY have any number of synonyms, which an operator can add at any time. A claim's intervention entity SHALL point to the shared intervention record, and its synonyms, development codes and search phrases SHALL be those of that record, so that a synonym added for one claim is used for every claim of the same intervention.

#### Scenario: Compound renamed
- **WHEN** an operator adds a company code name as a synonym of an intervention
- **THEN** later registry searches for that intervention also use the code name

#### Scenario: A synonym added through one of two claims
- **WHEN** an intervention record is shared by two claims and an operator adds a synonym through one of them
- **THEN** both claims' next registry searches use the synonym, and both are marked due for a search
