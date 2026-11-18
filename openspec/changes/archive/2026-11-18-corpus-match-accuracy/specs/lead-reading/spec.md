## ADDED Requirements

### Requirement: Equal names do not establish product identity
For a newly read lead, equal intervention and indication names SHALL identify candidates, not bypass the same-claim decision. This supersedes the name-only join in the active `social-link-backfill` change. The exact name and indication pair SHALL be prioritized within the existing candidate limit. Acceptance thresholds SHALL remain unchanged.

#### Scenario: Equal category names hide different vaccines
- **GIVEN** the read and an existing claim both name COVID-19 vaccine for COVID-19
- **AND** their summaries identify different vaccine products
- **WHEN** the lead is read
- **THEN** the identity decision receives both summaries and the names alone do not join the article

#### Scenario: The same named product is established
- **WHEN** the identity decision meets the existing acceptance thresholds for a candidate
- **THEN** the article is added using existing rules, leaving the reviewed claim unchanged

#### Scenario: Many conditions for the same intervention
- **GIVEN** eight older claims share the intervention name but have different indications
- **WHEN** the read names a ninth claim's intervention and indication
- **THEN** that exact pair is offered within the same eight-candidate limit and still requires the identity decision

### Requirement: Compare bounded identity context
The identity decision SHALL receive each side's summary, capped at 500 characters with truncation marked. No source article text SHALL be added to its log. Its instructions SHALL preserve complete product, route, stereoisomer, regimen, patient-population and treatment-setting identity. Shared category names SHALL NOT establish product equivalence; missing identity detail SHALL preserve uncertainty.

#### Scenario: Long candidate summary
- **WHEN** a candidate's stored summary exceeds 500 characters
- **THEN** the identity prompt receives at most 500 characters with truncation marked
- **AND** missing detail does not justify inferring product equivalence

### Requirement: Unresolved name collisions finish once
When no candidate satisfies the identity decision but an existing claim covers the literal intervention and indication names, the lead SHALL finish as identity unresolved. No article or duplicate claim SHALL be made. The outcome and overlapping claim slug SHALL be recorded and counted in the funnel. An ordinary repeated run SHALL perform no further reading or decision work for that lead.

#### Scenario: Identity was not established
- **WHEN** equal names collide but no candidate passes the identity decision
- **THEN** the lead finishes with identity unresolved and no claim association
- **AND** a subsequent ordinary run does not fetch or read it again

#### Scenario: The equal-name claim is rejected
- **GIVEN** the claim already covering the literal names is rejected
- **WHEN** no other candidate establishes identity
- **THEN** the rejected claim is not offered to the decision and the lead finishes as identity unresolved

#### Scenario: Off-topic business news has a name collision
- **WHEN** business news reaches the identity decision but equal names do not establish the same product
- **THEN** the lead finishes as identity unresolved with the overlapping slug, before the no-claim business-news fallback

### Requirement: Identity work is bounded and accounted for
The change SHALL add at most one same-claim decision for a newly read article that previously used the exact-name shortcut, offering at most the existing eight candidates. It SHALL add no source fetch, extraction call or work for already-tracked URLs. The funnel's reading cost SHALL include incurred treatment-kind and same-claim decisions alongside extraction and vertical decisions.

#### Scenario: A completed read is repeated
- **WHEN** an ordinary reading run is repeated without changed input
- **THEN** no new extraction or identity decision is made for the completed lead
