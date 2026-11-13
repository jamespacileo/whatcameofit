# Spec Delta

## ADDED Requirements

### Requirement: Claim lists lead with the intervention name
Each row of a claim list SHALL lead with the claim's intervention name as the link to the claim page. The claim's full headline SHALL remain in the same row, with less visual weight than the name.

#### Scenario: Row for a named intervention
- **WHEN** a topic index lists a claim whose intervention is "Trontinemab"
- **THEN** the row's link reads "Trontinemab" and the row also shows the claim's full headline

#### Scenario: Two claims for one intervention
- **WHEN** a list holds two claims that share an intervention name
- **THEN** both rows show the same name and each shows its own headline

### Requirement: Every status carries a plain-language gloss
The site SHALL hold one fixed gloss for every status code: a short phrase that states what the status means without trial-phase vocabulary. Wherever a claim list or a claim page shows a status label, it SHALL show that status's gloss with it. The precise meaning of each status SHALL remain on the claim page and the method page.

#### Scenario: Gloss in a list
- **WHEN** a topic index lists a claim whose status is Phase 3 trial
- **THEN** the row shows the label "Phase 3 trial" and its gloss

#### Scenario: Gloss on the claim page
- **WHEN** a reader opens a claim whose status is Preclinical only
- **THEN** the page shows the label, its gloss and the precise meaning

#### Scenario: Status code without a gloss
- **WHEN** the site is built and a status code has no gloss
- **THEN** the build fails and names the code

### Requirement: Topic index opens with a summary of where its claims stand
A topic index SHALL open with one sentence that gives the number of claims listed and, for each status its claims hold, the number of claims with that status in plain language. The sentence SHALL be built by fixed rules from the counts alone. Statuses SHALL be named in path order, then the statuses off the path.

#### Scenario: Topic with two statuses
- **WHEN** a topic lists 7 claims, 5 Preclinical only and 2 Phase 3 trial
- **THEN** the page opens with a sentence that gives 7, then 5 with the preclinical wording, then 2 with the Phase 3 wording

#### Scenario: Topic with one claim
- **WHEN** a topic lists one claim
- **THEN** the sentence is in the singular and states that claim's status in plain language

#### Scenario: Topic with more than four statuses
- **WHEN** a topic's claims hold six different statuses
- **THEN** the sentence names the four statuses with the most claims and gives the count of the remaining claims without naming their statuses

#### Scenario: Vertical with no published claims
- **WHEN** a topic lists no claims
- **THEN** no summary sentence is shown

## MODIFIED Requirements

### Requirement: Neutral wording
Status labels, status glosses, overlay text and the topic summary sentence SHALL describe evidence only. The site SHALL NOT describe a claim as dead, abandoned, a scam or any similar verdict. A gloss or summary clause that carries verdict wording SHALL fail the site build.

#### Scenario: Long-quiet claim
- **WHEN** a preclinical-only claim has had no evidence event for six years
- **THEN** the page reads "no signal for 6 years" and uses no verdict wording

#### Scenario: Gloss with verdict wording
- **WHEN** the site is built and a status gloss contains the word "abandoned"
- **THEN** the build fails and quotes the gloss

#### Scenario: Summary of a topic with ended trials
- **WHEN** a topic lists a claim whose status is Trials ended early
- **THEN** the summary sentence states that its trials were stopped early and uses no verdict wording
