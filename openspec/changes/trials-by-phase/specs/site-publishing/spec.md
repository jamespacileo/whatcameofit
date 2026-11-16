## MODIFIED Requirements

### Requirement: A long list of trials opens with the furthest
The claim page SHALL group its trials by each trial's furthest phase, furthest first, under a heading that names the phase and counts its trials. A trial whose phases are Phase 1 and Phase 2 SHALL sit with Phase 2, and a heading over more than one phase wording SHALL name each. Trials with no phase SHALL be in a last group named "No phase given". Each phase SHALL show its first ten trials and SHALL keep the rest of that phase reachable on the same page without loading anything.

#### Scenario: Claim with fifteen trials across three phases
- **WHEN** a reader opens a claim with four Phase 3 trials, ten trials of Phase 2 or Phase 1/Phase 2, and one with no phase
- **THEN** the page shows three headings in that order, "Phase 3", "Phase 2 and Phase 1/Phase 2" and "No phase given", with all fifteen trials shown

#### Scenario: Claim with twelve Phase 2 trials
- **WHEN** a reader opens a claim with twelve Phase 2 trials
- **THEN** ten are shown under the Phase 2 heading and the other two open on request

#### Scenario: Posted results among the trials not shown
- **WHEN** one of the trials of a phase that are not shown has posted results
- **THEN** the control that opens them says that one has results posted

## ADDED Requirements

### Requirement: A trial reads as one row
Each trial SHALL be one row with columns for how many people, what it was compared with, its main measure, its state and its identifier. The main measure SHALL be the registry's own words for its first main measure, with the sponsor's name under it; the plain reading stays in the row's fold. When a trial has posted results, its state SHALL say "Results posted" with the date under the state. The trial's design SHALL be in the row's fold. Only the first phase's table SHALL show the column names on screen.

#### Scenario: A finished Phase 2 trial with posted results
- **WHEN** a reader opens a claim with one finished Phase 2 trial of 83 people that posted results on 1 Sep 2025
- **THEN** its row reads "83 people", "A placebo", its main measure, "Finished" with "Results posted 1 Sep 2025" under it, and its identifier, and the row's fold says "Assigned at random · Blinded"
