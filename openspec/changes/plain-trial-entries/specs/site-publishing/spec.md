# Spec Delta

## MODIFIED Requirements

### Requirement: Trials on the claim page
A claim page SHALL list each of the claim's trials once, under its own heading, with its registry identifier linked to the record, its state, the facts the export carries for it, and the score of its match. An entry SHALL show the trial's phase when the registry gives one, and SHALL say inside its fold when the registry gives none. Trials SHALL be ordered furthest phase first and, within a phase, those with posted results first. Each trial event in the timetable SHALL lead to its trial. A claim with no trial SHALL show no such section.

#### Scenario: Claim with one completed Phase 2 trial
- **WHEN** a reader opens a claim whose one trial enrolled 83 participants, was randomised and has posted results
- **THEN** the page shows that trial once with its identifier, "Phase 2", that it has finished, 83 people, that people were assigned at random, and its posted primary outcome

#### Scenario: Trial with no phase
- **WHEN** a trial's registry record gives no phase
- **THEN** the entry's visible lines name no phase, and its fold says the registry gives none

#### Scenario: Reader follows a timetable entry
- **WHEN** a reader presses a trial's "results posted" entry in the timetable
- **THEN** they can reach that trial's entry and its posted results

#### Scenario: Claim with no trial
- **WHEN** a claim has no trial
- **THEN** the page shows no trials section and no placeholder for one

## ADDED Requirements

### Requirement: A trial entry leads with plain words
A trial's entry SHALL lead with a heading that states how many people the trial enrolled or plans to enrol and, where its record names what it was compared with, that comparison. The heading SHALL state only what the record states. The registry's own title SHALL be shown inside the entry's fold. Every trial SHALL be drawn at the same size and weight.

#### Scenario: Trial with a named comparison
- **WHEN** a device trial enrolled 135 participants and its record names a sham comparator and no treatment
- **THEN** its heading reads "135 people, compared with a sham device and with no treatment"

#### Scenario: Trial whose record names no comparison
- **WHEN** a trial enrolled 34 participants and its record names no comparator
- **THEN** its heading reads "34 people" and says nothing about a comparison

#### Scenario: Planned size
- **WHEN** a trial not yet started plans to enrol 400 participants
- **THEN** its heading says 400 people are planned, not that 400 took part

#### Scenario: Trial that states no size
- **WHEN** a trial's record states no number of participants
- **THEN** its heading is the registry's title, and the title is not repeated in the fold

### Requirement: A trial's design and state are said in plain words
Under its heading a trial's entry SHALL say, in the site's fixed plain wording, how people were assigned, whether the trial was blinded or open label, its state with the date it finished when it has finished, and that results are posted with the date they were posted. The registry's exact terms for the design SHALL be shown inside the fold. No wording SHALL say that a trial is open to participants or how it turned out.

#### Scenario: Randomised, quadruple-blind, completed, results posted
- **WHEN** a trial is randomised and quadruple-blind, completed on 5 March 2023 and posted results on 30 June 2026
- **THEN** the entry reads that people were assigned at random, that it was blinded, that it finished on 5 March 2023 and that results were posted on 30 June 2026, and its fold gives "Randomised, quadruple-blind" in the registry's terms

#### Scenario: Open-label trial
- **WHEN** a trial's masking is none
- **THEN** the entry says it was open label and says what that means in a few words

#### Scenario: Trial under way
- **WHEN** a trial is under way
- **THEN** the entry says it is under way, with no finishing date, and nothing says it is recruiting

#### Scenario: Design the record does not state
- **WHEN** a trial's record states neither allocation nor masking
- **THEN** the entry says nothing about how people were assigned or whether it was blinded

### Requirement: A trial entry says what it measured where a reading allows
Where a trial's first main measure has a usable reading of its kind, the entry SHALL say in one sentence what the trial measured, in the same fixed wording "The record in brief" uses for that kind, with how long it was followed when that reading is usable too. The entry SHALL say that a model read that sentence and that it was checked against the record. With no usable reading the entry SHALL have no such sentence, and the measures SHALL remain listed in the registry's words inside the fold.

#### Scenario: Symptom score followed for four weeks
- **WHEN** a trial's first main measure has a measure reading of symptom score, a title that names a change, and a follow-up reading of 4 weeks
- **THEN** the entry says it measured how much a symptom score changed over 4 weeks, and says a model read that and it was checked against the record

#### Scenario: Same wording as the record in brief
- **WHEN** the claim's largest trial has a measure sentence in its entry
- **THEN** the words for the measure are the same as in the brief's answer about what the largest trial measured

#### Scenario: No usable reading
- **WHEN** a trial has no reading, a reading too unsure to use, or a reading of a kind the site has no words for
- **THEN** the entry has no measure sentence and its fold lists the planned measures in the registry's words

### Requirement: Posted results are a table that says what its numbers are
Inside a trial's fold, a posted main measure with one value for each group SHALL be shown as a table with a row for each group, its value as the registry wrote it and how many were analysed, under a caption that names the measure and says what the numbers are. No figure SHALL be larger than body text, and nothing SHALL draw a result. The entry SHALL say that the registry record states what the measure runs from and to, and SHALL link to the record. The fold's control SHALL say whether posted results are inside.

#### Scenario: Three groups with a mean change
- **WHEN** a trial posted a mean change with a standard deviation for each of three groups, each with 39 analysed
- **THEN** the fold shows a table of three rows with the group, the mean change, the standard deviation and 39 analysed

#### Scenario: Measure that is a change
- **WHEN** the posted measure's title names a change and a group's value is below zero
- **THEN** a line under the table says a minus number is a fall

#### Scenario: Posted comparison
- **WHEN** the record gives a p value for a comparison of two groups
- **THEN** it is shown under the table as the record states it, naming the two groups, with no word on whether the measure was met

#### Scenario: Outcome posted in several rows
- **WHEN** a posted main measure gives several rows of values for each group
- **THEN** no table is shown for it, and the entry says the values are in the registry record

#### Scenario: Fold with no results
- **WHEN** a trial has posted no results
- **THEN** the fold's control does not mention results

#### Scenario: Narrow screen
- **WHEN** a reader opens a trial's results on a screen 320 pixels wide
- **THEN** the table is readable without the page being widened, and every control is at least 44 pixels tall
