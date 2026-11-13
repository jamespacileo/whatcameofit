# Spec Delta

## MODIFIED Requirements

### Requirement: Drafts need confirmation
A draft produced by extraction SHALL be approved by rule when its output passes validation and it duplicates no existing claim. A draft that fails validation SHALL be rejected by rule, kept, and listed for the operator. The operator SHALL be able to edit any field of a claim after it is published and to archive it.

#### Scenario: Valid draft
- **WHEN** extraction produces a draft that passes validation and duplicates no claim
- **THEN** the draft is approved by rule and appears on the site after the next export

#### Scenario: Unapproved draft
- **WHEN** extraction produces a draft that fails validation, and no operator approves it
- **THEN** it is rejected by rule, kept, and does not appear on the public site

#### Scenario: Edited draft
- **WHEN** an operator corrects the headline of a rejected draft and approves it
- **THEN** the claim carries the corrected headline

#### Scenario: Edited claim
- **WHEN** an operator corrects the headline of a published claim
- **THEN** the claim carries the corrected headline after the next export
