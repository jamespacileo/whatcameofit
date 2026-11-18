# entity-resolution Specification

## Purpose
Links the things a claim names (interventions, papers, people, institutions and companies) to identifiers in public registries, with every link confirmed by a human.

## Requirements

### Requirement: Entities and synonyms
Each claim SHALL have entities of type intervention, paper, person, institution or company. An entity SHALL have a name and MAY have any number of synonyms, which an operator can add at any time.

#### Scenario: Compound renamed
- **WHEN** an operator adds a company code name as a synonym of an intervention
- **THEN** later registry searches for that intervention also use the code name

### Requirement: Origin paper
A claim MAY designate one of its paper entities as the origin paper, meaning the publication the first news reports were about. A claim SHALL have at most one origin paper.

#### Scenario: Second origin paper
- **WHEN** an operator designates an origin paper for a claim that already has one
- **THEN** the new paper replaces the old one as the origin paper

### Requirement: Candidate matches
For each intervention entity the system SHALL search the trial registry by the entity's name, every synonym and every search phrase. A search phrase SHALL be searched only within the claim's indication. For each paper entity with a DOI the system SHALL look the DOI up. Every hit SHALL be stored as a candidate match with its source, external identifier and score.

#### Scenario: Intervention with two synonyms
- **WHEN** resolution runs for an intervention with a name and two synonyms, and each term finds a different trial
- **THEN** three candidate matches are stored

#### Scenario: Same trial found by two terms
- **WHEN** the name and a synonym both find the same trial
- **THEN** one candidate match is stored for that trial

#### Scenario: Trial found only by a search phrase
- **WHEN** the name as written finds only trials for other conditions and a search phrase finds a trial within the claim's indication
- **THEN** that trial is stored as a candidate match

#### Scenario: Search phrase that identifies nothing
- **WHEN** a search phrase returns more than a hundred trials within the indication, or none
- **THEN** that phrase contributes no candidates

### Requirement: Human confirmation
Every candidate match SHALL start as pending. A match SHALL become approved only through an operator's action or the rule for confident candidates.

#### Scenario: High-scoring match
- **WHEN** a candidate match has a score of 0.99 and no accept threshold is set
- **THEN** it remains pending until an operator approves it

### Requirement: Match score
Each candidate match SHALL carry a score between 0 and 1 that estimates how likely it is to be correct. The score SHALL order the review queue, SHALL be published with the match, and SHALL approve or reject a match only through the rules for confident and near-zero candidates.

#### Scenario: Low-scoring match
- **WHEN** a candidate match has a score of 0.3, between the thresholds
- **THEN** it remains pending and visible in the review queue

### Requirement: Repeatable resolution
Running resolution again for a claim SHALL NOT create a second candidate for an entity, source and external identifier that already have one, and SHALL NOT change the review state of an existing candidate.

#### Scenario: Rejected match found again
- **WHEN** resolution runs again and finds a trial whose match an operator rejected earlier
- **THEN** the match stays rejected and no new candidate is created

### Requirement: Matches are scored for the claim's indication
A candidate trial match SHALL be scored on whether the record is a trial of the claim's intervention for the claim's indication. A record of the same intervention for another indication SHALL score lower than one for the claim's indication and SHALL be shown to the reviewer as being for another indication.

#### Scenario: Same drug, another condition
- **WHEN** a claim is about a vaccine for melanoma and the registry holds a trial of that vaccine for lung cancer
- **THEN** the lung cancer trial scores below the melanoma trials and is labelled as another indication

#### Scenario: Laboratory compound with unrelated trials
- **WHEN** an animal study used a compound that has registered trials only in unrelated diseases
- **THEN** none of those trials scores as a match for the claim

### Requirement: Broad names are searched within the indication
When the registries are searched for a claim, the search SHALL be narrowed by the claim's indication, so that a broad intervention name returns trials for that condition. A name that still returns more than a hundred trials within the indication SHALL contribute the registry's first page there, its hundred most relevant trials, each scored like any candidate; no further page is asked for. A search phrase that does so SHALL contribute none, as a phrase is broader than a name. A name or phrase with no trial within the indication SHALL contribute none.

#### Scenario: Broad intervention name
- **WHEN** the intervention is "CAR-T cell therapy" and the indication is stiff person syndrome
- **THEN** the search returns trials of CAR-T cell therapy in stiff person syndrome, not every CAR-T trial

#### Scenario: An established drug with many trials for the condition
- **WHEN** a claim is about buprenorphine for opioid use disorder and the registry holds hundreds of such trials
- **THEN** the hundred the registry ranks first within the condition become candidates, and the claim does not read "no trial record found" for want of them

#### Scenario: Name that identifies nothing
- **WHEN** a search phrase still returns more than a hundred trials within the indication, or a name or phrase returns none
- **THEN** it contributes no candidates

### Requirement: Scores given without the indication are marked
A pending trial candidate whose score was given before the indication was part of the question SHALL be shown in the review queue as scored without the indication. An operator SHALL be able to have the pending trial candidates that the search still returns scored again. A candidate that has been decided SHALL keep the score it was decided on.

#### Scenario: Old score in the queue
- **WHEN** a pending trial candidate was last scored on the intervention alone
- **THEN** the review queue says it was scored without the indication

#### Scenario: Scoring again
- **WHEN** an operator resolves a claim again and asks for rescoring
- **THEN** its pending trial candidates that the search returns get a new score, and decided candidates are unchanged

### Requirement: Near-zero candidates are rejected by rule
A newly scored candidate match whose score is under a configured threshold SHALL be rejected by rule instead of waiting for review. The decision SHALL be recorded as made by a rule, SHALL NOT be stored as a human label, and the candidate SHALL be kept. An operator SHALL be able to list the candidates a rule rejected and to approve any of them. A threshold of zero SHALL turn the rule off. A candidate scored exactly at the threshold, such as 0.05 with the default, still remains pending.

#### Scenario: Candidate scored near zero
- **WHEN** a new candidate is scored 0.02 and the threshold is 0.05
- **THEN** it is rejected, recorded as decided by a rule, and absent from the review queue

#### Scenario: Seeing what the rule rejected
- **WHEN** an operator lists the candidates rejected by rule for a claim
- **THEN** each is shown with its id, score, record line and link, and can be approved

#### Scenario: Rule turned off
- **WHEN** the threshold is zero
- **THEN** no new candidate is rejected by rule

### Requirement: An organisation match is approved by rule only on strong evidence
An organisation match SHALL be approved and recorded as approved by rule only when all of these hold: the registry marks the record as its chosen answer for the name; the name given, compared without regard to case, accents, punctuation, a leading "The" or a closing bracket, equals one of the record's names, labels or aliases, or equals one of its acronyms as written; a one-word name also appears among the record's names with the same letters and capitals; the registry does not type the record as "other"; the name is not the title or abbreviation of a journal of any paper record held; and, when the registry types the record as a government body, the name given states the record's country by its name or its two-letter code. Any other organisation match SHALL be pending, and its organisation SHALL stay unidentified. No looser or second match SHALL be tried. An operator SHALL be able to reject an approved match afterwards, and a rejected match SHALL NOT be approved again by a later run.

#### Scenario: Registry chooses one record by its own name
- **WHEN** the registry returns one record marked chosen for "University of Nottingham", and that is the record's name
- **THEN** that match is approved and marked as approved by rule

#### Scenario: Registry chooses another organisation
- **WHEN** the registry's chosen record for "CRISPR Therapeutics" is "Sprint PNS System", or for "Ulster University" is "RK University"
- **THEN** the match is pending and the organisation is listed as not identified

#### Scenario: Government body without its country
- **WHEN** a report names the "Food and Drug Administration" and the registry chooses a national agency of that exact name in another country
- **THEN** the match is pending, while "U.S. Food and Drug Administration" for the United States agency is approved

#### Scenario: Journal or newspaper named in a report
- **WHEN** a report names the journal "Neuron" or "The New York Times" and the registry chooses a record
- **THEN** the match is pending: "Neuron" is a journal title on record and not exactly "NeurON", and the newspaper's record is typed "other"

#### Scenario: Registry chooses none
- **WHEN** the registry returns three records for a name and marks none chosen
- **THEN** none is approved and the entity has no approved match

#### Scenario: Operator rejected the chosen record
- **WHEN** resolution runs again for an entity whose approved match an operator rejected
- **THEN** the match stays rejected

### Requirement: A trial's organisation sponsor becomes an entity
When a trial has approved events, its lead sponsor SHALL be recorded as an entity of the claim, as a company when the registry classes it as industry and as an institution otherwise, marked as named by a registry record. A sponsor that is a person SHALL NOT be recorded. An entity the claim already has under the same name SHALL gain the mark and SHALL NOT be recorded twice.

#### Scenario: Industry sponsor not named in any report
- **WHEN** a fetch runs for a claim whose approved trial is sponsored by a company no report named
- **THEN** the claim gains a company entity for it, marked as named by a registry record

#### Scenario: Sponsor the report also named
- **WHEN** a trial's sponsor has the same name as an institution entity read from the report
- **THEN** the claim has one entity for it, marked as named by both

#### Scenario: Sponsor who is a person
- **WHEN** a trial's lead sponsor is a person
- **THEN** no entity is recorded

### Requirement: Confident candidates are approved by rule
A newly scored candidate match that was scored with the claim's indication and whose score is at or above the configured accept threshold SHALL be approved by rule. The decision SHALL be recorded as made by a rule and SHALL NOT be stored as a human label. A candidate scored without the indication SHALL never be approved by rule. An accept threshold of zero or none SHALL turn the rule off. An operator SHALL be able to reject a candidate the rule approved.

#### Scenario: Confident candidate
- **WHEN** a new candidate scored with the indication scores 0.91 and the accept threshold is 0.8
- **THEN** it is approved, recorded as decided by a rule

#### Scenario: Scored without the indication
- **WHEN** a new candidate scored without the indication scores 0.95
- **THEN** it stays pending

#### Scenario: Between the thresholds
- **WHEN** a new candidate scores 0.4 with an accept threshold of 0.8 and a reject threshold of 0.05
- **THEN** it stays pending and does not count toward the claim's status

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

#### Scenario: The only eligible trial sorts after the cutoff

- **WHEN** 102 stored titles name an intervention and only the last by registry ID shares the claim's indication
- **THEN** the last trial is returned for scoring. The broad-name limit applies to the eligible set

### Requirement: A name the stored trials file under one other name is searched under it
When stored intervention entries list one of the intervention's names among their other names, the entry's own name, without dose, form or route, is what a sponsor files the treatment under. The system SHALL take such a name as another name of the intervention only when every entry that lists the intervention's name agrees on one name, or on one name and its forms as for a substance, and either at least two stored trials file it so or the name it is filed under is a development code, one with a digit in it; an entry that joins several products, an entry whose own name is a control or a description, and an entry that is not a drug, biological, genetic, combination or supplement entry SHALL say nothing. The name taken SHALL be searched in the trial registry as a name of the intervention and SHALL be named in the question put to the match scoring, together with the substance's name. It SHALL NOT be stored or shown as a name of the intervention, and no model SHALL supply it. A name the entries file under two names SHALL give none.

To find stored candidates only, the system SHALL also use each name that at least two stored trials file the intervention's name under, whether or not the entries agree: a wrong one adds a candidate that is scored, and nothing else. Such a name SHALL NOT be searched in the trial registry and SHALL NOT be named in the question.

#### Scenario: Generic name filed under a development code
- **WHEN** every stored entry that lists "sasanlimab" among its other names is named PF-06801591
- **THEN** PF-06801591 is searched in the trial registry as a name, the scoring is told that registry trials list it beside the intervention's name and that this is a lead, not proof that a trial tests the intervention, and the intervention's synonyms are unchanged

#### Scenario: Name one trial alone files under another
- **WHEN** a single stored entry named Palifermin lists "growth factor" among its other names
- **THEN** no other name is taken for an intervention named "growth factor"

#### Scenario: One trial files the name under a development code
- **WHEN** a single stored entry named REGN3767 lists "fianlimab" among its other names and no other entry files fianlimab under another name
- **THEN** REGN3767 is taken as another name of the intervention

#### Scenario: Name filed under two names
- **WHEN** one stored entry named EX-900 lists the intervention's name and another, named "Arm A chemotherapy", lists it too
- **THEN** no other name is taken, searched or told to the scoring

#### Scenario: One trial lists two forms under one brand

- **WHEN** one NCT lists a non-code brand alias for two forms of the same drug
- **THEN** it contributes one trial of corroboration. A second distinct supporting NCT qualifies the alias under the two-trial rule

### Requirement: Whoever scores a trial sees the other names it lists
The trial registry's search SHALL ask for the other names of each intervention, and the record put to the match scoring SHALL show them with the intervention they belong to, at most eight for an intervention. A sponsor files a trial under one name and lists the generic name, the brand and the development codes there; without them a trial of the claim's intervention filed under a code reads as a trial of something else.

#### Scenario: Trial filed under a code
- **WHEN** a candidate's intervention is named NMRA-335140 and lists navacaprant among its other names
- **THEN** the record shown for scoring names navacaprant beside NMRA-335140

### Requirement: A combination is searched by its treatments as names alone
When an intervention's name joins several treatments, the search for all of them together SHALL take each treatment as a name alone: words that say the name is a combination ("combination regimen", "combination therapy") SHALL be left out of a part, and treatments listed with commas SHALL be parts like those joined by a word. A part that names a kind of care and no product ("standard chemotherapy") SHALL be left out of the search when at least two named treatments remain, and kept otherwise.

#### Scenario: Combination words in the name
- **WHEN** the intervention is "eloralintide and tirzepatide combination regimen"
- **THEN** the registry is searched for trials that give eloralintide and tirzepatide

#### Scenario: Three parts, one a kind of care
- **WHEN** the intervention is "Braftovi, cetuximab and standard chemotherapy"
- **THEN** the registry is searched for trials that give Braftovi and cetuximab

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

### Requirement: A registry search leaves a record
Each search of a registry for a claim SHALL leave a record of the source, the term sent, the condition it was narrowed by if any, the time, the number of records the source reported, the number kept, and whether a limit left records out. A term that was not sent SHALL leave a record saying why. The records of a claim's latest search SHALL replace those of the search before.

#### Scenario: A search that found trials
- **WHEN** a claim's intervention is searched and the registry reports 37 records
- **THEN** a record holds the term, the time, 37 reported and 37 kept

#### Scenario: A search that found none
- **WHEN** a term is searched and the registry reports no record
- **THEN** a record holds the term, the time and zero reported

#### Scenario: A limit left records out
- **WHEN** a name is still broad once narrowed by the condition and its records are not taken
- **THEN** a record holds the term, the number reported, zero kept and that a limit left them out

#### Scenario: A term that is not sent
- **WHEN** a name is refused as no search term
- **THEN** a record holds the name and the reason it was not sent

### Requirement: A lookup that failed is not a finished search
A claim's search SHALL be finished only when the lookup of its substance and every search of the registry for its names ran to an answer. When one of them could not be asked or failed, the search SHALL be unfinished, SHALL be reported with the claim and the lookup that failed, and SHALL be due again. A lookup that answered that it knows nothing SHALL count as an answer.

#### Scenario: The registry of substances is down
- **WHEN** the lookup of a claim's substance fails on every attempt
- **THEN** the claim's search is unfinished and due again, and the claim is not decided on it

#### Scenario: The substance is not known
- **WHEN** the registry of substances answers that it has no record for the name
- **THEN** the lookup is finished, and the claim has no substance record

#### Scenario: Papers could not be searched
- **WHEN** the registry searches finished and the literature index failed
- **THEN** the claim's search of registries is finished, and its search for papers is due again by itself

### Requirement: A claim never searched is told apart from one searched
The pipeline SHALL be able to say of any claim whether its registries were searched, when, and with what terms, from the records its searches left. A claim with no such record SHALL be reported as never searched by `thenwhat prepare` and by the audit list, whatever status it holds. The rule that derives a status SHALL be unchanged.

#### Scenario: A claim with no search record
- **WHEN** a claim holds the status given when no trial is found and has no record of a search
- **THEN** it is listed as never searched, and its registry search is due

#### Scenario: A claim searched with no result
- **WHEN** a claim's searches each left a record reporting no trial
- **THEN** it is not listed as never searched

### Requirement: A trial match keeps its record field by field
Whenever a trial match's one-line summary is written, the pipeline SHALL also keep the record's title, conditions and interventions as the registry wrote them, its phases and state as the codes the trial facts use, and its size as the trial facts read it. A registry state that recruits SHALL be kept as "under_way". A match to anything other than a trial registry record SHALL keep no fields. A command SHALL read the fields of every shown trial match stored before they were kept, and SHALL name and exit 1 for any the registry no longer answers for, leaving its fields empty.

#### Scenario: Candidate found by a registry search
- **WHEN** a search returns a recruiting Phase 1/Phase 2 trial for a claim
- **THEN** its match keeps the title, conditions and interventions, the phases "phase_1" and "phase_2", and the state "under_way"

#### Scenario: Match stored before the fields were kept
- **WHEN** the operator runs `thenwhat entity record-facts` and one stored match's trial is no longer in the registry
- **THEN** every other shown trial match has its fields, and the command names that trial and exits 1

### Requirement: The export says the score a match needs to be approved by rule
The export SHALL carry the score at or above which a registry match is approved by rule, or none when that rule is off, so the site can say what a possible record lacks.

#### Scenario: Rule on at 0.8
- **WHEN** the export is built with approval by rule at 0.8
- **THEN** the export's `match_accept_above` is 0.8, and it is null when the rule is off

### Requirement: Organisations are looked up by name
For each institution or company entity the system SHALL look its name up in an open organisation registry and store each hit as a candidate match with the registry's identifier and a one-line record of the organisation's name, country and website. The score SHALL be the registry's own measure of the name match, and no model SHALL score it.

#### Scenario: University named in the article
- **WHEN** resolution runs for an institution entity that the organisation registry matches exactly
- **THEN** one candidate match is stored with that registry's identifier and a score of 1

#### Scenario: Name the registry does not know
- **WHEN** the registry returns no organisation for the name
- **THEN** no candidate is stored and nothing fails

### Requirement: People are not looked up
The system SHALL NOT search any registry or directory for a person entity.

#### Scenario: Claim with a named researcher
- **WHEN** resolution runs for a claim that has a person entity
- **THEN** no request is made for that person and no candidate is stored

### Requirement: A rule's trial approvals can be scored again
On request, resolving a claim SHALL score again, with the question, thresholds and rule of a first resolution, each trial match a rule approved that the registry search still returns, and SHALL let the rule decide it again. A match a person or an assistant decided SHALL be left as it is. A match the rule no longer approves SHALL wait for review, or be rejected by the rule when it scores under the rejection threshold, and the claim's status SHALL be derived again. Nothing SHALL be decided until every match is scored.

#### Scenario: A rule's approval no longer stands
- **WHEN** a trial a rule approved is scored again and is read as the intervention studied for something else
- **THEN** the match waits for review, the events read from it are rejected by the rule, and the claim's status no longer rests on that trial

#### Scenario: A rule's approval stands
- **WHEN** a trial a rule approved is scored again at or above the approval threshold for the claim's indication
- **THEN** the match stays approved by the rule and its events are unchanged

#### Scenario: A decision by a person or an assistant
- **WHEN** a claim's trial match was approved by a person or an assistant
- **THEN** it is not scored again and its events are unchanged

#### Scenario: A scoring that fails
- **WHEN** the scoring of a claim's rule approvals fails part of the way
- **THEN** every approval and event is as it was

### Requirement: What a re-scoring withdraws and leaves is reported
For a match the rule no longer approves, the events read from it that a rule approved or that still wait SHALL be rejected by the rule; an event a person or an assistant decided SHALL be left and reported. A rule-approved trial the search no longer returns SHALL stay approved and be reported. The result SHALL name the trials now waiting, the trials rejected, the trials not returned and the events left.

#### Scenario: An event decided by a person or an assistant
- **WHEN** a match is no longer approved and one of its events was approved by an assistant
- **THEN** that event stays approved and the result names it

#### Scenario: An approved trial the search no longer returns
- **WHEN** a rule approved a trial for a claim and the registry search for the claim no longer returns it
- **THEN** the match stays approved, it is not scored, and the result names it

### Requirement: A trial the intervention is in without being what it tests is its own answer
The question asked about a trial record SHALL offer, beside a match, another indication and not a match, the answer that the claim's intervention is in the record but is not what the trial tests as a treatment for the indication: it is the comparator or control for something else under test, it is given to every arm alongside what is tested, or it has another role in the trial, such as the anaesthetic for a procedure. A record read so SHALL NOT be approved by rule, whatever its score. The review queue and the site SHALL say that it was read so. The live lookup SHALL ask the same question with the same answers. An active comparator is not tested: in a head-to-head trial of another drug against the claim's drug, the trial's phase and outcome belong to the other drug's claim. For a claim whose intervention is a combination, the combination is what is tested when the arms differ in a part of it.

#### Scenario: Comparator or background treatment
- **WHEN** a trial gives the claim's drug to every arm as the anaesthetic for the procedure it tests, and the record is read as in the trial but not what is tested
- **THEN** the match is not approved by rule and the review queue says how it was read

#### Scenario: Active comparator in a head-to-head trial
- **WHEN** a trial tests another drug against the claim's drug as its active comparator
- **THEN** the record is read as in the trial but not what is tested, and is not approved by rule for the claim

#### Scenario: The claim's drug is the treatment on trial
- **WHEN** a trial's arms differ in whether patients receive the claim's drug for the claim's condition
- **THEN** the record can be read as a match and approved by rule as before

### Requirement: A combination is searched for all its treatments together
When the intervention's name or one of its other names joins several treatments ("plus", "with", "and", "in combination with", "combined with", "+" or "/"), the registry search SHALL also look for every one of those treatments at once, each part in brackets and the parts joined by AND, under the same rules as a name. The name as written SHALL still be searched. Every trial found is a candidate scored like any other; finding it by the parts does not make it a match.

#### Scenario: A combination
- **WHEN** a claim's intervention is "aspirin plus avelumab"
- **THEN** the registry is searched for "aspirin plus avelumab" and for "(aspirin) AND (avelumab)", and a trial the second search finds becomes a candidate

#### Scenario: One treatment
- **WHEN** a claim's intervention is "semaglutide"
- **THEN** only its names, phrases and codes are searched, as before

### Requirement: A treatment is also searched by its substance's name
The registry of substances SHALL be asked for each of the intervention's names and, where a name carries a dose or schedule, for its core name too ("semaglutide 2.4 mg" as "semaglutide"). When it lists those names under one substance, the registry search SHALL also search the name it gives that substance, as a name, unless it equals a name already searched. A brand such as Mosquirix, Aduhelm or Wegovy then finds the trials filed under the substance. Every trial found is a candidate scored like any other.

#### Scenario: A brand name and its substance
- **WHEN** a claim's intervention is a brand that the registry of substances lists under a substance with another name
- **THEN** the trial registry is searched for the brand and for the substance's name, and a trial found by the substance's name becomes a candidate
