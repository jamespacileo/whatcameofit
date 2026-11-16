## ADDED Requirements

### Requirement: Optional substance enrichment uses shorter network waits
GSRS development-code requests SHALL default to two attempts with a five-second network inactivity timeout per phase. They SHALL retain the existing contact client, source pacing, thirty-day successful-response cache and stated retry delay. Other source clients SHALL retain their existing default waits and attempt counts.

#### Scenario: Substance service asks for a longer delay
- **WHEN** the first response asks the client to wait longer than five seconds before retrying
- **THEN** the second attempt is made no sooner than that stated delay
- **AND** the timeout is not presented as a whole-operation deadline; shared pacing and separate successful requests can also extend elapsed time

### Requirement: Optional substance failures remain explicit and recoverable
An exhausted GSRS lookup SHALL remain an explicit source error, not an empty successful listing, and SHALL NOT cache a failure. A later lookup SHALL be able to recover through the ordinary successful-response path.

#### Scenario: Optional substance service does not answer
- **WHEN** both attempts time out while resolving a substance name
- **THEN** the optional lookup reports its refusal after those two attempts, records no empty success, and lets normal preparation continue with its existing warning

#### Scenario: Substance service recovers
- **WHEN** the failed lookup is asked again and the source now answers successfully
- **THEN** the source is contacted again and only the successful response becomes reusable


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
