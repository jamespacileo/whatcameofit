# Spec Delta

## MODIFIED Requirements

### Requirement: Claim identity
A claim SHALL represent exactly one intervention for one indication. Its intervention SHALL be a shared intervention record, and its indication SHALL be a shared condition record whenever the claim's condition has an approved exact term, with the indication's text kept as the label a reader sees. News articles about the same intervention and indication SHALL attach to the same claim, whatever their publication date. A trial's narrower population, such as one stage, one line of treatment or one marker, SHALL NOT make a separate claim when the trial's condition descriptor is the claim's.

#### Scenario: Later article about an existing claim
- **WHEN** an operator adds a 2021 article about an intervention and indication that already have a claim from a 2018 article
- **THEN** the article is attached to the existing claim and no new claim is created

#### Scenario: Same intervention, different indication
- **WHEN** an operator adds a claim for an intervention that already has a claim for a different indication
- **THEN** a separate claim is created

#### Scenario: A trial in a narrower population
- **WHEN** a trial filed under the descriptor for breast neoplasms enrols only people with HER2-positive metastatic disease, and a claim exists for its tested intervention and breast neoplasms
- **THEN** the trial is a candidate for that claim and no second claim is made for the narrower population

### Requirement: No duplicate claims
Every claim SHALL record its intervention and its indication. The system SHALL refuse a new claim that points to the same intervention record and the same condition record as any claim that has not been merged into another, archived or not. For a claim with no condition record, the system SHALL refuse a new claim whose indication equals that of an existing claim and whose intervention equals that claim's intervention by name or by any synonym, ignoring letter case and spacing. The refusal SHALL name the existing claim.

#### Scenario: Second claim for the same intervention and indication
- **WHEN** an operator adds a claim for an intervention and indication that already have a claim
- **THEN** the claim is not created and the operator is told the slug of the existing claim

#### Scenario: Compound known under another name
- **WHEN** an existing claim's intervention has the synonym "TRG-035" and an operator adds a claim for "trg-035" with the same indication
- **THEN** the claim is not created

#### Scenario: Same records, indication worded differently
- **WHEN** a claim exists for intervention record X and the condition record for breast neoplasms, worded "breast cancer", and a new claim is proposed for X and the same condition record, worded "cancer of the breast"
- **THEN** the claim is not created and the existing claim is named

#### Scenario: An archived claim holds the pair
- **WHEN** the only claim for a pair of records is archived and not merged
- **THEN** a new claim for that pair is refused, naming the archived claim, so the operator unarchives it instead
