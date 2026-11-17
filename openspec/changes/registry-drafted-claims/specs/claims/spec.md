# Spec Delta

## MODIFIED Requirements

### Requirement: Source articles
A claim SHALL have one or more source articles, each recorded with URL, outlet, title and published date, unless it was drafted from registry records, in which case it MAY have none. The same URL SHALL appear at most once per claim. A claim that was not drafted from registry records SHALL NOT be left with no source article.

#### Scenario: Add an article
- **WHEN** an operator adds an article with URL, outlet, title and published date to a claim
- **THEN** the article is listed among the claim's source articles

#### Scenario: Duplicate article URL
- **WHEN** an operator adds an article whose URL is already attached to the claim
- **THEN** no second article record is created and the operator is told the claim already has it

#### Scenario: A claim drafted from registry records
- **WHEN** a claim is drafted from registry records and no article reports it
- **THEN** the claim exists with no source article

#### Scenario: A claim entered by an operator with no article
- **WHEN** an operator enters a claim by hand and gives no article
- **THEN** the claim is not created and the operator is told an article is needed

### Requirement: First reported date
A claim's first reported date SHALL equal the earliest published date among its source articles, and SHALL be empty while the claim has no source article.

#### Scenario: Earlier article added later
- **WHEN** a claim first reported in 2019 gains a source article published in 2017
- **THEN** the claim's first reported date becomes the 2017 date

#### Scenario: A claim with no report
- **WHEN** a claim drafted from registry records has no source article
- **THEN** its first reported date is empty

#### Scenario: A first report arrives
- **WHEN** a claim with no source article gains one published in 2026
- **THEN** its first reported date becomes that date

## ADDED Requirements

### Requirement: A claim records what it was drafted from
Every claim SHALL record what it was drafted from: a news article, registry records, or an operator's entry. The record SHALL NOT change when the claim later gains an article or a trial.

#### Scenario: A registry-drafted claim gains an article
- **WHEN** a claim drafted from registry records gains its first source article
- **THEN** it still records that it was drafted from registry records
