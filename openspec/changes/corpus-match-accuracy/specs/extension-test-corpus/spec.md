## ADDED Requirements

### Requirement: Separate trial and knowledge-card evidence
Each audited corpus row SHALL record its trial outcome and knowledge-card identity separately, with UTC time, released build and reading method. A positive trial candidate SHALL NOT make an unrelated card correct. Negative controls, ambiguous claims and inaccessible content SHALL retain truthful outcomes. The native Sheet SHALL preserve unrelated values, formulas, validation and formatting.

#### Scenario: Correct trial with the wrong card
- **WHEN** a released lookup finds the intended trial and links a card about another condition
- **THEN** the row records the card failure and does not receive an overall pass

#### Scenario: Caption and video differ in coverage
- **WHEN** verification reads only a caption or a single frame
- **THEN** the evidence states that limitation rather than claiming full-video verification

### Requirement: Corpus verification reuses proven work
The full-corpus audit SHALL check exact published address mappings before paid lookup, reuse current eligible evidence, and record measured fresh/reused timing and request counts where available. Model or source failures SHALL not be retained as successful empty results. Audit artifacts SHALL contain no copied article text or screenshots.

#### Scenario: Published article already mapped
- **WHEN** an address maps exactly to published claims
- **THEN** its card identity can be checked without another reading-model request
