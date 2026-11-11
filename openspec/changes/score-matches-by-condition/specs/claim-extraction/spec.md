# Spec Delta

## ADDED Requirements

### Requirement: Other names are names
Extraction SHALL record as another name of the intervention only a name: a brand, a code or a generic name. A description the model returns as a name, such as "the drug" or "a one-time treatment", SHALL NOT be recorded.

#### Scenario: Article that only describes the intervention
- **WHEN** the model returns "EX-1", "the drug" and "experimental antibody jab" as other names
- **THEN** only "EX-1" is recorded

### Requirement: Preparing many claims
An operator SHALL be able to have unread articles read, registries searched and approved matches fetched for many claims with one command, several claims at a time. A step that fails SHALL be reported with its claim, and the claim's other steps SHALL still run. The command SHALL approve nothing and SHALL say how long each step took.

#### Scenario: Article that cannot be read
- **WHEN** one of a claim's articles cannot be read
- **THEN** the failure is reported and the claim is still searched
