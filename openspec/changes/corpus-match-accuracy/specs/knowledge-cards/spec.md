# Knowledge cards

## ADDED Requirements

### Requirement: Background cards describe the whole intervention
An explicit component of a named combination SHALL NOT be linked or exported as the complete intervention's vocabulary or drug card. Component aliases and registry filing SHALL NOT override this boundary. Whole-regimen aliases SHALL remain candidates. A component's drug-derived target SHALL NOT be exported as if it described the complete regimen. Existing review decisions SHALL remain recorded; the export boundary SHALL suppress incompatible component cards without rewriting decisions or clinical status.

#### Scenario: Model calls one component an exact match
- **GIVEN** a claim for EX-1 plus EX-2 and a candidate term naming EX-1
- **WHEN** vocabulary candidates are gathered from aliases or registry filing
- **THEN** EX-1 is excluded before any paid classification, even if a model would label it exact

#### Scenario: Only one component exists in the drug source
- **GIVEN** a combination with a recorded component alias and only that component listed in the drug source
- **WHEN** drug linking runs
- **THEN** the component does not become the whole regimen's drug record

#### Scenario: Old component link was approved
- **GIVEN** an approved intervention or drug link that names a component of the claim's explicit regimen
- **WHEN** a new export is built
- **THEN** the component card and its drug-derived target are omitted, condition cards remain eligible, and the stored review decision is unchanged

#### Scenario: Complete regimen has a brand alias
- **GIVEN** EX-1 plus EX-2 is also named Dualex
- **WHEN** the vocabulary has a term for Dualex
- **THEN** it remains eligible for the ordinary scored match decision

#### Scenario: Brand is the primary name
- **GIVEN** Dualex has the explicit regimen alias EX-1 plus EX-2 and the component alias EX-1
- **WHEN** background terms or drugs are linked or exported
- **THEN** Dualex and its complete-regimen alias remain eligible but EX-1 does not

#### Scenario: Older component precedes a whole-regimen drug
- **GIVEN** an approved component drug link is older than an approved whole-regimen drug link
- **WHEN** background cards are exported
- **THEN** the component is skipped before selection so the whole-regimen drug remains eligible

#### Scenario: Regimen uses a list or a combination label
- **GIVEN** an intervention named EX-1, EX-2 and EX-3, EX-1 and EX-2 combination, or Combination of EX-1 and EX-2
- **WHEN** one of those explicitly named components is proposed as a background card
- **THEN** the component is excluded before paid classification
