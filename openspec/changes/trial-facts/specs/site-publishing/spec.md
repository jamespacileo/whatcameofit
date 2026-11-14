# Spec Delta

## ADDED Requirements

### Requirement: Trials on the claim page
A claim page SHALL list each of the claim's trials once, under its own heading, with its registry identifier linked to the record, phase, state, the facts the export carries for it, and the score of its match. Trials SHALL be ordered furthest phase first and, within a phase, those with posted results first. Each trial event in the timetable SHALL lead to its trial. A claim with no trial SHALL show no such section.

#### Scenario: Claim with one completed Phase 2 trial
- **WHEN** a reader opens a claim whose one trial enrolled 83 participants, was randomised and has posted results
- **THEN** the page shows that trial once with its identifier, "Phase 2", its state, 83 participants, its design and its posted primary outcome

#### Scenario: Reader follows a timetable entry
- **WHEN** a reader presses a trial's "results posted" entry in the timetable
- **THEN** they can reach that trial's entry and its posted results

#### Scenario: Claim with no trial
- **WHEN** a claim has no trial
- **THEN** the page shows no trials section and no placeholder for one

### Requirement: A long list of trials opens with the furthest
When a claim has more than five trials, the claim page SHALL show the first five and SHALL keep the rest reachable on the same page without loading anything.

#### Scenario: Claim with thirty-three trials
- **WHEN** a reader opens a claim with thirty-three trials
- **THEN** five are shown, furthest phase first, and the other twenty-eight open on request

#### Scenario: Posted results among the trials not shown
- **WHEN** three of the twenty-eight trials not shown have posted results
- **THEN** the control that opens them says that three have results posted

### Requirement: The claim page counts its trials
A claim page for a claim with at least one trial SHALL state, among its facts, how many trials are on record and the largest number of participants any of them states, with whether that number is actual or planned. The statement SHALL be a count and SHALL NOT add participants across trials.

#### Scenario: Three trials, the largest of 1,200
- **WHEN** a claim has three trials and the largest states 1,200 actual participants
- **THEN** the page states three trials on record and the largest with 1,200 participants

#### Scenario: Trials that state no number
- **WHEN** none of a claim's trials states a number of participants
- **THEN** the page states the number of trials and no size

### Requirement: Trial facts are worded without a verdict
The site SHALL word each trial fact code itself and SHALL fail the build on a code it has no wording for. It SHALL show a posted result as the registry's numbers and SHALL NOT label an outcome as met, missed, significant, successful or failed, nor a trial as having worked. The trials section SHALL say that the numbers are as posted by the trial's sponsor to the registry.

#### Scenario: Posted comparison with a p value
- **WHEN** a trial's posted primary outcome carries a comparison with the p value 0.03
- **THEN** the page shows the group values and "p = 0.03" with the method, and no word on whether the outcome was met

#### Scenario: Fact code without site wording
- **WHEN** the export carries a masking code the site has no wording for
- **THEN** the site build fails and names the code

#### Scenario: Wording with a verdict
- **WHEN** the site is built and the wording for a trial fact contains "successful"
- **THEN** the build fails and quotes the wording

### Requirement: Trial facts show when their record was read
Each trial's entry SHALL show the date its registry record was read, and the trials section SHALL say that the facts are a selection from the record and link to the record for the whole of it.

#### Scenario: Record read on 3 October 2026
- **WHEN** a trial's facts were read from a record fetched on 3 October 2026
- **THEN** the trial's entry shows that date

### Requirement: A trial is not presented as open to join
The trials section SHALL NOT show where a trial takes place, whom to contact, who may take part, or that a trial is recruiting. A trial under way SHALL be worded as under way.

#### Scenario: Trial the registry shows as recruiting
- **WHEN** a claim's trial is recruiting in the registry
- **THEN** its entry reads that the trial is under way and shows no location, contact or eligibility

### Requirement: Papers are listed apart from trial records
A claim page SHALL list matched papers under a heading of their own and SHALL NOT describe a paper as a trial registry record or count it among registry records.

#### Scenario: Claim with one matched paper and no trial
- **WHEN** a reader opens a claim whose only approved match is a paper
- **THEN** the paper is listed under the papers heading and the page says no trial record matched

### Requirement: Confidence is shown with an event scored below certain
An evidence event whose confidence is below 1 SHALL show that confidence on the claim page in the words and bands the site uses for matches. An event with a confidence of 1 SHALL show none.

#### Scenario: Follow-up paper scored 0.6
- **WHEN** a claim page shows a follow-up paper event with a confidence of 0.6
- **THEN** the event shows "Medium match · 60%"

#### Scenario: Trial event read from a registry record
- **WHEN** a claim page shows a trial registered event with a confidence of 1
- **THEN** the event shows no confidence
