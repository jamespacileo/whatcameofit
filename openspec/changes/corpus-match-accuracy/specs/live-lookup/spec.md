## Purpose

Associates automatic article and post lookups with existing knowledge cards only when they describe the same claim.

## ADDED Requirements

### Requirement: Card association preserves claim identity
A live answer SHALL name a tracked card only when its complete intervention and condition match. A single component SHALL NOT establish a combination match. Missing or ambiguous condition information SHALL produce no confirmed card association. Case and whitespace differences and recorded whole-intervention aliases SHALL remain supported without an extra model or source call.

#### Scenario: Same medicine for another condition
- **WHEN** an obesity report names a medicine also tracked for biological ageing
- **THEN** the biological-ageing card is not returned as its tracked claim

#### Scenario: Combination contains a tracked medicine
- **WHEN** a report names a two-medicine regimen and an existing card concerns only one of them
- **THEN** that card is not returned as the same claim, even if a component appears among extracted aliases

#### Scenario: Matching recorded alias
- **WHEN** the complete intervention matches a recorded alias and the same condition is identified
- **THEN** the tracked card is returned without another model call

#### Scenario: Older index lacks condition
- **WHEN** an index entry has names but no explicit condition
- **THEN** name overlap alone cannot confirm a card association

### Requirement: Corrected associations replace saved mistakes
The service and extension SHALL reject saved results produced before the claim-identity correction. Exact tracked source-address mappings SHALL retain their no-model path.

#### Scenario: Previously saved wrong-condition card
- **WHEN** a version-four result contains a name-only card association
- **THEN** the next eligible lookup does not reuse it

### Requirement: Combination readings retain the complete experiment
When a report's main experiment adds one named treatment to another, the reading SHALL retain the complete regimen. Discussion of a component-only comparison arm SHALL NOT by itself shorten that regimen to its newest component. A report explicitly centred on monotherapy SHALL retain that monotherapy. Unrelated roundups and company profiles SHALL remain negative identifications. Both lookup implementations SHALL use equivalent reading instructions and obsolete saved answers SHALL be invalidated.

#### Scenario: Combination trial discusses a component-only result
- **WHEN** a report describes A plus B and also highlights an A-only arm
- **THEN** its main combination is named A plus B

#### Scenario: Main claim is monotherapy
- **WHEN** the report explicitly concerns A alone and mentions an earlier combination as context
- **THEN** A remains the identified treatment
