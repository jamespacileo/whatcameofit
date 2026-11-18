# Spec Delta

## MODIFIED Requirements

### Requirement: Status explanation
Every derived status SHALL come with the list of evidence events that produced it, and the list SHALL hold only the events that decide the status. For trial registered it SHALL hold the registered event of each standing trial. For a phase status it SHALL hold, for each standing trial at the furthest started phase, its registered event and the event that shows it started: its started event, or its completed event when it has no approved started event. Explanations of approved, retracted, failed and terminated statuses are unchanged. A status reached with no trial SHALL have an empty list.

#### Scenario: Phase 2 claim
- **WHEN** a claim's status is Phase 2 because of one trial that has registered, started, completed and results-posted events
- **THEN** the explanation lists that trial's registered and started events and no other

#### Scenario: Trial registered with three trials
- **WHEN** a claim's status is trial registered and it has three standing trials, each with registered, started, completed and results-posted events
- **THEN** the explanation lists the three registered events and no other

#### Scenario: Trial known to have started only from its completion
- **WHEN** a claim's status is Phase 2 because of one trial with approved registered and completed events and no approved started event
- **THEN** the explanation lists that trial's registered and completed events

#### Scenario: Earlier-phase trial beside the deciding one
- **WHEN** a claim has a started Phase 1 trial and a started Phase 3 trial
- **THEN** the explanation lists only the Phase 3 trial's registered and started events

#### Scenario: No trial found
- **WHEN** a claim's status is preclinical only
- **THEN** the explanation lists no event
