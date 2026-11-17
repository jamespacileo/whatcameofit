# Spec Delta

## ADDED Requirements

### Requirement: Basis of a rule-set approach on the claim page
The export SHALL carry, for a claim whose approach a rule set, the basis of that approach as codes: the registry intervention type and the number of trials that list it. For any other claim the basis SHALL be empty. A claim page SHALL state the basis beside the approach label, in the site's own wording, and SHALL say nothing about a basis when there is none. The wording SHALL say what the registry lists and SHALL NOT say whether the intervention works or is available.

#### Scenario: Approach set by rule
- **WHEN** a reader opens a claim whose approach drug was set by rule from 3 trials
- **THEN** the page shows the label for drug and states that the registry lists the intervention as a drug in 3 trials

#### Scenario: Approach set by a person
- **WHEN** a reader opens a claim whose approach an operator set
- **THEN** the page shows the approach label and no basis

#### Scenario: Registry type without site wording
- **WHEN** the export carries a basis whose registry type the site has no words for
- **THEN** the site build fails and names the type
