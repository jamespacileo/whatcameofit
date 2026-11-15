# Knowledge cards

## ADDED Requirements

### Requirement: Completed background work survives later source failures
The terms command SHALL commit each completed claim before starting the next. A later source failure SHALL return an error without discarding earlier completed terms, decisions or source records. Ordinary repeats SHALL reuse completed scored terms without new model calls. Existing source pacing and review thresholds SHALL remain unchanged.

#### Scenario: Later claim's vocabulary source fails
- **GIVEN** one selected claim completes and a later claim's vocabulary source fails
- **WHEN** the terms command exits with an error
- **THEN** the first claim's completed work remains and repeating that claim reuses its readings

### Requirement: Background cards describe the whole intervention
Vocabulary and drug cards SHALL describe complete regimens. Explicit components, including aliases and registry-filed names, SHALL NOT stand in for the whole regimen; whole-regimen aliases SHALL remain eligible. The export SHALL suppress incompatible legacy component cards and their drug-derived targets while preserving review decisions and clinical status.

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

### Requirement: Vocabulary checks receive entry-name evidence
The term classifier SHALL receive recorded vocabulary entry-name matches alongside the candidate label and definition. An entry name SHALL be treated as evidence, not an automatic exact match: it may name a narrower concept. Existing confidence thresholds and whole-intervention safeguards SHALL remain in force.

#### Scenario: Preferred label differs from the claim name
- **GIVEN** a candidate vocabulary record has a verified entry name equal to the claim's name
- **WHEN** the term is checked
- **THEN** the classifier receives that evidence and may still return broader, unrelated or uncertain

### Requirement: Pending term readings can be explicitly rechecked
Ordinary term runs SHALL reuse scored candidates. An explicit pending-term reread SHALL require named claims and reconsider only undecided condition/intervention vocabulary links. Approved and rejected links, previous decision logs and human labels SHALL remain unchanged. Every reread SHALL receive its own decision log; failure SHALL retain the prior fit and score. Kind, target and drug links SHALL NOT be rescored by this option.

#### Scenario: Successful pending reread
- **GIVEN** a pending vocabulary candidate already has a score
- **WHEN** its claim is explicitly named with `--rescore-pending`
- **THEN** the new reading is recorded and the existing approval/rejection thresholds apply

#### Scenario: Failed pending reread
- **GIVEN** a pending candidate has an earlier fit and score
- **WHEN** its explicit reread fails
- **THEN** the failed call is logged and the earlier fit and score remain

#### Scenario: Mass reread refused
- **WHEN** `--rescore-pending` is combined with `--all` or `--missing` instead of named claims
- **THEN** the command refuses before any source or model work
