# Spec Delta

## Purpose

The published claims as a file anyone can download, cite and reuse, under a stated licence, so that the site's evidence can be checked and built on without scraping it.

## ADDED Requirements

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
