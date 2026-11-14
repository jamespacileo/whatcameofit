# Spec Delta

## ADDED Requirements

### Requirement: Papers in the download
The data file SHALL hold, for each published claim, the papers the claim page lists, each with its identifier, link, roles, the facts the page shows for it and the date its index record was read. It SHALL NOT hold an abstract, an author, an affiliation or an index record itself.

#### Scenario: Claim with a results paper
- **WHEN** a reader downloads the data file
- **THEN** the claim's results paper is in it with its title, journal, year, kinds, the trial it reports and the date its record was read

#### Scenario: Authors
- **WHEN** the data file is inspected
- **THEN** it names no author of any paper
