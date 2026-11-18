# open-data Specification

## Purpose
The published claims as a file anyone can download, cite and reuse, under a stated licence, so that the site's evidence can be checked and built on without scraping it.

## Requirements

### Requirement: Published claims as a download
The site SHALL offer, at a stable address (`/data/claims.json`), an index holding a short entry for every published claim, in a list named `entries`: its slug, headline, intervention, indication, status code, first reported date, the date the registries were last checked, and the address of its full record, given from the root of the site that serves the index, so a copy of the site (a pull request's preview) leads to its own records. The index and each record file SHALL name their kind and version (`format`, `format_version` 2), so a tool written for the single file of every full record, which had neither, fails at once. Each published claim's full record SHALL be offered as a file of its own at `/data/claims/<slug>.json`, holding the claim with its status, the events that produced the status, its matches with their scores, its source articles by outlet, title, date and address, its promises, whether a person checked it, and the date the registries were last checked. The files SHALL hold only what the claim pages already show. They SHALL NOT hold article text, any claim that is unpublished or archived, outlet icon images, or raw registry payloads. In a preview build the files SHALL say that they are a preview and SHALL mark each claim not checked by a person. The page that links to the index SHALL say how to fetch every record: the index, then each address it gives.

#### Scenario: Reader downloads the data
- **WHEN** a reader requests the index
- **THEN** they receive an entry for every published claim with its status code, the last-checked date and the address of its full record

#### Scenario: Reader fetches a claim's record
- **WHEN** a reader requests the address an index entry gives
- **THEN** they receive that claim's full record with its status, explaining events, scored matches, articles, promises and the last-checked date

#### Scenario: Index served by a preview copy
- **WHEN** a reader follows an entry's record address in the index a pull request's preview serves
- **THEN** it leads to that preview's record file, not production's

#### Scenario: Tool written for the old file
- **WHEN** a tool that reads full records from the old file's `claims` list reads the index
- **THEN** it finds no `claims` list, and the index names itself `claims-index`, version 2

#### Scenario: Unpublished claim
- **WHEN** a claim is pending or rejected
- **THEN** it has no index entry and no record file

#### Scenario: Archived claim
- **WHEN** a claim has been archived
- **THEN** it has no index entry and no record file

#### Scenario: Article text
- **WHEN** the index and the record files are inspected
- **THEN** they hold each article's outlet, title, date and address and no text from the article

### Requirement: The licence and the sources travel with the data
The index and every record file SHALL each name the licence the data is offered under, how to credit it, the data sources with their addresses, and the address of the page that explains the method. The page that links to the index SHALL state the same.

#### Scenario: File read on its own
- **WHEN** the index or a single record file is opened away from the site
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

### Requirement: Background cards in the download
The data file SHALL hold, for each published claim, each background card the claim page shows whose source's licence allows it to be offered under the file's licence, with its label, link, source, score, reasons and the date its record was read. A card or a fact whose licence does not allow this SHALL be left out, and the file SHALL name each source left out and say why.

#### Scenario: Card from a public-domain source
- **WHEN** a claim's card comes from a source that places no condition on reuse
- **THEN** the card is in the data file with its source named

#### Scenario: Target card from a named gene
- **WHEN** a claim's page shows a target card whose function description is offered under an attribution licence
- **THEN** the card is in the data file with the description's source credited, its score and its reasons

#### Scenario: Fact from a share-alike source
- **WHEN** a claim's page shows a mechanism from a share-alike source
- **THEN** the data file leaves the mechanism out and names the source and its licence as the reason

### Requirement: No built file near the host's limit
Every build of the site SHALL fail when any single built file is larger than 20 MiB, and SHALL name each such file and its size. The host refuses a file over 25 MiB at deploy time; this check stops the build first, so a deploy cannot fail on a file's size.

#### Scenario: A built file over 20 MiB
- **WHEN** a build produces a file of 21 MiB
- **THEN** the build fails, naming that file, its size and the 20 MiB limit, and nothing is deployed

#### Scenario: Every file under the limit
- **WHEN** every built file is 20 MiB or smaller
- **THEN** the size check passes and says so

### Requirement: Built files counted against the host's limit
Every build of the site SHALL count the files it built and say how many. It SHALL fail when there are more than 18,000, or more than a higher limit set for a plan that allows more, and SHALL give the count, the limit and the host's own limit. The host refuses a version of more than 20,000 files on its free plan.

#### Scenario: Too many built files
- **WHEN** a build produces 18,001 files and no higher limit is set
- **THEN** the build fails, saying how many files it holds, the 18,000 it may hold and the host's 20,000, and nothing is deployed

#### Scenario: A build under the limit
- **WHEN** a build produces 14,223 files
- **THEN** the check passes and says 14,223 files of the 18,000 a build may hold
