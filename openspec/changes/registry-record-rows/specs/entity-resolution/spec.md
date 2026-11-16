# Spec Delta

## ADDED Requirements

### Requirement: A trial match keeps its record field by field
Whenever a trial match's one-line summary is written, the pipeline SHALL also keep the record's title, conditions and interventions as the registry wrote them, and its phases and state as the codes the trial facts use. A registry state that recruits SHALL be kept as "under_way". A match to anything other than a trial registry record SHALL keep no fields. A command SHALL read the fields of every shown trial match stored before they were kept, and SHALL name and exit 1 for any the registry no longer answers for, leaving its fields empty.

#### Scenario: Candidate found by a registry search
- **WHEN** a search returns a recruiting Phase 1/Phase 2 trial for a claim
- **THEN** its match keeps the title, conditions and interventions, the phases "phase_1" and "phase_2", and the state "under_way"

#### Scenario: Match stored before the fields were kept
- **WHEN** the operator runs `thenwhat entity record-facts` and one stored match's trial is no longer in the registry
- **THEN** every other shown trial match has its fields, and the command names that trial and exits 1
