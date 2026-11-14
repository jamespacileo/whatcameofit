# Spec Delta

## ADDED Requirements

### Requirement: Background cards in the download
The data file SHALL hold, for each published claim, each background card the claim page shows whose source's licence allows it to be offered under the file's licence, with its label, link, source, score, reasons and the date its record was read. A card or a fact whose licence does not allow this SHALL be left out, and the file SHALL name each source left out and say why.

#### Scenario: Card from a public-domain source
- **WHEN** a claim's card comes from a source that places no condition on reuse
- **THEN** the card is in the data file with its source named

#### Scenario: Fact from a share-alike source
- **WHEN** a claim's page shows a mechanism from a share-alike source
- **THEN** the data file leaves the mechanism out and names the source and its licence as the reason
