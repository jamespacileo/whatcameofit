# Spec Delta

## ADDED Requirements

### Requirement: A claim page answers fixed questions from its records
Every claim page SHALL show a section, "The record in brief", of fixed questions, each with a short answer. An answer SHALL be fixed wording filled only with counts, sizes, dates and names taken from the trials, papers and regulatory records the page shows, or from a reading the export carries. Which questions appear SHALL be decided by rule from those records. A question whose answer the records do not give SHALL be absent, with nothing in its place. No person SHALL write an answer, and no model SHALL write the words of one.

#### Scenario: Claim with completed trials
- **WHEN** a reader opens a claim with 3 trials on record
- **THEN** the section asks whether it was tested in people and answers that it was, in 3 trials

#### Scenario: Sizes of the trials
- **WHEN** the claim's trials state enrolments of 135, 34 and 31
- **THEN** the section says the largest trial enrolled 135 people and the others 34 and 31

#### Scenario: Many trials
- **WHEN** the claim has 12 trials that state their enrolment
- **THEN** the section gives the largest and the lowest and highest of the others, and does not list every size

#### Scenario: Comparison group
- **WHEN** 1 of the claim's 3 trials names a sham comparator
- **THEN** the section asks, in plain words, whether it was compared with a dummy device and answers that it was, in 1 of 3 trials

#### Scenario: Results posted
- **WHEN** all 3 of the claim's trials have results posted to the registry
- **THEN** the section says results were posted by all 3 trials

#### Scenario: Trial with no stated enrolment
- **WHEN** no trial of the claim states how many participants it enrolled
- **THEN** the section has no question about how many people

#### Scenario: Claim with no trial on record
- **WHEN** a reader opens a claim with no trial on record
- **THEN** the section says no trial in people is on record and still answers the questions its papers and first report allow

### Requirement: Answers are grouped by kind of fact
The questions SHALL be shown in three groups, in this order: how the treatment was tested, what was posted, and what the records do not cover. The third group SHALL hold only absences: an answer there says that a kind of record is not on record, and where the rule has one, the date of the last record of that kind. A group with no question SHALL be left out. A question's group SHALL depend only on what kind of fact it is, never on what a result was. No heading, mark, colour or order SHALL say that an answer counts for or against the treatment. No answer SHALL say why a record is absent, predict, advise, or say that a trial is open to participants.

#### Scenario: No trial under way
- **WHEN** a claim has trials on record and none is under way
- **THEN** the third group says none is on record as under way and gives the date the last one completed

#### Scenario: A trial under way
- **WHEN** 2 of a claim's trials are under way
- **THEN** the first group says 2 trials are under way, and no answer says a trial is recruiting or open to participants

#### Scenario: Approved claim
- **WHEN** a reader opens a claim whose status is Approved
- **THEN** the second group says a regulator has recorded an approval, with its date, and the opened answer says an approval is not advice to take a treatment

#### Scenario: Claim that is not approved
- **WHEN** a reader opens a claim with no approval on record
- **THEN** the third group says no approval by a regulator is on record

#### Scenario: Nothing absent by rule
- **WHEN** no absence rule applies to a claim
- **THEN** the third group is left out

#### Scenario: Same question, opposite result
- **WHEN** two claims differ only in which group of a trial had the larger posted change
- **THEN** both pages show the same questions in the same groups and order

#### Scenario: Wording with a verdict
- **WHEN** the site is built and a question, an answer or a group name contains the word "abandoned"
- **THEN** the build fails and quotes the wording

### Requirement: Every answer shows the record it was read from
Each answer SHALL open to show the record it was read from as a link, what was read from it, whether it was read by rule or by a model, and the date the record was read. An answer read by a model SHALL also show the exact words it was read from and how sure the reading is, as a word and a percentage. An answer that counts trials or papers SHALL link to them on the page. The section SHALL say, in one line, that it is about the records and not the treatment, and is not advice.

#### Scenario: Answer read by rule
- **WHEN** a reader opens the answer about a comparison group
- **THEN** it names the trial by its registry identifier as a link, gives the design as the registry states it, says it was read by rule, and gives the date the record was read

#### Scenario: Answer read by a model
- **WHEN** a reader opens an answer that rests on a reading
- **THEN** it shows the words the reading was read from in quotation marks, says it was read by a model and that the words were checked against the record, and gives how sure the reading is

#### Scenario: Without scripting
- **WHEN** a reader opens a claim page with scripting turned off
- **THEN** every answer can still be opened

#### Scenario: Narrow screen
- **WHEN** a reader opens a claim page on a screen 320 pixels wide
- **THEN** each question is above its answer, each row is at least 44 pixels tall, and the page is not widened

### Requirement: Posted results are shown only inside an opened answer
The section SHALL show a trial's posted result values only inside the opened answer about what that trial measured, one line for each group, at the size of body text, with what the numbers are and what a lower number means stated in words by rule. A closed answer SHALL NOT carry a result value. No colour, size, word or order SHALL say how a trial turned out.

#### Scenario: Largest trial with posted values
- **WHEN** a reader opens the answer about what the largest trial measured, and that trial posted one value for each of three groups
- **THEN** the three groups are listed with their values and how many were analysed, at body size, and the closed answer names only the measure

#### Scenario: Outcome posted in several rows
- **WHEN** the largest trial's main measure was posted as several rows of values for each group
- **THEN** the opened answer says so and links to the registry record, and shows no values

#### Scenario: Comparison posted
- **WHEN** the trial's record gives a p value for a comparison of two groups
- **THEN** the opened answer gives it as the record states it, names the two groups, and links to the guide entry that explains it
