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

### Requirement: A brand the substance registry does not list is looked up under its ingredient
When the substance registry lists no substance under any of an intervention's names, the system SHALL ask a second source, one that files brand names under their ingredients and whose terms are recorded, about the same names. The second source SHALL NOT be asked when the substance registry lists the names under one substance or under more than one. A brand SHALL be resolved only when the second source lists one of the names as a brand, equal to it ignoring letter case and runs of spaces and nothing else, and the brands found lead to exactly one ingredient, counting an ingredient and its forms as one by the same rule as for the substance registry. The system SHALL then keep that ingredient's record as fetched, with the second source's name, the ingredient's identifier there and the fetch time, in place of a substance's record, and SHALL keep no code from it. The ingredient's name SHALL be searched in the trial registry as a name of the intervention, as a substance's name is, and SHALL NOT be stored or shown as a name of the intervention. A brand of more than one ingredient, and a name the second source does not list as a brand, SHALL keep nothing. No model SHALL supply an ingredient and no loose match SHALL be taken. The command SHALL say which source answered, and when neither listed the names SHALL say so of both. A later run SHALL replace what was kept, and SHALL remove it when neither source lists the names under one substance any longer.

#### Scenario: Brand the substance registry does not list, of one ingredient
- **WHEN** the substance registry lists none of an intervention's names and the second source lists its name as a brand of one ingredient
- **THEN** the ingredient's record is kept with the second source's name, its identifier and the fetch time, no code is kept, the ingredient's name is searched in the trial registry as a name, the intervention's synonyms and search phrases are unchanged, and the command names the second source as the one that answered

#### Scenario: The substance registry lists the intervention
- **WHEN** the substance registry lists the intervention's names under one substance, or under more than one
- **THEN** the second source is not asked

#### Scenario: Brand of more than one ingredient
- **WHEN** the substance registry lists none of the names and the second source lists the brand under two ingredients, neither a form of the other
- **THEN** nothing is kept and the command names the ingredients found

#### Scenario: Brand neither source lists
- **WHEN** neither the substance registry nor the second source lists any of the names
- **THEN** nothing is kept, the command says that neither lists it, and the trial registry is searched as before
