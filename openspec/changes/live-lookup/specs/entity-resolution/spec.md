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
When the substance registry lists no substance under any of an intervention's names, the system SHALL ask a second source, one that files brand names under their ingredients and whose terms are recorded and accepted by the operator, about the same names. While the operator has not accepted its terms the second source SHALL NOT be asked, and the command that looks many claims up SHALL say so. The second source SHALL NOT be asked when the substance registry lists the names under one substance or under more than one. A brand SHALL be resolved only when the second source lists one of the names as a brand, equal to it ignoring letter case and runs of spaces and nothing else, and the brands found lead to exactly one ingredient. Ingredients with different names SHALL count as several, with no allowance for a name that opens another: the rule that counts a substance and its forms as one applies to the substance registry only. The system SHALL then keep that ingredient's record as fetched, with the second source's name, the ingredient's identifier there and the fetch time, in place of a substance's record, and SHALL keep no code from it. The ingredient's name SHALL be searched in the trial registry as a name of the intervention, as a substance's name is, and SHALL NOT be stored or shown as a name of the intervention. When the second source marks the brand a vaccine, its ingredient is the antigen, which another maker's vaccine can share: the record SHALL still be kept as fetched, the ingredient's name SHALL NOT be searched as a name of the intervention nor find a claim for a read, and the command SHALL say that the brand is a vaccine and its ingredient is not searched. RxNorm marks a vaccine by a code from CDC's vaccine code set (CVX) on the brand's branded drugs; no name, word or model decides it. A CVX code CDC gives a product that is not a vaccine (an immune globulin, an antitoxin, a monoclonal antibody such as nirsevimab, a tuberculin skin test, or an unspecified or unknown code) SHALL NOT mark a vaccine. An ingredient kept before vaccines were told apart SHALL be treated as not known to be no vaccine, and so not searched, until the brand is looked up again. Only a brand of one ingredient is ever kept, and every such record kept since vaccines were told apart has the answers that tell it, so no record stays unknown once looked up again. A brand of more than one ingredient, and a name the second source does not list as a brand, SHALL keep nothing. No model SHALL supply an ingredient and no loose match SHALL be taken. The command SHALL say which source answered, and when neither listed the names SHALL say so of both. A later run SHALL replace what was kept. It SHALL remove what was kept only when the sources asked answered whole and their answer no longer identifies one substance: neither lists the names, or a source lists them under more than one substance or a brand under more than one ingredient. When a source could not answer whole, or could not be asked, what was kept SHALL stay as it was. When either source cannot be asked about a claim, or cannot answer whole, the command that looks many claims up SHALL say that the claim was not looked up, SHALL leave what was kept for it unchanged, and SHALL go on to the next claim.

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
- **WHEN** many claims are looked up and a source fails for one of them, or cannot answer whole
- **THEN** the command says that claim was not looked up, keeps nothing new for it, leaves what was kept for it as it was, and looks the remaining claims up

#### Scenario: Brand neither source lists
- **WHEN** neither the substance registry nor the second source lists any of the names
- **THEN** nothing is kept, the command says that neither lists it, and the trial registry is searched as before

### Requirement: Stored trials that list the intervention are candidates
Besides the trial registry's own search, the system SHALL look for an intervention among the registry trials it holds (registry-corpus), with no network request and no model. A stored trial SHALL be found when one of its intervention entries names the intervention: the entry's name or one of the other names it lists equals one of the intervention's names, a development code kept for it, or its substance's name. Names SHALL be compared whole, ignoring only letter case, runs of spaces and trade mark signs. An entry that writes several names, apart by commas or semicolons or with one in brackets ("Braftovi, PF-07263896, LGX818", "Zidesamtinib (NVL-520)"), SHALL count as naming each; no name SHALL be found inside a longer name. A name that no stored entry names SHALL be looked for as a whole word in the stored trials' titles and acronyms, and, when it has a digit in it as a development code does, at the start of the sponsor's study identifier. A name that joins several treatments SHALL find the stored trials that have an entry for every treatment it joins; a part that names a kind of care and no product ("standard chemotherapy") SHALL need no entry. When more than twenty stored trials are found for a name, only those whose conditions or title share a telling word with the claim's indication SHALL be kept, and none when those are more than a hundred: the registry's own search, which ranks, handles a broad name. Twenty or fewer SHALL all be kept, whatever their conditions: a trial across several tumour types names no one condition, and the scoring decides.

A stored trial found this way that the registry's search did not return SHALL be read from the registry in full and SHALL then be a candidate match like any other: scored with the same question, rejected near zero and approved by the same rule, and never approved for being listed. One the registry no longer answers for SHALL NOT become a candidate. A candidate that already exists SHALL be left as it is and SHALL NOT be read again.

#### Scenario: Trial filed under a code that lists the name
- **WHEN** a stored trial's intervention entry is named by a development code and lists the claim's intervention among its other names, and the registry's search for the claim did not return it
- **THEN** the trial is read from the registry in full, stored as a candidate match and scored for the claim's indication

#### Scenario: Stored trial for another condition
- **WHEN** a stored trial lists the intervention and is for a condition other than the claim's indication
- **THEN** it is a candidate, it is scored as any candidate is, and the rule that approves a trial scored high for the indication does not approve it

#### Scenario: Name inside a longer name
- **WHEN** a stored entry is named "zentalimab pegol" and the intervention is "zentalimab"
- **THEN** the trial is not found by that entry

#### Scenario: Combination whose parts are filed apart
- **WHEN** the intervention is "zanzalintinib plus Tecentriq" and a stored trial has one entry named XL092 and another that lists Tecentriq among its other names, and other stored trials list zanzalintinib as another name of XL092
- **THEN** the trial is a candidate

#### Scenario: Name in a study identifier only
- **WHEN** no stored entry names "BNT211" and a stored trial's sponsor identifier is "BNT211-01"
- **THEN** the trial is a candidate

#### Scenario: Broad name
- **WHEN** more than a hundred stored trials list a name, and more than a hundred of them share a telling word with the claim's indication
- **THEN** none becomes a candidate through the stored trials

#### Scenario: Name with many trials, few for the indication
- **WHEN** more than twenty stored trials list a name and one of them is for the claim's indication
- **THEN** that one is a candidate and the others are not

#### Scenario: No stored trials
- **WHEN** the system holds no registry trial
- **THEN** resolution searches the registry as before

### Requirement: A name the stored trials file under one other name is searched under it
When stored intervention entries list one of the intervention's names among their other names, the entry's own name, without dose, form or route, is what a sponsor files the treatment under. The system SHALL take such a name as another name of the intervention only when every entry that lists the intervention's name agrees on one name, or on one name and its forms as for a substance, and either at least two stored trials file it so or the name it is filed under is a development code, one with a digit in it; an entry that joins several products, an entry whose own name is a control or a description, and an entry that is not a drug, biological, genetic, combination or supplement entry SHALL say nothing. The name taken SHALL be searched in the trial registry as a name of the intervention and SHALL be named in the question put to the match scoring, together with the substance's name. It SHALL NOT be stored or shown as a name of the intervention, and no model SHALL supply it. A name the entries file under two names SHALL give none.

To find stored candidates only, the system SHALL also use each name that at least two stored trials file the intervention's name under, whether or not the entries agree: a wrong one adds a candidate that is scored, and nothing else. Such a name SHALL NOT be searched in the trial registry and SHALL NOT be named in the question.

#### Scenario: Generic name filed under a development code
- **WHEN** every stored entry that lists "sasanlimab" among its other names is named PF-06801591
- **THEN** PF-06801591 is searched in the trial registry as a name, the scoring is told it is another name of the intervention, and the intervention's synonyms are unchanged

#### Scenario: Name one trial alone files under another
- **WHEN** a single stored entry named Palifermin lists "growth factor" among its other names
- **THEN** no other name is taken for an intervention named "growth factor"

#### Scenario: One trial files the name under a development code
- **WHEN** a single stored entry named REGN3767 lists "fianlimab" among its other names and no other entry files fianlimab under another name
- **THEN** REGN3767 is taken as another name of the intervention

#### Scenario: Name filed under two names
- **WHEN** one stored entry named EX-900 lists the intervention's name and another, named "Arm A chemotherapy", lists it too
- **THEN** no other name is taken, searched or told to the scoring

### Requirement: Whoever scores a trial sees the other names it lists
The trial registry's search SHALL ask for the other names of each intervention, and the record put to the match scoring SHALL show them with the intervention they belong to, at most eight for an intervention. A sponsor files a trial under one name and lists the generic name, the brand and the development codes there; without them a trial of the claim's intervention filed under a code reads as a trial of something else.

#### Scenario: Trial filed under a code
- **WHEN** a candidate's intervention is named NMRA-335140 and lists navacaprant among its other names
- **THEN** the record shown for scoring names navacaprant beside NMRA-335140

### Requirement: A rule's rejection made without the other names is scored again
When pending candidates are scored again on request, the system SHALL also score again each trial candidate that a rule rejected for scoring near zero and whose record files the intervention under another name: an intervention entry that is named by none of the intervention's names or codes lists one of them among its other names, or is named by a name the stored trials file the intervention under. Before the scoring was shown those names, such a record read as a trial of something else. A candidate scored again this way SHALL wait like a pending candidate and SHALL be decided by the same rules: rejected again near zero, approved only when scored high for the claim's indication. A rejection a person or an assistant made SHALL be left as it is, and so SHALL a rule's rejection of a record that names the intervention plainly. When a scoring fails, every rejection SHALL stay as it was.

#### Scenario: Rejected when the name was not shown
- **WHEN** a rule rejected a trial whose intervention is named by a development code, the record lists the claim's intervention among that entry's other names, and pending candidates are scored again
- **THEN** the trial is scored again with the other names shown, and the rules decide it afresh

#### Scenario: Rejected by a person
- **WHEN** a person rejected such a trial
- **THEN** it is not scored again and stays rejected

### Requirement: The brand source is credited with the statement it asks for
While the source of brands is recorded as accepted, the export's list of data sources SHALL name it with its address, and the site SHALL show, where it lists its data sources, the statement the source's terms ask an application to carry, word for word.

#### Scenario: Method page
- **WHEN** a reader opens the part of the method page that says where the data comes from
- **THEN** the source of brands is named, what it is used for is said, and the statement its terms ask for is shown in full
