# Spec Delta

## MODIFIED Requirements

### Requirement: Vertical
Each claim SHALL belong to exactly one vertical from a configured set of verticals. Each vertical belongs to one group, as defined by the health-areas capability.

#### Scenario: Unknown vertical
- **WHEN** an operator creates a claim with a vertical that is not in the configured set
- **THEN** the claim is not created and the valid verticals are listed

#### Scenario: Retired vertical
- **WHEN** an operator creates a claim with the retired vertical `pain`
- **THEN** the claim is not created and the valid verticals are listed

## ADDED Requirements

### Requirement: Approach on entry
An operator SHALL be able to give a claim's approach when entering it one at a time or in a CSV file, and to change it later. A CSV row with an unknown approach SHALL fail the whole import.

#### Scenario: CSV with an approach column
- **WHEN** an operator imports a CSV whose rows give the approaches drug and gene therapy
- **THEN** each claim is stored with its approach

#### Scenario: CSV with an unknown approach
- **WHEN** one row of a CSV import gives an approach that is not in the configured set
- **THEN** no claim from the file is created and the row and the valid approaches are named
