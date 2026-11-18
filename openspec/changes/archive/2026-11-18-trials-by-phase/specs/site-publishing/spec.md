## MODIFIED Requirements

### Requirement: A long list of trials opens with the furthest
The claim page SHALL show first, under a "Results posted" heading, every trial that has posted results, whatever its phase, each row naming its own phase. It SHALL group the other trials by each trial's furthest phase, furthest first, under a heading that names the phase and counts its trials. A trial whose phases are Phase 1 and Phase 2 SHALL sit with Phase 2, and the heading of a group with more than one phase wording SHALL read "<phase>, including <other wording>". Trials with no phase SHALL be in a last group named "No phase given". Each group SHALL show its first ten trials and SHALL keep the rest of that group reachable on the same page without loading anything. A group's heading SHALL stay in view while its trials are read.

#### Scenario: Claim with fifteen trials across three phases
- **WHEN** a reader opens a claim with four Phase 3 trials, ten trials of Phase 2 or Phase 1/Phase 2, and one with no phase, none with posted results
- **THEN** the page shows three headings in that order, "Phase 3", "Phase 2, including Phase 1/Phase 2" and "No phase given", with all fifteen trials shown

#### Scenario: Trials with posted results lead
- **WHEN** a claim has a Phase 2 trial that posted results and a Phase 3 trial that did not
- **THEN** the Phase 2 trial is shown first, under "Results posted", and names its phase

#### Scenario: Claim with twelve Phase 2 trials
- **WHEN** a reader opens a claim with twelve Phase 2 trials and none with posted results
- **THEN** ten are shown under the Phase 2 heading and the other two open on request

## ADDED Requirements

### Requirement: A trial reads as one row
Each trial SHALL be one row under its group's column names: how many people, what it was compared with, its main measure, its state and its identifier. What it was compared with SHALL be the names the record gives its comparator arms, at most two and a count of the rest, else the plain words for the kinds of comparator. When the claim's treatment is only a comparator in the trial, the row SHALL say what the trial tests and that the claim's treatment is what it is compared with. The main measure SHALL be the registry's own words for its first main measure; an abbreviation the site knows SHALL be said plainly under it, once per section, on the first row that uses it; the sponsor SHALL be named under it with its kind. When a trial has posted results, the date SHALL be under its state. The control that opens a row SHALL say that it opens more from the trial's record. The design SHALL be in the row's fold, once, with the registry's terms under it, and the match SHALL be said once, in the fold's notes.

#### Scenario: A finished Phase 2 trial with posted results
- **WHEN** a reader opens a claim with one finished Phase 2 trial of 83 people, placebo-controlled, that posted results on 1 Sep 2025
- **THEN** its row reads "83 people", "Placebo", its main measure, "Finished" with "Results posted 1 Sep 2025" under it, and its identifier, and the row's fold says "Assigned at random · Blinded" with the registry's terms under it

#### Scenario: The claim's treatment is only what a trial compares with
- **WHEN** a trial's record tests another drug against the claim's treatment
- **THEN** its row names the claim's treatment under "Compared with" and says "It tests <other drug>; <treatment> is what it is compared with."

#### Scenario: An abbreviation in the main measure
- **WHEN** two rows' main measures say "PFS"
- **THEN** the first says "PFS: progression-free survival, the time before the illness grew or got worse" under the registry's words, and the second does not
