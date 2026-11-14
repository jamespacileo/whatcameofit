# Spec Delta

## ADDED Requirements

### Requirement: Trial facts in the download
The data file SHALL hold, for each published claim, the trials the claim page lists with the facts the page shows for each and the date each trial's registry record was read. It SHALL hold each event's confidence. It SHALL NOT hold a registry record itself, nor any fact the claim pages do not show.

#### Scenario: Claim with a trial that has posted results
- **WHEN** a reader downloads the data file
- **THEN** the claim's trial is in it with its participants, design, planned primary outcomes, posted results and the date its record was read

#### Scenario: Registry record
- **WHEN** the data file is inspected
- **THEN** it holds no registry record as the registry returned it
