# Spec Delta

## ADDED Requirements

### Requirement: Search phrases
For an intervention the article describes without a product name, extraction SHALL give up to three search phrases: the words a registry or a paper would use for it. A search phrase SHALL be kept apart from the intervention's other names and SHALL NOT be shown as a name. A phrase that is only a generic word for a treatment, such as "the device", SHALL NOT be recorded.

#### Scenario: Device with no product name
- **WHEN** an article describes a wrist-worn device that stimulates the median nerve and gives it no name
- **THEN** the draft holds a search phrase such as "median nerve stimulation" and no other name

#### Scenario: Named drug
- **WHEN** an article names a drug by its generic name
- **THEN** the draft may hold no search phrase

### Requirement: People recorded are researchers
Extraction SHALL record a person only when the article names them as carrying out or leading the research. A patient, a relative, a reporter or a commentator SHALL NOT be recorded, by full name or by first name.

#### Scenario: Report featuring a patient
- **WHEN** an article names its reporter, a teenage patient by first name and the professor who led the study
- **THEN** the draft holds one person, the professor

#### Scenario: Article naming no researcher
- **WHEN** an article names only patients
- **THEN** the draft holds no person
