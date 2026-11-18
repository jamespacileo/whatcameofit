# Spec Delta

## MODIFIED Requirements

### Requirement: Published claims as a download
The site SHALL offer, at a stable address, a file holding every published claim with its status, the events that produced the status, its matches with their scores, its source articles by outlet, title, date and address, its promises, whether a person checked it, and the date the registries were last checked. The file SHALL hold only what the claim pages already show. It SHALL NOT hold article text, any claim that is unpublished or archived, outlet icon images, or raw registry payloads.

#### Scenario: Reader downloads the data
- **WHEN** a reader requests the data file
- **THEN** they receive every published claim with its status, explaining events, scored matches, articles, promises and the last-checked date

#### Scenario: Unpublished claim
- **WHEN** a claim is pending or rejected
- **THEN** it does not appear in the data file

#### Scenario: Archived claim
- **WHEN** a claim has been archived
- **THEN** it does not appear in the data file

#### Scenario: Article text
- **WHEN** the data file is inspected
- **THEN** it holds each article's outlet, title, date and address and no text from the article
