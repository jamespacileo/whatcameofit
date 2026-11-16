## ADDED Requirements

### Requirement: Arms in the record's words
Each trial's facts SHALL list the arms its ClinicalTrials.gov record gives, in the record's order, each with its label, its kind (experimental, active comparator, placebo comparator, sham comparator, no intervention, or other) and the names of the interventions it gets, unaltered but for the registry's "<type>: " prefix. A record of another registry SHALL list no arms. The arms SHALL be read from the stored record at export, by rule.

#### Scenario: Placebo-controlled record
- **WHEN** a record lists a "Kudzu" arm of kind active comparator getting "Dietary Supplement: Kudzu" and a "Placebo" arm getting "Dietary Supplement: Placebo"
- **THEN** the facts list both arms in that order, with the interventions "Kudzu" and "Placebo"

### Requirement: Whether the claim's treatment is the arm under test
Each exported trial SHALL say whether the claim's intervention, by its name or a synonym matched as a whole word ignoring case against each arm's interventions and label, is in an experimental arm, only in comparator arms, or cannot be told. With no experimental arm in the record, an active comparator arm counts as the arm under test. No partial or approximate match SHALL count, and nothing SHALL be guessed when no arm names it.

#### Scenario: The claim's drug is only the comparison
- **WHEN** a montelukast claim's trial has an experimental mometasone arm and an active comparator montelukast arm
- **THEN** the trial is marked as having the claim's treatment only as a comparator

#### Scenario: No arm names the treatment
- **WHEN** no arm's interventions or label contain the claim's name or a synonym as a whole word
- **THEN** the trial carries no answer
