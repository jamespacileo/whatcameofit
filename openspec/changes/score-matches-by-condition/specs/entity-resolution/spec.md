# Spec Delta

## ADDED Requirements

### Requirement: Matches are scored for the claim's indication
A candidate trial match SHALL be scored on whether the record is a trial of the claim's intervention for the claim's indication. A record of the same intervention for another indication SHALL score lower than one for the claim's indication and SHALL be shown to the reviewer as being for another indication.

#### Scenario: Same drug, another condition
- **WHEN** a claim is about a vaccine for melanoma and the registry holds a trial of that vaccine for lung cancer
- **THEN** the lung cancer trial scores below the melanoma trials and is labelled as another indication

#### Scenario: Laboratory compound with unrelated trials
- **WHEN** an animal study used a compound that has registered trials only in unrelated diseases
- **THEN** none of those trials scores as a match for the claim

### Requirement: Broad names are searched within the indication
When the registries are searched for a claim, the search SHALL be narrowed by the claim's indication, so that a broad intervention name returns trials for that condition.

#### Scenario: Broad intervention name
- **WHEN** the intervention is "CAR-T cell therapy" and the indication is stiff person syndrome
- **THEN** the search returns trials of CAR-T cell therapy in stiff person syndrome, not every CAR-T trial
