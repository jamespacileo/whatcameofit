## ADDED Requirements

### Requirement: Candidate-first results
An automatic answer SHALL show its automatic/unreviewed provenance, identified treatment and indication when available, and individual candidate cards before lengthy explanations. Each card SHALL retain its complete linked title, model match confidence, phase and registry state. Missing confidence SHALL remain unavailable; reviewed claims SHALL have no invented score. Icons and colour SHALL support visible labels and SHALL NOT imply treatment effectiveness.

#### Scenario: Image post produces candidates
- **WHEN** a lookup returns one or more candidates
- **THEN** the first card is visible in a 360 by 600 pixel popup using representative long titles, without first expanding or scrolling past explanatory paragraphs

### Requirement: Accessible supporting detail
Source provenance, registry identifiers, match explanations, confidence limitations, OpenAI processing and retention details SHALL remain available through labelled keyboard-operable disclosures. Automatic/unreviewed provenance, cached-result date, lack-of-evidence uncertainty and a short medical limitation SHALL remain visible. The explicit first-use permission screen SHALL continue to identify the recipients and shared content before consent.

#### Scenario: Reader checks a candidate
- **WHEN** the reader opens that card's details
- **THEN** its registry identifier, reason when supplied, and model-confidence limitation are available without leaving the result

#### Scenario: Reader checks sources or privacy
- **WHEN** the reader opens Sources and privacy
- **THEN** full source context, additional search details, OpenAI disclosure and the privacy link are available

#### Scenario: Reused answer or unsuccessful identification
- **WHEN** an earlier answer is reused or no treatment or candidate can be identified
- **THEN** the checked date or uncertainty remains visible without expanding details, and retry remains available
