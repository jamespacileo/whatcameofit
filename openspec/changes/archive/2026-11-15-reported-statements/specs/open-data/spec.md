# Spec Delta

## ADDED Requirements

### Requirement: Reported statements in the download
The data file SHALL hold, for each published claim, the approved reported statements the claim page shows, each with its text, kind, firmness, speaker role, basis, confidence and the address of its article. It SHALL NOT hold a pending or rejected statement, nor any text from an article.

#### Scenario: Claim with approved statements
- **WHEN** a reader downloads the data file
- **THEN** the claim's approved statements are in it, each in the site's own words with its confidence and its article's address

#### Scenario: Pending statement
- **WHEN** a statement is still pending
- **THEN** it does not appear in the data file
