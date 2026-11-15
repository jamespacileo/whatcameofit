# open-data Specification

## Purpose
The published claims as a file anyone can download, cite and reuse, under a stated licence, so that the site's evidence can be checked and built on without scraping it.

## Requirements

### Requirement: Published claims as a download
The site SHALL offer, at a stable address, a file holding every published claim with its status, the events that produced the status, its source articles by outlet, title, date and address, its promises, and the date the registries were last checked. The file SHALL hold only what the claim pages already show. It SHALL NOT hold article text, any claim not approved in review, outlet icon images, or raw registry payloads. In a preview build the file SHALL say that it is a preview and SHALL mark each claim not checked by a person.

#### Scenario: Reader downloads the data
- **WHEN** a reader requests the data file
- **THEN** they receive every published claim with its status, explaining events, articles, promises and the last-checked date

#### Scenario: Unpublished claim
- **WHEN** a claim has not been approved in review
- **THEN** it does not appear in the data file

#### Scenario: Article text
- **WHEN** the data file is inspected
- **THEN** it holds each article's outlet, title, date and address and no text from the article

### Requirement: The licence and the sources travel with the data
The data file SHALL name the licence it is offered under, how to credit it, the data sources with their addresses, and the address of the page that explains the method. The page that links to the file SHALL state the same.

#### Scenario: File read on its own
- **WHEN** the data file is opened away from the site
- **THEN** it states its licence, the credit line, its sources and where the method is explained

### Requirement: Trial facts in the download
The data file SHALL hold, for each published claim, the trials the claim page lists with the facts the page shows for each and the date each trial's registry record was read. It SHALL hold each event's confidence. It SHALL NOT hold a registry record itself, nor any fact the claim pages do not show.

#### Scenario: Claim with a trial that has posted results
- **WHEN** a reader downloads the data file
- **THEN** the claim's trial is in it with its participants, design, planned primary outcomes, posted results and the date its record was read

#### Scenario: Registry record
- **WHEN** the data file is inspected
- **THEN** it holds no registry record as the registry returned it

### Requirement: Reported statements in the download
The data file SHALL hold, for each published claim, the approved reported statements the claim page shows, each with its text, kind, firmness, speaker role, basis, confidence and the address of its article. It SHALL NOT hold a pending or rejected statement, nor any text from an article.

#### Scenario: Claim with approved statements
- **WHEN** a reader downloads the data file
- **THEN** the claim's approved statements are in it, each in the site's own words with its confidence and its article's address

#### Scenario: Pending statement
- **WHEN** a statement is still pending
- **THEN** it does not appear in the data file

### Requirement: Organisations in the download
The data file SHALL hold, for each published claim, the organisations the claim page lists, each with its name, roles and, when identified, its kind, country, website, registry record link, match score and the date its record was read; and, for each article, the organisation it is marked as published by. It SHALL NOT hold a person's name or a registry record itself.

#### Scenario: Claim with an identified sponsor
- **WHEN** a reader downloads the data file
- **THEN** the sponsor is in it with its registry link, kind, country, score and the trials it sponsors

#### Scenario: Person sponsor
- **WHEN** a claim's only sponsor is a person
- **THEN** the data file lists no organisation for that sponsor and names no one

### Requirement: Papers in the download
The data file SHALL hold, for each published claim, the papers the claim page lists, each with its identifier, link, roles, the facts the page shows for it and the date its index record was read. It SHALL NOT hold an abstract, an author, an affiliation or an index record itself.

#### Scenario: Claim with a results paper
- **WHEN** a reader downloads the data file
- **THEN** the claim's results paper is in it with its title, journal, year, kinds, the trial it reports and the date its record was read

#### Scenario: Authors
- **WHEN** the data file is inspected
- **THEN** it names no author of any paper
