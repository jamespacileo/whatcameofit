# Spec Delta

## ADDED Requirements

### Requirement: The quiet period starts at the latest thing known
The no-signal overlay SHALL be measured from the later of the claim's first reported date and its latest approved event. An approved event older than the first report SHALL NOT lengthen the quiet period.

#### Scenario: Record older than the report
- **WHEN** a claim first reported in September 2018 has one approved event, a trial registered in March 2013, and the as-of date is November 2026
- **THEN** the overlay says 8 years, not 13

#### Scenario: Recent report, old record
- **WHEN** a claim first reported 17 months before the as-of date has only an approved event from 13 years before it
- **THEN** there is no overlay
