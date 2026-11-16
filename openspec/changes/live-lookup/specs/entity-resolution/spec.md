# Spec Delta

## ADDED Requirements

### Requirement: Development codes come from a substance registry
Before the trial registry is searched for an intervention, the system SHALL look the intervention's name and every synonym up in a substance registry whose terms are recorded. When they lead to exactly one substance, the system SHALL keep that substance's record as fetched, with its source, its identifier and the fetch time, and the names the registry marks as codes for it, leaving out any code that is already one of the intervention's names. Each code SHALL be searched for in the trial registry like a search phrase, within the claim's indication only, and SHALL be named in the question put to the match scoring. A code SHALL NOT be stored or shown as a name of the intervention. No model SHALL supply a code, and no code SHALL be taken from a substance found by a loose match. A substance and the forms the registry files apart from it, each named by the substance's name followed by further whole words or a hyphenated suffix, SHALL count as that one substance. When the names lead to no substance, or to more than one, the system SHALL keep no code and SHALL say which of the two it was. A later run SHALL replace what was kept, and SHALL remove it when the registry no longer lists the names under one substance.

#### Scenario: Trial filed under a development code
- **WHEN** the substance registry lists an intervention's name under one substance with a code, and the trial registry holds a trial under that code within the claim's indication
- **THEN** the code is kept with the substance's record, the trial is stored as a candidate match, and the intervention's synonyms and search phrases are unchanged

#### Scenario: Intervention the substance registry does not list
- **WHEN** the substance registry lists no substance under any of the intervention's names
- **THEN** no code is kept, the command says that the registry does not list it, and the trial registry is searched as before

#### Scenario: Names listed under more than one substance
- **WHEN** the intervention's name leads to one substance and a synonym to another
- **THEN** no code is kept and the command names the substances found

#### Scenario: A brand listed under a substance and its salt
- **WHEN** the substances found are one substance and its forms, each form's name being the substance's name followed by further whole words or a hyphenated suffix (imatinib and imatinib mesylate, dostarlimab and dostarlimab-gxly)
- **THEN** they count as that one substance, its record and its codes are kept, and its name is searched in the trial registry as a name of the intervention

### Requirement: A brand the substance registry does not list is looked up under its ingredient
When the substance registry lists no substance under any of an intervention's names, the system SHALL ask a second source, one that files brand names under their ingredients and whose terms are recorded and accepted by the operator, about the same names. While the operator has not accepted its terms the second source SHALL NOT be asked, and the command that looks many claims up SHALL say so. The second source SHALL NOT be asked when the substance registry lists the names under one substance or under more than one. A brand SHALL be resolved only when the second source lists one of the names as a brand, equal to it ignoring letter case and runs of spaces and nothing else, and the brands found lead to exactly one ingredient. Ingredients with different names SHALL count as several, with no allowance for a name that opens another: the rule that counts a substance and its forms as one applies to the substance registry only. The system SHALL then keep that ingredient's record as fetched, with the second source's name, the ingredient's identifier there and the fetch time, in place of a substance's record, and SHALL keep no code from it. The ingredient's name SHALL be searched in the trial registry as a name of the intervention, as a substance's name is, and SHALL NOT be stored or shown as a name of the intervention. When the second source marks the brand a vaccine, its ingredient is the antigen, which another maker's vaccine can share: the record SHALL still be kept as fetched, the ingredient's name SHALL NOT be searched as a name of the intervention nor find a claim for a read, and the command SHALL say that the brand is a vaccine and its ingredient is not searched. RxNorm marks a vaccine by a code from CDC's vaccine code set (CVX) on the brand's branded drugs; no name, word or model decides it. A CVX code CDC gives a product that is not a vaccine (an immune globulin, an antitoxin, a monoclonal antibody such as nirsevimab, a tuberculin skin test, or an unspecified or unknown code) SHALL NOT mark a vaccine. An ingredient kept before vaccines were told apart SHALL be treated as not known to be no vaccine, and so not searched, until the brand is looked up again. A brand of more than one ingredient, and a name the second source does not list as a brand, SHALL keep nothing. No model SHALL supply an ingredient and no loose match SHALL be taken. The command SHALL say which source answered, and when neither listed the names SHALL say so of both. A later run SHALL replace what was kept, and SHALL remove it when neither source lists the names under one substance any longer. When either source cannot be asked about a claim, the command that looks many claims up SHALL say that the claim was not looked up, SHALL leave what was kept for it unchanged, and SHALL go on to the next claim.

#### Scenario: Brand the substance registry does not list, of one ingredient
- **WHEN** the substance registry lists none of an intervention's names and the second source lists its name as a brand of one ingredient
- **THEN** the ingredient's record is kept with the second source's name, its identifier and the fetch time, no code is kept, the ingredient's name is searched in the trial registry as a name, the intervention's synonyms and search phrases are unchanged, and the command names the second source as the one that answered

#### Scenario: A brand the source of brands marks a vaccine
- **WHEN** the substance registry lists none of an intervention's names and the second source lists its name as a brand of one ingredient, and gives the brand's branded drug a vaccine code (Ervebo, under "Zaire ebolavirus envelope glycoprotein", CVX 204)
- **THEN** the ingredient's record is kept with the vaccine code, the ingredient's name is not searched in the trial registry, and the command says the brand is a vaccine whose ingredient is not searched as a name

#### Scenario: A brand CDC gives a code that is not a vaccine's
- **WHEN** the second source lists a brand under one ingredient whose branded drugs carry only CVX codes CDC gives products that are not vaccines (Beyfortus, nirsevimab, CVX 306 and 307)
- **THEN** the ingredient is searched as a name, as for any brand of one ingredient

#### Scenario: An ingredient kept before vaccines were told apart
- **WHEN** an ingredient from the second source was kept without the answers that tell a vaccine apart
- **THEN** it is not searched and finds no claim until `entity codes` or `resolve` looks the brand up again, and is then searched or not by the rule above

#### Scenario: The substance registry lists the intervention
- **WHEN** the substance registry lists the intervention's names under one substance, or under more than one
- **THEN** the second source is not asked

#### Scenario: Brand of more than one ingredient
- **WHEN** the substance registry lists none of the names and the second source lists the brand under two ingredients, neither a form of the other
- **THEN** nothing is kept and the command names the ingredients found

#### Scenario: Brand of two ingredients, one's name opening the other's
- **WHEN** the second source lists the brand under two ingredients and one's name is the other's followed by further words
- **THEN** they are two ingredients and nothing is kept

#### Scenario: Second source's terms not accepted
- **WHEN** the operator has not accepted the second source's terms
- **THEN** it is not asked, the command says so, and an intervention the substance registry does not list is said to have no code as before

#### Scenario: A source does not answer for one claim among many
- **WHEN** many claims are looked up and a source fails for one of them
- **THEN** the command says that claim was not looked up, keeps nothing new for it, and looks the remaining claims up

#### Scenario: Brand neither source lists
- **WHEN** neither the substance registry nor the second source lists any of the names
- **THEN** nothing is kept, the command says that neither lists it, and the trial registry is searched as before

### Requirement: The brand source is credited with the statement it asks for
While the source of brands is recorded as accepted, the export's list of data sources SHALL name it with its address, and the site SHALL show, where it lists its data sources, the statement the source's terms ask an application to carry, word for word.

#### Scenario: Method page
- **WHEN** a reader opens the part of the method page that says where the data comes from
- **THEN** the source of brands is named, what it is used for is said, and the statement its terms ask for is shown in full
