# Spec Delta

## Purpose

Publishes reviewed claims as a static public site on which every status is shown with the sourced evidence that produced it.

## ADDED Requirements

### Requirement: Publication gate
The export that feeds the site SHALL contain only approved claims and, for each of them, only approved evidence events. Pending and rejected items SHALL NOT appear in the export in any form.

#### Scenario: Claim with mixed events
- **WHEN** an approved claim has three approved events and two pending events
- **THEN** the export contains the claim with three events

#### Scenario: Draft claim
- **WHEN** a claim is still a pending draft
- **THEN** the export does not contain it

### Requirement: Build from the export alone
The site SHALL be built from the export only, with no access to the database or to external services.

#### Scenario: Offline build
- **WHEN** the site is built on a machine that has the export and no network or database
- **THEN** the build succeeds

### Requirement: Claim page
Each published claim SHALL have a page at `/{slug}` that shows its headline, summary, status with any no-signal overlay, date first reported, promises next to what actually happened, and its evidence events. Each event SHALL show its date, summary and a link to its source.

#### Scenario: Reader opens a claim
- **WHEN** a reader opens the page of a claim with four approved events
- **THEN** the page shows the status and four dated events, each linking to its source

#### Scenario: Unknown slug
- **WHEN** a reader opens a slug that no published claim has
- **THEN** a not-found page is shown

### Requirement: Status explanation on the page
A claim page SHALL identify the evidence events that produced the current status.

#### Scenario: Status produced by one trial
- **WHEN** a claim's status is Phase 2 because of one trial
- **THEN** the page marks that trial's events as the reason for the status

### Requirement: Source articles are linked, not reproduced
A claim page SHALL list its source articles by outlet, title and date with a link to each. The site SHALL NOT display article text.

#### Scenario: Claim with two articles
- **WHEN** a claim has two source articles
- **THEN** the page lists both with links and shows no text from either

### Requirement: Topic index
Each vertical SHALL have an index page at `/topic/{vertical}` that lists its published claims with their statuses.

#### Scenario: Vertical with claims
- **WHEN** a reader opens the index of a vertical that has 30 published claims
- **THEN** 30 claims are listed with their statuses

### Requirement: Home page
The home page SHALL offer a search over published claims and SHALL list the claims whose status changed most recently.

#### Scenario: Search by intervention name
- **WHEN** a reader searches for a synonym of an intervention
- **THEN** the claim for that intervention is among the results

#### Scenario: Search with no result
- **WHEN** a reader searches for a term that matches no claim
- **THEN** the reader is told nothing was found

### Requirement: Approved claims page
The page at `/it-happened` SHALL list every published claim whose status is approved.

#### Scenario: No approved claims
- **WHEN** no published claim has the status approved
- **THEN** the page says that no tracked claim has reached approval yet

### Requirement: Status card image
Each published claim SHALL have a status card image that shows its headline, date first reported, latest promise as a date, and current status. The image SHALL be the claim page's link preview image and SHALL NOT show a count of days.

#### Scenario: Claim promised for 2025
- **WHEN** a claim's latest promise has the parsed date 31 December 2025
- **THEN** the card reads "promised by 2025" and shows no day count

#### Scenario: Claim with no promise
- **WHEN** a claim has no promises
- **THEN** the card omits the promise line

### Requirement: Footer notices
Every page SHALL carry a footer stating that the site gives no medical advice, that a registered trial is not a treatment option, which data sources are used, and when the data was last checked.

#### Scenario: Any page
- **WHEN** a reader opens any page of the site
- **THEN** the footer shows the two notices, the data sources and the last-checked date

### Requirement: Neutral wording
Status labels and overlay text SHALL describe evidence only. The site SHALL NOT describe a claim as dead, abandoned, a scam or any similar verdict.

#### Scenario: Long-quiet claim
- **WHEN** a preclinical-only claim has had no evidence event for six years
- **THEN** the page reads "no signal for 6 years" and uses no verdict wording
