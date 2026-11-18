# Spec Delta

## ADDED Requirements

### Requirement: Archived addresses answer gone
The address of an archived claim or source page SHALL answer with status 410 and a short page saying the page was taken down and on which date. It SHALL NOT state the reason. Archived items SHALL NOT appear in any feed, the sitemap, the lookup file or the data file.

#### Scenario: Reader opens an archived claim
- **WHEN** a reader opens the address of a claim archived on 14 November 2026
- **THEN** the response has status 410 and says the page was taken down on 14 November 2026

### Requirement: Confidence is shown with every match
Each entity match a claim page or source page shows SHALL carry its score as a word and a percentage, such as "High match · 92%", with its reasons available on request. The words and their bands SHALL be set by the site. A match a person approved SHALL keep its score. Pending candidates SHALL be listed apart from the matches that produced the status and SHALL NOT count toward it.

#### Scenario: Claim with one rule-approved trial and one pending candidate
- **WHEN** a reader opens the claim page
- **THEN** the trial that produced the status shows "High match" with its percentage, and the pending candidate is listed separately with its own score

## MODIFIED Requirements

### Requirement: Publication gate
The export that feeds the site SHALL contain only claims that are approved, by any decider, and not archived, and for each of them only approved evidence events. Pending, rejected and archived items SHALL NOT appear in the export in any form, except that pending candidate matches of a published claim SHALL appear with their scores, marked as candidates.

#### Scenario: Claim with mixed events
- **WHEN** an approved claim has three approved events and two pending events
- **THEN** the export contains the claim with three events

#### Scenario: Draft claim
- **WHEN** a claim is still a pending draft, or a draft rejected by rule
- **THEN** the export does not contain it

#### Scenario: Archived claim
- **WHEN** an approved claim is archived
- **THEN** the export does not contain it and lists its slug as archived
