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

### Requirement: Looking up a pasted link
The home page's main field SHALL accept the address of a news article as well as search words. An address SHALL be compared with the lookup file in the reader's browser and SHALL NOT be sent to any server. For a tracked article the page SHALL show its claim and status; for an untracked one it SHALL show the tracked claims that share words with the address, stated to be a guess, or say that nothing tracked looks close and that this implies nothing about the story. A shortened link or a social media post SHALL be named as such, with what to paste instead.

#### Scenario: Tracked article
- **WHEN** a reader pastes the address of a source article of a published claim
- **THEN** the claim's headline and status are shown with a link to its page

#### Scenario: The same article shared another way
- **WHEN** the address arrives inside a social site's redirect, an AMP cache or a web archive, or with a mobile host or tracking parameters
- **THEN** it is read as the article itself

#### Scenario: Another outlet's report
- **WHEN** the address is not tracked but its words name a tracked treatment, or share two or more telling words with a tracked claim
- **THEN** those claims are listed as a guess for the reader to check

#### Scenario: Shortened link
- **WHEN** the address belongs to a link shortener
- **THEN** the reader is told to open it and paste the article's own address
