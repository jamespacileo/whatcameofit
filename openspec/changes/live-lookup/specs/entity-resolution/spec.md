# Spec Delta

## ADDED Requirements

### Requirement: Development codes come from a substance registry
Before the trial registry is searched for an intervention, the system SHALL look the intervention's name and every synonym up in a substance registry whose terms are recorded. When they lead to exactly one substance, the system SHALL keep that substance's record as fetched, with its source, its identifier and the fetch time, and the names the registry marks as codes for it, leaving out any code that is already one of the intervention's names. Each code SHALL be searched for in the trial registry like a search phrase, within the claim's indication only, and SHALL be named in the question put to the match scoring. A code SHALL NOT be stored or shown as a name of the intervention. No model SHALL supply a code, and no code SHALL be taken from a substance found by a loose match. A substance and the forms the registry files apart from it, each named by the substance's name followed by further whole words or a hyphenated suffix, SHALL count as that one substance. When the names lead to no substance, or to more than one, the system SHALL keep no code and SHALL say which of the two it was. A later run SHALL replace what was kept, and SHALL remove it when the registry no longer lists the names under one substance.

#### Scenario: Trial filed under a development code
- **WHEN** the substance registry lists an intervention's name under one substance with a code, and the trial registry holds a trial under that code within the claim's indication
- **THEN** the code is kept with the substance's record, the trial is stored as a candidate match, and the intervention's synonyms and search phrases are unchanged

#### Scenario: Intervention the substance registry does not list
- **WHEN** the substance registry lists no substance under any of the intervention's names
- **THEN** no code is kept, the command says that the registry does not list it, and the trial registry is searched as before

#### Scenario: Names listed under more than one substance
- **WHEN** the intervention's name leads to one substance and a synonym to another
- **THEN** no code is kept and the command names the substances found

#### Scenario: A brand listed under a substance and its salt
- **WHEN** the substances found are one substance and its forms, each form's name being the substance's name followed by further whole words or a hyphenated suffix (imatinib and imatinib mesylate, dostarlimab and dostarlimab-gxly)
- **THEN** they count as that one substance, its record and its codes are kept, and its name is searched in the trial registry as a name of the intervention
