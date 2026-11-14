# Spec Delta

## Purpose

Measures how well triage separates leads that report a treatment from those that do not, from labels the operator gives a sample, and keeps leads from being read until that has been measured.

## ADDED Requirements

### Requirement: Sample across the score range
`thenwhat backfill sample-leads` SHALL draw a sample of scored leads that have no label, in equal numbers from each tenth of the score range and spread across platforms. The same seed SHALL draw the same sample. For each lead it SHALL show the title, the outlet, the date first shared and the address, and SHALL NOT show the score.

#### Scenario: A sample of 200
- **WHEN** the operator asks for 200 leads and every tenth of the score range holds at least 20 unlabelled leads
- **THEN** 20 leads from each tenth are listed, without their scores

#### Scenario: A thin tenth
- **WHEN** one tenth of the score range holds only 5 unlabelled leads
- **THEN** those 5 are listed, and the output says that tenth is short

### Requirement: Lead label
`thenwhat backfill label-lead` SHALL record for a lead one of the triage options as its label, with who gave it and when. A label given by an assistant SHALL be recorded as an assistant's, never as a person's. A lead SHALL have at most one label from a person and one from an assistant. A label SHALL belong to the lead, and SHALL stay when triage is run again at a new version.

#### Scenario: The operator labels a lead
- **WHEN** the operator labels a lead as reporting a specific treatment for a specific condition
- **THEN** the lead has that label, recorded as a person's

#### Scenario: An assistant labels a lead
- **WHEN** a label is given with `--as-assistant`
- **THEN** it is recorded as an assistant's and is not counted as a person's label anywhere

#### Scenario: A label that is not an option
- **WHEN** the operator gives a label that is not one of the triage options
- **THEN** the command fails, lists the options and records nothing

### Requirement: Evaluation report
`thenwhat backfill evaluate-leads` SHALL report, from leads that have a person's label and a score at the current triage version, for each pass threshold from 0.1 to 0.9: the share of leads at or above it that report a treatment (precision), the share of all leads reporting a treatment that are at or above it (recall), and how many scored leads are at or above it.

#### Scenario: After 200 labels
- **WHEN** 200 leads have a person's label
- **THEN** the report gives precision, recall and the number of leads passed at each threshold

#### Scenario: No labels yet
- **WHEN** no lead has a person's label
- **THEN** the report says so and gives no figures

### Requirement: Figures describe the leads, not the sample
Each tenth of the score range SHALL be weighted in the report's figures by how many scored leads it holds, because the sample takes equal numbers from each tenth.

#### Scenario: A crowded low tenth
- **WHEN** the lowest tenth holds 60,000 scored leads and the highest 2,000, and 20 of each are labelled
- **THEN** a labelled lead in the lowest tenth counts thirty times as much as one in the highest

### Requirement: What the report breaks down
The report SHALL give the number of labels in each tenth, the same figures for each platform, and the labelled leads on which label and score disagree most. Assistants' labels SHALL be reported separately and SHALL NOT enter the figures.

#### Scenario: Two platforms
- **WHEN** labelled leads come from Hacker News and from Reddit
- **THEN** precision and recall are given for each platform as well as overall

#### Scenario: Assistant labels present
- **WHEN** 50 leads have only an assistant's label
- **THEN** they are counted in their own line and change no precision or recall figure

### Requirement: Nothing is read before triage is measured
The reading step SHALL refuse to run while fewer than the configured number of leads, 200 unless set otherwise, have both a person's label and a score at the current triage version, or while either threshold is unset. The refusal SHALL name what is missing.

#### Scenario: Too few labels
- **WHEN** 120 leads have a person's label and the reading step is run
- **THEN** it refuses, says 80 more labels are needed, and reads nothing

#### Scenario: Triage version raised
- **WHEN** the triage version is raised after 200 leads were labelled, and those leads have been scored again
- **THEN** their labels count for the new version without being given again

### Requirement: Labels stay private
A lead's label and score SHALL NOT appear in the export or on the site.

#### Scenario: Export after labelling
- **WHEN** leads are labelled and the export is produced
- **THEN** the export is identical to the one produced before
