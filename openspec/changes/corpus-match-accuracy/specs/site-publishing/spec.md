# Spec Delta

## ADDED Requirements

### Requirement: No-trial wording does not imply a human study
Status explanations, topic summaries and guide text for `no_trial_found` SHALL describe the absence of a matched trial record without asserting a study in people. Confirmed first-report evidence SHALL remain separately visible where available. `preclinical_only` explanations SHALL describe confirmed laboratory or animal evidence.

#### Scenario: Claim has an unknown first-report stage
- **WHEN** a claim with no approved trial and no confirmed evidence stage is displayed or counted in a topic summary
- **THEN** its no-trial wording does not say it was studied in people or only in the laboratory
