## ADDED Requirements

### Requirement: Registry searches retain the evidence needed to judge treatment roles
Both ClinicalTrials.gov clients SHALL request study type, intervention descriptions and arm membership, arm types and arm descriptions in name and trial-title search responses. They SHALL preserve existing query, page, pacing and cache bounds and SHALL NOT add individual-record requests solely to obtain those fields.

#### Scenario: Search response is projected to requested fields
- **WHEN** the registry returns only the requested fields for an experimental arm and its comparator
- **THEN** both clients retain their types, intervention membership and descriptions in the same search response

#### Scenario: Search finds expanded access
- **WHEN** a name search returns an expanded-access record
- **THEN** the scorer receives its study type without fetching that record separately

### Requirement: A refused condition has one bounded discovery fallback
When ClinicalTrials.gov explicitly refuses the condition field of a condition-scoped search, the client SHALL try the existing distinct condition-keyword wording once, if available. Both broad-name and search-phrase discovery SHALL use this behavior. The intervention name SHALL remain unchanged and no unscoped search SHALL replace it.

#### Scenario: Long precise condition is refused
- **WHEN** the registry refuses the full condition but accepts the existing keyword wording
- **THEN** the client returns only the bounded candidate set from that condition-scoped fallback, with the treatment name unchanged

### Requirement: Condition fallback preserves discovery limits and clinical scope
The candidate limit and source pacing SHALL remain unchanged. The claim's complete indication SHALL remain the input to match scoring; discovery wording SHALL NOT replace it.

#### Scenario: Fallback remains too broad
- **WHEN** the accepted fallback returns more than one hundred trials
- **THEN** it contributes no candidates and no further page or broader query is requested

### Requirement: Unusable searches remain explicit refusals
A refused fallback, or an initial refusal with no distinct fallback, SHALL remain an explicit search error rather than an empty successful result. An intervention-field refusal, an unknown-field refusal, or another source error SHALL NOT trigger this fallback.

#### Scenario: No usable condition wording
- **WHEN** the fallback is also refused, or no distinct keyword wording exists
- **THEN** the search refusal is reported and no further query is sent

#### Scenario: Refused treatment or unknown field
- **WHEN** the registry refuses the intervention field or names an unknown field
- **THEN** the error is reported without rewriting the treatment or condition
