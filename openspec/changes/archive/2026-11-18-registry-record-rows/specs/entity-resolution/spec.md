# Spec Delta

## ADDED Requirements

### Requirement: A trial match keeps its record field by field
Whenever a trial match's one-line summary is written, the pipeline SHALL also keep the record's title, conditions and interventions as the registry wrote them, its phases and state as the codes the trial facts use, and its size as the trial facts read it. A registry state that recruits SHALL be kept as "under_way". A match to anything other than a trial registry record SHALL keep no fields. A command SHALL read the fields of every shown trial match stored before they were kept, and SHALL name and exit 1 for any the registry no longer answers for, leaving its fields empty.

#### Scenario: Candidate found by a registry search
- **WHEN** a search returns a recruiting Phase 1/Phase 2 trial for a claim
- **THEN** its match keeps the title, conditions and interventions, the phases "phase_1" and "phase_2", and the state "under_way"

#### Scenario: Match stored before the fields were kept
- **WHEN** the operator runs `thenwhat entity record-facts` and one stored match's trial is no longer in the registry
- **THEN** every other shown trial match has its fields, and the command names that trial and exits 1

### Requirement: The export says the score a match needs to be approved by rule
The export SHALL carry the score at or above which a registry match is approved by rule, or none when that rule is off, so the site can say what a possible record lacks.

#### Scenario: Rule on at 0.8
- **WHEN** the export is built with approval by rule at 0.8
- **THEN** the export's `match_accept_above` is 0.8, and it is null when the rule is off
