## ADDED Requirements

### Requirement: Saved checks preserve search limitations
A recently checked entry with no trial candidate SHALL preserve the generated answer's distinction between a registry search with no matching record and content from which a treatment could not be identified. Older entries without that distinction SHALL use neutral wording about no saved trial match. The additional limitation SHALL remain in browser-local storage alongside the existing answer; no article text or screenshot SHALL be retained for this purpose.

#### Scenario: Registry not searched
- **WHEN** a check could not identify a treatment and condition
- **THEN** its recent entry says that the registry was not searched, without claiming no record was found

#### Scenario: Registry searched without a match
- **WHEN** a check searched the registry but found no matching trial record
- **THEN** its recent entry preserves that outcome and the limitation that other records may exist

#### Scenario: Older entry
- **WHEN** an existing entry has no saved limitation
- **THEN** it says no trial match is saved and offers to open the original page
