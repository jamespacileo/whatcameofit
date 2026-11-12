# claims Specification

## Purpose
Holds the claims the site tracks, where a claim is one intervention for one indication, together with the news articles that reported each claim and the timelines those articles promised.

## Requirements

### Requirement: Claim identity
A claim SHALL represent exactly one intervention for one indication. News articles about the same intervention and indication SHALL attach to the same claim, whatever their publication date.

#### Scenario: Later article about an existing claim
- **WHEN** an operator adds a 2021 article about an intervention and indication that already have a claim from a 2018 article
- **THEN** the article is attached to the existing claim and no new claim is created

#### Scenario: Same intervention, different indication
- **WHEN** an operator adds a claim for an intervention that already has a claim for a different indication
- **THEN** a separate claim is created

### Requirement: No duplicate claims
Every claim SHALL record its intervention and its indication. The system SHALL refuse a new claim whose indication equals that of an existing claim and whose intervention equals that claim's intervention by name or by any synonym, ignoring letter case and spacing. The refusal SHALL name the existing claim.

#### Scenario: Second claim for the same intervention and indication
- **WHEN** an operator adds a claim for an intervention and indication that already have a claim
- **THEN** the claim is not created and the operator is told the slug of the existing claim

#### Scenario: Compound known under another name
- **WHEN** an existing claim's intervention has the synonym "TRG-035" and an operator adds a claim for "trg-035" with the same indication
- **THEN** the claim is not created

### Requirement: Claim slug
Each claim SHALL have a unique slug made of lowercase letters, digits and hyphens, at most 60 characters long. A slug SHALL NOT change after the claim has been published.

#### Scenario: Duplicate slug
- **WHEN** an operator creates a claim with a slug that another claim already uses
- **THEN** the claim is not created and the operator is told the slug is taken

#### Scenario: Slug change after publication
- **WHEN** an operator tries to change the slug of a claim that has been published
- **THEN** the change is refused

### Requirement: Source articles
A claim SHALL have one or more source articles, each recorded with URL, outlet, title and published date. The same URL SHALL appear at most once per claim.

#### Scenario: Add an article
- **WHEN** an operator adds an article with URL, outlet, title and published date to a claim
- **THEN** the article is listed among the claim's source articles

#### Scenario: Duplicate article URL
- **WHEN** an operator adds an article whose URL is already attached to the claim
- **THEN** no second article record is created and the operator is told the claim already has it

### Requirement: No article text
The system SHALL NOT persist the body text of a news article in any form. Only the URL, outlet, title, published date, a content hash and an archive URL MAY be kept for an article.

#### Scenario: Article stored after extraction
- **WHEN** an article has been added and processed
- **THEN** no stored record contains the article body

### Requirement: Promised timelines
Each timeline promised for a claim SHALL be recorded separately with a short description, the source article it came from, and a parsed date when one can be determined. A claim MAY have zero or more promises.

#### Scenario: Repeated promises
- **WHEN** a 2018 article promises human trials "by 2020" and a 2021 article promises them "by 2024"
- **THEN** the claim has two promises, each linked to its own article

#### Scenario: Year-only promise
- **WHEN** a promise reads "by 2025"
- **THEN** its parsed date is 31 December 2025

#### Scenario: Relative promise
- **WHEN** an article published on 10 March 2018 promises results "within five years"
- **THEN** the parsed date is 10 March 2023

#### Scenario: Unparseable promise
- **WHEN** a promise reads "in the near future"
- **THEN** the description is kept and the parsed date is empty

### Requirement: First reported date
A claim's first reported date SHALL equal the earliest published date among its source articles.

#### Scenario: Earlier article added later
- **WHEN** a claim first reported in 2019 gains a source article published in 2017
- **THEN** the claim's first reported date becomes the 2017 date

### Requirement: Vertical
Each claim SHALL belong to exactly one vertical from a configured set of verticals.

#### Scenario: Unknown vertical
- **WHEN** an operator creates a claim with a vertical that is not in the configured set
- **THEN** the claim is not created and the valid verticals are listed

### Requirement: Evidence stage at announcement
A claim SHALL be able to carry the stage of evidence at the time of announcement: in vitro, animal, early human or late human. The stage SHALL stay empty until an operator has confirmed it.

#### Scenario: Suggested but unconfirmed stage
- **WHEN** a stage has been suggested for a claim and no operator has confirmed it
- **THEN** the claim's stage is empty

### Requirement: Manual and bulk entry
An operator SHALL be able to add claims and source articles one at a time from the command line, or many at once from a CSV file. A CSV import SHALL be all-or-nothing.

#### Scenario: CSV with an invalid row
- **WHEN** an operator imports a CSV file in which row 7 has no URL
- **THEN** nothing is imported and the error names row 7 and the missing field

#### Scenario: Valid CSV
- **WHEN** an operator imports a CSV file in which every row is valid
- **THEN** every claim and article in the file is created
