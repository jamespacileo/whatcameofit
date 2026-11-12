# evidence-events Specification

## Purpose
Records dated, sourced facts about a claim drawn from public registries. Evidence events are the only inputs to a claim's status and the only evidence shown publicly.

## Requirements

### Requirement: Event record
An evidence event SHALL have a type, an event date, a source name, a source URL, a summary, a confidence between 0 and 1, the raw payload it was built from, the time that payload was fetched, and a review state. The type SHALL be one of: follow-up paper, trial registered, trial status change, trial results posted, grant awarded, company event, retraction, regulatory decision.

#### Scenario: Event without a source link
- **WHEN** an event is created without a source URL
- **THEN** the event is refused

#### Scenario: Event built from a registry record
- **WHEN** an event is created from a fetched trial record
- **THEN** the event stores that record's unmodified payload and its fetch time

### Requirement: Regulatory decision outcome
Every regulatory decision event SHALL record its outcome, approved or refused. No other type of event SHALL carry an outcome.

#### Scenario: Regulatory decision without an outcome
- **WHEN** a regulatory decision event is created without an outcome
- **THEN** the event is refused

#### Scenario: Refusal recorded
- **WHEN** an operator enters a regulatory decision event with the outcome refused
- **THEN** the event is stored with that outcome and does not make the claim approved

### Requirement: Events come from approved matches
A fetch for a claim SHALL create events only from registry records that an approved entity match points to.

#### Scenario: Pending match
- **WHEN** a fetch runs for a claim whose only trial match is pending
- **THEN** no trial events are created

### Requirement: Trial events from the current record
For each approved trial match, a fetch SHALL create events from the dated fields of the trial's current registry record: one registered event, one status change event for an actual start, one status change event for a current end state (completed, terminated, withdrawn or suspended), and one results posted event when results exist. The fetch SHALL NOT reconstruct earlier states the record no longer shows.

#### Scenario: Completed trial with results
- **WHEN** a fetch runs for a trial that was registered, started, completed and has posted results
- **THEN** four events are created: registered, started, completed and results posted

#### Scenario: Registered trial that has not started
- **WHEN** a fetch runs for a trial whose start date is only anticipated
- **THEN** one registered event is created and no started event

### Requirement: Trial event details
Every trial event SHALL carry the trial's registry identifier and its phase or phases as registered. Every trial status change event SHALL carry the state it reports. Every trial event SHALL record which registry field its event date was taken from.

#### Scenario: Terminated trial without a completion date
- **WHEN** a terminated trial's record has no actual completion date
- **THEN** the terminated event is dated from the record's last update date and says so

### Requirement: Follow-up papers
A paper SHALL become a follow-up paper event only when it cites the claim's origin paper and, in addition, either shares at least one author with the origin paper or names the intervention or one of its synonyms in its title or abstract.

#### Scenario: Citing paper from the same group
- **WHEN** a paper cites the origin paper and shares an author with it
- **THEN** a follow-up paper event is created

#### Scenario: Independent paper naming the intervention
- **WHEN** a paper cites the origin paper, shares no author, and names the intervention in its abstract
- **THEN** a follow-up paper event is created

#### Scenario: Unrelated citing paper
- **WHEN** a paper cites the origin paper, shares no author and does not name the intervention
- **THEN** no event is created

#### Scenario: Claim without an origin paper
- **WHEN** a fetch runs for a claim that has no origin paper
- **THEN** no follow-up paper events are created

### Requirement: Retraction events
A fetch SHALL create a retraction event when the DOI registry holds a retraction notice for the claim's origin paper or for a paper behind one of the claim's follow-up paper events. The event SHALL name the retracted paper.

#### Scenario: Origin paper retracted
- **WHEN** the origin paper's DOI has a retraction notice
- **THEN** a retraction event is created that names the origin paper and is dated from the notice

### Requirement: Manually entered events
An operator SHALL be able to enter an event of any type by giving its date, source URL and summary. A manually entered trial event SHALL also give the trial's registry identifier, its phase and, for a status change, the state. The entered details SHALL be stored as the event's payload and the entry time as its fetch time.

#### Scenario: Regulatory approval entered by hand
- **WHEN** an operator enters a regulatory decision event with a date, a link to the regulator's notice and a summary
- **THEN** the event is stored and is pending review

#### Scenario: Trial in a registry with no client
- **WHEN** an operator enters a trial registered event for a trial listed only in a registry the system has no client for, giving its identifier, phase, date and registry link
- **THEN** the event is stored, is pending review, and counts toward status once approved

#### Scenario: Trial event without an identifier
- **WHEN** an operator enters a trial event without a registry identifier
- **THEN** the event is refused

### Requirement: Initial review state
A new event whose confidence is below the configured threshold SHALL be pending. A new event at or above the threshold SHALL be approved and recorded as approved by rule. Follow-up paper events and manually entered events SHALL always start pending.

#### Scenario: Trial event from an approved match
- **WHEN** a registered event is created from a human-approved trial match with confidence above the threshold
- **THEN** the event is approved and marked as approved by rule

#### Scenario: Follow-up paper
- **WHEN** a follow-up paper event is created
- **THEN** it is pending whatever its confidence

### Requirement: No duplicate events
Fetching a claim again SHALL NOT create a second event for a fact that already has one, and SHALL NOT change the review state of an existing event.

#### Scenario: Second fetch with no registry change
- **WHEN** a claim is fetched twice and the registries have not changed
- **THEN** the second fetch creates no events

#### Scenario: Rejected event found again
- **WHEN** a fetch finds a paper whose follow-up event an operator rejected earlier
- **THEN** the event stays rejected and no new event is created
