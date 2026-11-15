# Spec Delta

## ADDED Requirements

### Requirement: Only research organisations are recorded as institutions or companies
Extraction SHALL record an institution or a company only for a university, hospital, research institute, company, funder or public body that the article names. It SHALL NOT record a journal, a news outlet, a bank or an investment analyst as one. Entities already recorded are not changed by this requirement; the organisation registry's approval rule keeps them from being identified.

#### Scenario: Article names the journal and the newspaper that reported first
- **WHEN** an article says a study was published in a journal and was first reported by a newspaper
- **THEN** neither the journal nor the newspaper is recorded as an institution or a company
