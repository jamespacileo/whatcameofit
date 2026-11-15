## Purpose

Associates automatic article and post lookups with existing knowledge cards only when they describe the same claim.

## ADDED Requirements

### Requirement: Trial matching preserves explicit intervention scope
Both lookup and private-pipeline scoring SHALL receive intervention descriptions and arm membership from the fetched registry record. Explicit route, formulation, stereoisomer and regimen conflicts SHALL mean `not_a_match`. Separate component arms SHALL NOT establish a complete regimen. Missing or truncated evidence SHALL retain uncertainty about explicit restrictions.

#### Scenario: Injected treatment against an inhaled claim
- **GIVEN** the claim explicitly concerns inhaled treatment and a record describes subcutaneous injection
- **WHEN** that trial is scored
- **THEN** the description is available to the scorer and the conflicting route is not a full match

#### Scenario: Separate component arms
- **GIVEN** the claim concerns A plus B while the registry describes an A-only arm and a B-only arm
- **WHEN** that trial is scored
- **THEN** arm membership is available and the two names alone cannot establish a combination match

#### Scenario: Long duplicate title
- **GIVEN** an unusually long official title and short intervention/arm descriptions
- **WHEN** the existing input limit is applied
- **THEN** the short route and arm evidence comes before the duplicate title and shortened content is marked

#### Scenario: Compatibility is absent
- **GIVEN** an explicit route restriction and a missing or truncated description that does not establish the route
- **WHEN** the record is scored
- **THEN** the restriction remains uncertain rather than becoming a confident match

### Requirement: Detailed trial inputs remain bounded
The existing 1,500-character record limit, request counts and source caches SHALL remain. Shortened content SHALL be marked and obsolete completed answers SHALL be invalidated.

#### Scenario: Record exceeds the input limit
- **WHEN** descriptions and arm details exceed the record limit
- **THEN** the shortened input remains within 1,500 characters, carries a truncation marker and adds no request

### Requirement: Trial matching respects explicit patient restrictions
Lookup and private-pipeline scoring SHALL treat explicit patient populations and treatment settings as part of the indication. An incompatible setting SHALL be read as `other_indication`, even for a mentioned trial. Missing compatibility SHALL retain uncertainty; a broad claim SHALL NOT gain an unstated restriction. Existing bounded calls and source caches SHALL remain; obsolete completed answers SHALL be invalidated.

#### Scenario: Article links a separate first-line trial
- **GIVEN** the claim concerns previously treated metastatic pancreatic cancer and a linked record concerns first-line treatment
- **WHEN** candidates are scored
- **THEN** that record is not a full match solely because it tests the same drug and is explicitly linked

#### Scenario: Compatible prior-treatment study
- **GIVEN** the claim and record both concern the named intervention in previously treated metastatic pancreatic cancer
- **WHEN** the candidate is scored
- **THEN** it remains eligible as a match

#### Scenario: Broad condition is not silently narrowed
- **GIVEN** a claim about metastatic pancreatic cancer with no prior-treatment restriction
- **WHEN** first-line and previously treated records are scored
- **THEN** neither is excluded solely because of an unstated prior-treatment restriction

#### Scenario: Prior adjuvant treatment is compatible
- **GIVEN** the claim describes previous adjuvant therapy for resected disease and the record explicitly permits it for first-line metastatic treatment
- **WHEN** the candidate is scored
- **THEN** prior treatment alone does not make the settings incompatible

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
