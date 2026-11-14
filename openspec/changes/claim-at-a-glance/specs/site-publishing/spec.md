# Spec Delta

## ADDED Requirements

### Requirement: A claim page answers fixed questions from its records
Every claim page SHALL show a section, "The record in brief", of at most six fixed questions, each with a short answer. An answer SHALL be fixed wording filled only with counts, sizes, dates and names from the records the page shows, or from a reading the export carries. No person SHALL write an answer, and no model SHALL write the words of one.

#### Scenario: Claim with trials
- **WHEN** a reader opens a claim with 3 trials on record, the largest stating 135 participants
- **THEN** the section answers "In 3 trials. 135 people in the largest", and the answer does not begin with "Yes"

#### Scenario: Comparison group
- **WHEN** 1 of the claim's 3 trials names a sham comparator and the claim's approach is a device
- **THEN** the section asks whether it was compared with a dummy device and answers that one record names a dummy device, and the opened answer says the other two records name no comparison

#### Scenario: What the largest trial measured
- **WHEN** the largest trial's main measure has a measure reading of symptom score and a follow-up reading of 4 weeks
- **THEN** the section answers with the site's fixed phrase for a symptom score, worded as a change when the registry's title names a change, and "over 4 weeks"

#### Scenario: Measure with no reading
- **WHEN** the largest trial's main measure has no stored reading
- **THEN** the answer is the registry's title for the measure in quotation marks, and the opened answer says it is in the registry's words

#### Scenario: Results posted
- **WHEN** all 3 of the claim's trials have results posted, the latest on 30 June 2026
- **THEN** the section says results were posted by all 3 trials and gives that date, and a link under the answer, shown without opening it, leads to the trials' posted results on the page

#### Scenario: Trial with no stated enrolment
- **WHEN** no trial of the claim states how many participants it enrolled
- **THEN** the answer about testing in people gives the number of trials and no size

### Requirement: Each question has one fixed place
The questions SHALL be shown in a fixed order in two groups: how the treatment was tested, then where the records stand now. A question's place SHALL NOT depend on its answer. A question that has nothing to ask about, because the claim has no trial, SHALL be left out, and the others SHALL keep their order. An answer that a kind of record is absent SHALL say "None on record" in the question's own place, with the date of the last record of that kind where the rule has one. No heading, mark, colour or order SHALL say that an answer counts for or against the treatment. No answer SHALL say why a record is absent, predict, advise, or say that a trial is open to participants.

#### Scenario: Same questions, opposite answers
- **WHEN** one claim has a trial under way and an approval, and another has neither
- **THEN** both pages show "A trial under way?" and "Approved by a regulator?" in the same group and the same order

#### Scenario: No trial under way
- **WHEN** a claim has trials on record and none is under way
- **THEN** the answer is "None on record" with the date the last one completed

#### Scenario: A trial under way
- **WHEN** 2 of a claim's trials are under way
- **THEN** the answer says 2 are under way, and does not say a trial is recruiting or open to participants

#### Scenario: Approved claim
- **WHEN** a reader opens a claim whose status is Approved
- **THEN** the answer names the regulator and the date of the approval and says, without being opened, that an approval is not advice to take a treatment

#### Scenario: Approval entered by hand
- **WHEN** the approval's record names no regulator as its source
- **THEN** the answer gives the date of the approval and the same caution, and names no regulator

#### Scenario: Claim with no trial on record
- **WHEN** a reader opens a claim with no trial on record
- **THEN** the section says no trial in people is on record, says what the first report was about, answers the approval question, and has no question about a comparison, a measure, posted results or a trial under way

#### Scenario: Wording with a verdict
- **WHEN** the site is built and a question, an answer or a group name contains the word "abandoned"
- **THEN** the build fails and quotes the wording

### Requirement: Every answer shows the record it was read from
Each answer SHALL open to show the record it was read from as a link, what was read from it, whether it was read directly from the record or by a model, and the date the record was read. An answer read by a model SHALL also show the exact words it was read from and how sure the reading is, as a word and a percentage. An answer that counts trials SHALL link to them on the page. The section SHALL say that its answers are read from the records on the page, that they describe the records and not the treatment, and that they are not advice.

#### Scenario: Answer read directly
- **WHEN** a reader opens the answer about a comparison group
- **THEN** it names the trial by its registry identifier as a link, gives the design as the registry states it, and gives the date the record was read

#### Scenario: Answer read by a model
- **WHEN** a reader opens an answer that rests on a reading
- **THEN** it shows the words the reading was read from in quotation marks, says a model read them and that they were checked against the record, and says how sure the reading is

#### Scenario: Reading the model is certain of
- **WHEN** a reading's confidence is 1
- **THEN** the opened answer says how sure the reading is as 99%, never 100%

#### Scenario: Every answer opens to something
- **WHEN** a reader opens any answer in the section
- **THEN** it shows at least the record or records it was read from and the date they were read

#### Scenario: Without scripting
- **WHEN** a reader opens a claim page with scripting turned off
- **THEN** every answer can still be opened

#### Scenario: Narrow screen
- **WHEN** a reader opens a claim page on a screen 320 pixels wide
- **THEN** each question is above its answer, every row and every link in an opened answer is at least 44 pixels tall, and the page is not widened

### Requirement: The brief carries no result values
The section SHALL NOT show a trial's posted result values or a posted comparison. The answer about what the largest trial measured SHALL link to that trial's entry on the page, where its posted results are.

#### Scenario: Largest trial with posted values
- **WHEN** the largest trial has posted a value for each of three groups and a p value
- **THEN** the section shows none of those numbers, and the opened answer links to the trial's entry

### Requirement: The digest says when trials state no phase
When a claim's status is Trial registered and it has trials on record, the digest panel SHALL say, after what the status means, how many trials are on record, how many of them have finished, and that the registry gives none a phase.

#### Scenario: Three trials with no phase
- **WHEN** a reader opens a claim whose status is Trial registered and which has 3 trials on record, none stating a phase
- **THEN** the digest says 3 trials are on record and all have finished, and that the registry gives none a phase

#### Scenario: Status with a phase
- **WHEN** a reader opens a claim whose status is Phase 2 trial
- **THEN** the digest has no such sentence

## MODIFIED Requirements

### Requirement: The claim page counts its trials
A claim page for a claim with at least one trial SHALL state, in "The record in brief", how many trials are on record and the largest number of participants any of them states, with whether that number is actual or planned when the answer is opened. The statement SHALL be a count and SHALL NOT add participants across trials. The facts under the digest SHALL NOT repeat it.

#### Scenario: Three trials, the largest of 1,200
- **WHEN** a claim has three trials and the largest states 1,200 actual participants
- **THEN** the section states three trials on record and 1,200 people in the largest, and the facts under the digest do not

#### Scenario: Trials that state no number
- **WHEN** none of a claim's trials states a number of participants
- **THEN** the section states the number of trials and no size
