# Spec Delta

## Purpose

Measures how well triage separates leads that report a treatment from those that do not, from labels given to a sample by the operator or by an assistant the operator spot-checks, and keeps leads from being read until that has been measured.

## ADDED Requirements

### Requirement: Sample across the score range
`thenwhat backfill sample-leads` SHALL draw a sample of scored leads that have no label, in equal numbers from each tenth of the score range and spread across platforms. Asked for one tenth, it SHALL draw the whole sample from that tenth. The same seed SHALL draw the same sample. For each lead it SHALL show the title, the outlet, the date first shared and the address, and SHALL NOT show the score.

#### Scenario: A sample of 200
- **WHEN** the operator asks for 200 leads and every tenth of the score range holds at least 20 unlabelled leads
- **THEN** 20 leads from each tenth are listed, without their scores

#### Scenario: A thin tenth
- **WHEN** one tenth of the score range holds only 5 unlabelled leads
- **THEN** those 5 are listed, and the output says that tenth is short

#### Scenario: A crowded tenth
- **WHEN** the operator asks for 300 leads from the one tenth of the score range that starts at 0.0
- **THEN** 300 unlabelled leads scored under 0.1 are listed, and no other tenth is drawn from

#### Scenario: A lead an assistant has labelled
- **WHEN** a lead has an assistant's label and no person's
- **THEN** it is not drawn again

### Requirement: Lead label
`thenwhat backfill label-lead` SHALL record for a lead one of the triage options as its label, with who gave it and when. A label given by an assistant SHALL be recorded as an assistant's, never as a person's. A lead SHALL have at most one label from a person and one from an assistant. A label SHALL belong to the lead, and SHALL stay when triage is run again at a new version.

#### Scenario: The operator labels a lead
- **WHEN** the operator labels a lead as reporting a specific treatment for a specific condition
- **THEN** the lead has that label, recorded as a person's

#### Scenario: An assistant labels a lead
- **WHEN** a label is given with `--as-assistant`
- **THEN** it is recorded as an assistant's and is never shown or stored as a person's

#### Scenario: A label that is not an option
- **WHEN** the operator gives a label that is not one of the triage options
- **THEN** the command fails, lists the options and records nothing

### Requirement: Labels from a file
`thenwhat backfill label-leads` SHALL record the labels in a file that gives a lead's number and a label on each line, as a person's or with `--as-assistant` as an assistant's. It SHALL record all of them or none: a line that names no lead, or a label that is not an option, SHALL fail the whole file and name the line.

#### Scenario: A file of 200 labels
- **WHEN** a file of 200 valid lines is given with `--as-assistant`
- **THEN** 200 labels are recorded as an assistant's

#### Scenario: One bad line
- **WHEN** line 7 of a file gives a label that is not an option
- **THEN** nothing is recorded and the error names line 7

### Requirement: Which label counts
A lead's label for measuring triage SHALL be the person's when a person has labelled it, and otherwise the assistant's. The operator decided on 2026-11-14 that an assistant's labels count where no person has labelled, on condition that the operator spot-checks them.

#### Scenario: Both have labelled a lead
- **WHEN** an assistant labelled a lead as a treatment report and the operator then labels it as other health news
- **THEN** the lead counts as other health news

#### Scenario: Only an assistant has labelled a lead
- **WHEN** a lead has an assistant's label and no person's
- **THEN** the assistant's label counts

### Requirement: Evaluation report
`thenwhat backfill evaluate-leads` SHALL report, from leads that have a label that counts and a score at the current triage version, for each pass threshold from 0.1 to 0.9: the share of leads at or above it that report a treatment (precision), the share of all leads reporting a treatment that are at or above it (recall), and how many scored leads are at or above it.

#### Scenario: After 200 labels
- **WHEN** 200 leads have a label that counts
- **THEN** the report gives precision, recall and the number of leads passed at each threshold

#### Scenario: No labels yet
- **WHEN** no lead has a label
- **THEN** the report says so and gives no figures

### Requirement: Figures describe the leads, not the sample
Each tenth of the score range SHALL be weighted in the report's figures by how many scored leads it holds, because the sample takes equal numbers from each tenth.

#### Scenario: A crowded low tenth
- **WHEN** the lowest tenth holds 60,000 scored leads and the highest 2,000, and 20 of each are labelled
- **THEN** a labelled lead in the lowest tenth counts thirty times as much as one in the highest

### Requirement: What the report breaks down
The report SHALL give the number of labels in each tenth, the same figures for each platform, and the labelled leads on which label and score disagree most. It SHALL say how many of the labels that count are a person's and how many an assistant's, and, for the leads both have labelled, on how many they agree.

#### Scenario: Two platforms
- **WHEN** labelled leads come from Hacker News and from Reddit
- **THEN** precision and recall are given for each platform as well as overall

#### Scenario: Labels by an assistant and spot-checks by the operator
- **WHEN** 200 leads have an assistant's label and the operator has labelled 30 of them, agreeing on 27
- **THEN** the report says 170 labels are an assistant's, 30 a person's, and that the two agree on 27 of the 30 both labelled

### Requirement: Spot-check list
`thenwhat backfill spot-check-leads` SHALL list, from the leads that only an assistant has labelled: those on which the assistant's label and the score disagree most, and a random draw of the rest, which the same seed draws again. For each it SHALL show the title, the outlet, the address and the assistant's label, so that the operator can label it themselves. It SHALL NOT show the score.

#### Scenario: After an assistant has labelled a sample
- **WHEN** an assistant has labelled 200 leads and the operator asks for the list
- **THEN** the strongest disagreements and a random 30 of the others are listed with the assistant's label

#### Scenario: The operator corrects a label
- **WHEN** the operator labels a listed lead differently from the assistant
- **THEN** the operator's label counts and the lead leaves the list

### Requirement: Nothing is read before triage is measured
The reading step SHALL refuse to run while fewer than the configured number of leads, 200 unless set otherwise, have both a label that counts and a score at the current triage version, or while either threshold is unset. The refusal SHALL name what is missing.

#### Scenario: Too few labels
- **WHEN** 120 leads have a label that counts and the reading step is run
- **THEN** it refuses, says 80 more labels are needed, and reads nothing

#### Scenario: Triage version raised
- **WHEN** the triage version is raised after 200 leads were labelled, and those leads have been scored again
- **THEN** their labels count for the new version without being given again

### Requirement: Labels stay private
A lead's label and score SHALL NOT appear in the export or on the site.

#### Scenario: Export after labelling
- **WHEN** leads are labelled and the export is produced
- **THEN** the export is identical to the one produced before
