# Spec Delta

## MODIFIED Requirements

### Requirement: Published claims as a download
The site SHALL offer, at a stable address (`/data/claims.json`), an index holding a short entry for every published claim, in a list named `entries`: its slug, headline, intervention, indication, status code, first reported date, the date the registries were last checked, and the address of its full record, given from the root of the site that serves the index, so a copy of the site (a pull request's preview) leads to its own records. The index and each record file SHALL name their kind and version (`format`, `format_version` 2), so a tool written for the single file of every full record, which had neither, fails at once. Each published claim's full record SHALL be offered as a file of its own at `/data/claims/<slug>.json`, holding the claim with its status, the events that produced the status, its source articles by outlet, title, date and address, its promises, and the date the registries were last checked. The files SHALL hold only what the claim pages already show. They SHALL NOT hold article text, any claim not approved in review, outlet icon images, or raw registry payloads. In a preview build the files SHALL say that they are a preview and SHALL mark each claim not checked by a person. The page that links to the index SHALL say how to fetch every record: the index, then each address it gives.

#### Scenario: Reader downloads the data
- **WHEN** a reader requests the index
- **THEN** they receive an entry for every published claim with its status code, the last-checked date and the address of its full record

#### Scenario: Reader fetches a claim's record
- **WHEN** a reader requests the address an index entry gives
- **THEN** they receive that claim's full record with its status, explaining events, articles, promises and the last-checked date

#### Scenario: Index served by a preview copy
- **WHEN** a reader follows an entry's record address in the index a pull request's preview serves
- **THEN** it leads to that preview's record file, not production's

#### Scenario: Tool written for the old file
- **WHEN** a tool that reads full records from the old file's `claims` list reads the index
- **THEN** it finds no `claims` list, and the index names itself `claims-index`, version 2

#### Scenario: Unpublished claim
- **WHEN** a claim has not been approved in review
- **THEN** it has no index entry and no record file

#### Scenario: Article text
- **WHEN** the index and the record files are inspected
- **THEN** they hold each article's outlet, title, date and address and no text from the article

### Requirement: The licence and the sources travel with the data
The index and every record file SHALL each name the licence the data is offered under, how to credit it, the data sources with their addresses, and the address of the page that explains the method. The page that links to the index SHALL state the same.

#### Scenario: File read on its own
- **WHEN** the index or a single record file is opened away from the site
- **THEN** it states its licence, the credit line, its sources and where the method is explained

## ADDED Requirements

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
