# Spec Delta

## Purpose

States what a registered trial says of itself (its size, design, sponsor, planned outcomes and posted results), read by fixed rules from the trial's registry record, so that a claim's trials can be compared without opening each record.

## ADDED Requirements

### Requirement: One trial per registry identifier
The export SHALL list, for each published claim, one trial for each registry identifier carried by the claim's approved trial events. Each trial SHALL carry its identifier, its registry's name, a link to its record, its phases and its state. A trial behind only pending or rejected events SHALL NOT be listed.

#### Scenario: Trial with four approved events
- **WHEN** a published claim has four approved events for one trial
- **THEN** the export lists that trial once

#### Scenario: Trial whose events are all pending
- **WHEN** every event of a trial is pending
- **THEN** the export does not list the trial

### Requirement: Facts are read from the registry record by rule
Trial facts SHALL be read by fixed rules from the registry record stored with the trial's approved events, using the record fetched most recently. No model SHALL be asked, and no source SHALL be called to produce them. A fact the record does not state SHALL be absent and SHALL NOT be inferred.

#### Scenario: Record that gives no masking
- **WHEN** a trial's record states no masking
- **THEN** the trial's facts carry no masking and nothing in its place

#### Scenario: Two stored records for one trial
- **WHEN** a trial's registered event stores a record fetched in March and its completed event stores one fetched in October
- **THEN** the facts are read from the October record

#### Scenario: Export with no network
- **WHEN** the export is built on a machine with the database and no network
- **THEN** every trial's facts are present

### Requirement: Facts carry the date their record was read
Each trial's facts SHALL carry the time the registry record they were read from was fetched.

#### Scenario: Record fetched on 3 October 2026
- **WHEN** a trial's facts are read from a record fetched on 3 October 2026
- **THEN** the trial's facts carry that date

### Requirement: A trial with no stored registry record has no facts
A trial whose events were entered by hand, or whose stored payload is not a registry record, SHALL be listed with its identifier, link, phases and state only.

#### Scenario: Trial entered by hand from a registry with no client
- **WHEN** a claim's only trial was entered by hand with an identifier, a phase and a link
- **THEN** the trial is listed with those and carries no facts

### Requirement: Participants
A trial's facts SHALL state the number of participants the record gives and whether the registry marks that number as actual or as planned.

#### Scenario: Completed trial
- **WHEN** a record gives an enrolment of 83 marked actual
- **THEN** the facts state 83 participants, actual

#### Scenario: Trial not yet started
- **WHEN** a record gives an enrolment of 400 marked estimated
- **THEN** the facts state 400 participants, planned

### Requirement: Design
A trial's facts SHALL state, as codes, the kind of study, whether participants were allocated at random, the level of masking, and each kind of comparator among the trial's arms: placebo, sham, active treatment, or no treatment.

#### Scenario: Randomised, double-masked, placebo-controlled trial
- **WHEN** a record states random allocation, double masking and a placebo arm
- **THEN** the facts carry the codes for randomised, double masking and a placebo comparator

#### Scenario: Single-arm trial
- **WHEN** a record has one arm and states no allocation
- **THEN** the facts carry no allocation and no comparator

### Requirement: Who was studied
A trial's facts SHALL state whether the record accepts healthy volunteers and which of the registry's age groups it covers. They SHALL NOT carry eligibility criteria.

#### Scenario: Phase 1 trial in healthy adults
- **WHEN** a record accepts healthy volunteers and covers adults only
- **THEN** the facts state healthy volunteers and the adult age group

### Requirement: Sponsor
A trial's facts SHALL state the lead sponsor's name and its kind as the registry classes it. When the registry classes the lead sponsor as an individual, the facts SHALL state the kind and SHALL NOT state the name.

#### Scenario: Industry sponsor
- **WHEN** a record's lead sponsor is a company the registry classes as industry
- **THEN** the facts state the company's name and the industry kind

#### Scenario: Sponsor who is a person
- **WHEN** a record's lead sponsor is classed as an individual
- **THEN** the facts state that the sponsor is an individual and give no name

### Requirement: Planned primary outcomes
A trial's facts SHALL state up to three of the primary outcomes the record plans, each with its measure and time frame in the registry's words, and the total number the record plans.

#### Scenario: Record with five primary outcomes
- **WHEN** a record plans five primary outcomes
- **THEN** the facts state the first three and a total of five

### Requirement: Reason for stopping
When a record states why the trial was stopped, the trial's facts SHALL carry that statement in the registry's words.

#### Scenario: Terminated trial with a stated reason
- **WHEN** a terminated trial's record states "Sponsor decision"
- **THEN** the facts carry "Sponsor decision"

#### Scenario: Terminated trial with no stated reason
- **WHEN** a terminated trial's record states no reason
- **THEN** the facts carry no reason

### Requirement: Posted results for primary outcomes
When a record holds posted results, the trial's facts SHALL state, for up to three posted primary outcomes: the title, time frame, unit and kind of measure, and for each group its title, the number analysed, the value and any spread or interval. Results for other outcomes SHALL NOT be carried.

#### Scenario: Two-group trial with one primary outcome
- **WHEN** a record posts one primary outcome with a mean and standard deviation for a placebo group and a treatment group of ten each
- **THEN** the facts state the outcome's title and unit and, for each group, ten analysed with its mean and standard deviation

#### Scenario: Record without results
- **WHEN** a record holds no posted results
- **THEN** the facts carry no results

### Requirement: Posted comparisons
For each primary outcome carried, the facts SHALL state each comparison the record posts: the groups compared, the p value and the statistical method as posted, and whether the registry marks the test as one of superiority, non-inferiority or equivalence. A p value SHALL be carried as the registry wrote it.

#### Scenario: Comparison posted as "<0.001"
- **WHEN** a record posts a comparison with the p value "<0.001" by a named method
- **THEN** the facts carry "<0.001" and the method's name

#### Scenario: Outcome with no posted comparison
- **WHEN** a posted primary outcome has no comparison
- **THEN** the facts carry its group values and no comparison

### Requirement: An outcome reported in several rows carries no numbers
When a posted primary outcome reports more than one row of values for each group, the facts SHALL state its title, time frame and the number of rows, and SHALL NOT carry its values.

#### Scenario: Outcome reported at four time points
- **WHEN** a posted primary outcome gives four rows of values for each group
- **THEN** the facts state the outcome's title and four rows, with no values

### Requirement: Sponsor's descriptions of results are not carried
The facts SHALL NOT carry the free-text description a record gives for a results group or for a posted outcome, because that text can state a conclusion.

#### Scenario: Group described as having improved significantly
- **WHEN** a record's results group has a description saying the treatment significantly reduced the measure
- **THEN** the facts carry the group's title and values and none of the description

### Requirement: Trial state does not say whether a trial is recruiting
A trial's state SHALL be one of: not started, under way, completed, suspended, terminated, withdrawn, or unknown. A trial the registry shows as recruiting, enrolling or active SHALL be under way. The facts SHALL NOT carry locations, contacts or any statement that a trial is open to participants.

#### Scenario: Recruiting trial
- **WHEN** a record's overall status is recruiting
- **THEN** the trial's state is under way and the facts carry no location or contact

### Requirement: Trial facts do not change the status
Trial facts SHALL NOT be inputs to a claim's status. A claim's status and the events that explain it SHALL be the same with and without them.

#### Scenario: Posted result with a high p value
- **WHEN** a claim's only trial posts a primary outcome comparison with a p value of 0.6
- **THEN** the claim's status and its explaining events are unchanged
