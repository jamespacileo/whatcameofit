# Spec Delta

## ADDED Requirements

### Requirement: A report on the website of a trial's sponsor is marked by rule
A source article whose address is on the website that an approved organisation record gives for the lead sponsor of one of the claim's approved trials SHALL be marked as published by that organisation, by rule and with no model, so that the claim page says the report is on that organisation's website. A report on a website no approved organisation record gives SHALL carry no such mark, and the mark SHALL NOT be set from an agent's hint, a headline or a guess at who owns a domain.

#### Scenario: A release on the sponsor's investor pages
- **WHEN** a claim's report is on a subdomain of the website an approved organisation record gives for the sponsor of one of its approved trials
- **THEN** the page says, beside the report, that it is on that organisation's website

#### Scenario: A company page with no organisation record
- **WHEN** a claim's report is on a company's website and no approved organisation record gives that website
- **THEN** the page lists the report with its outlet's name and says nothing more about it
