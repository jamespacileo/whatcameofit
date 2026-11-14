# Spec Delta

## ADDED Requirements

### Requirement: Organisations in the download
The data file SHALL hold, for each published claim, the organisations the claim page lists, each with its name, roles and, when identified, its kind, country, website, registry record link, match score and the date its record was read; and, for each article, the organisation it is marked as published by. It SHALL NOT hold a person's name or a registry record itself.

#### Scenario: Claim with an identified sponsor
- **WHEN** a reader downloads the data file
- **THEN** the sponsor is in it with its registry link, kind, country, score and the trials it sponsors

#### Scenario: Person sponsor
- **WHEN** a claim's only sponsor is a person
- **THEN** the data file lists no organisation for that sponsor and names no one
