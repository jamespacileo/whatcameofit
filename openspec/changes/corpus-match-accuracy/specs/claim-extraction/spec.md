## ADDED Requirements

### Requirement: Alternate names preserve complete intervention scope
Extraction instructions SHALL ask only for names of the same complete intervention, excluding components, class members, broader categories, related substances and names omitting explicit stereochemistry, route or regimen restrictions. Before saving new synonyms, the pipeline SHALL exclude explicit regimen components using the existing whole-intervention boundary. Whole-regimen brand aliases SHALL remain eligible. No additional model call SHALL be introduced.

#### Scenario: A draft lists component names
- **GIVEN** a draft for EX-1 plus EX-2 lists EX-1, EX-2 and Dualex as alternate names
- **WHEN** its entities are saved
- **THEN** only Dualex is saved as an alternate name

#### Scenario: A brand is the primary name
- **GIVEN** a draft for Dualex lists EX-1 plus EX-2 and its individual components as alternate names
- **WHEN** its entities are saved
- **THEN** the whole-regimen alias is retained and component aliases are excluded
