# Spec Delta

## ADDED Requirements

### Requirement: Article lookup file
The site SHALL publish a file at `/lookup.json` that maps the address of every source article of a published claim to that claim, and gives for each published claim its headline, status wording, no-signal note, first-reported date, latest dated promise and page address. The file SHALL carry the footer notices and the date the registries were last checked. It SHALL contain no article text.

#### Scenario: Article of a published claim
- **WHEN** a published claim has a source article
- **THEN** the lookup file lists that article's address in its comparison form and names the claim

#### Scenario: Two addresses of one article
- **WHEN** an article is reached with or without "www.", a trailing slash, a tracking parameter or a fragment
- **THEN** all of those addresses have the same comparison form

#### Scenario: Unpublished claim
- **WHEN** a claim has not been approved in review
- **THEN** neither the claim nor its articles appear in the lookup file
