# Spec Delta

## Purpose

Ties a claim's condition, intervention and target to entries in open vocabularies, with a score for each tie, and publishes each entry's own definition as a background card, so that a claim page can be read by someone who does not already know its terms.

## ADDED Requirements

### Requirement: Candidate terms are gathered by rule
For each claim, candidate subject terms SHALL be gathered without a model from two places: the terms the registry files at least half of the claim's approved trials under, each with the number of those trials that carry it, and vocabulary terms whose label equals the claim's indication, its intervention's name or one of the intervention's other names. No more than the configured number of candidates, ten by default, SHALL be kept for a claim.

#### Scenario: Claim with trials
- **WHEN** a claim has six approved trials, five filed under "Osteoarthritis, Knee", three under "Pain" and one under "Fibromyalgia"
- **THEN** the first two terms are candidates for its condition, with counts of five and three, and the third is not a candidate

#### Scenario: Claim with no trial and a named drug
- **WHEN** a claim has no trial and its intervention's name equals a vocabulary term's label
- **THEN** that term is a candidate for its intervention

#### Scenario: Claim with no trial and a free-text condition
- **WHEN** a claim has no trial and no vocabulary label equals its indication
- **THEN** the claim has no candidate for its condition

### Requirement: Each candidate is scored for the claim
Each candidate SHALL be put to a bounded decision with three options: the term is the claim's condition or intervention, the term is broader than it, the term is something else. The candidate's score SHALL be the probability of the option chosen when that option is one of the first two, and zero otherwise. The candidate SHALL record which of the two it was read as.

#### Scenario: Exact term
- **WHEN** the decision reads "Hepatitis B, Chronic" as the claim's condition with a probability of 0.95
- **THEN** the candidate is exact with a score of 0.95

#### Scenario: Broader term
- **WHEN** the decision reads "Metabolic Diseases" as broader than the claim's condition with a probability of 0.9
- **THEN** the candidate is broader with a score of 0.9

#### Scenario: Term the registry filed wrongly
- **WHEN** the decision reads a Parkinson's disease term as something else for a claim about endometrial cancer
- **THEN** the candidate's score is zero

### Requirement: Each candidate carries its reasons
Each candidate SHALL carry, as codes found by rule, why it was gathered: that the registry files a stated number of the claim's trials under it, or that its label equals a stated name of the claim.

#### Scenario: Term on five of six trials
- **WHEN** a candidate was gathered from five of a claim's six trials
- **THEN** it carries the registry reason with the counts five and six

### Requirement: Term links are decided by rule
A candidate whose score is at or above the configured threshold SHALL be approved and recorded as approved by rule. One below the configured rejection level SHALL be rejected by rule. Any other SHALL be pending. An operator SHALL be able to reject an approved link, and a rejected link SHALL NOT be approved again by a later run.

#### Scenario: Confident exact term
- **WHEN** a candidate has a score of 0.95 and the threshold is 0.8
- **THEN** the link is approved and marked as approved by rule

#### Scenario: Wrongly filed term
- **WHEN** a candidate has a score of zero
- **THEN** the link is rejected by rule and no card is made from it

### Requirement: One card for the condition and one for the intervention
For the condition and for the intervention, the export SHALL carry at most one card each: the approved exact link with the highest score or, when there is none, the approved broader link with the highest score, marked as broader. A claim with no approved link for either SHALL carry no card for it.

#### Scenario: Exact and broader terms both approved
- **WHEN** a claim's condition has an approved exact term and an approved broader term
- **THEN** the card is made from the exact term

#### Scenario: Only a broader term
- **WHEN** a claim's condition has only an approved broader term
- **THEN** the card is made from it and says it is a broader term

### Requirement: A card states the vocabulary's own words
A card SHALL carry the term's label, its definition as the vocabulary's publisher wrote it, a link to the term's record, the source's name, the version or date of the vocabulary, the link's score, its reasons, and the date the record was read. The definition SHALL NOT be rewritten, summarised or added to.

#### Scenario: Condition card
- **WHEN** a card is made from a vocabulary term
- **THEN** it carries that term's label and its definition word for word, with the source and the date read

#### Scenario: Term with no definition
- **WHEN** an approved term's record has no definition
- **THEN** the card carries the label and link and no definition

### Requirement: A drug card states what it is and what it acts on
For an intervention found by name in the drug source, where the source's name for it equals the intervention's name or one of its other names, a card SHALL carry the kind of molecule and, when the source gives one, each mechanism as an action and a target's name. The card SHALL NOT carry the source's view of how far the drug has got, what it is approved for or what it is used for.

#### Scenario: Named peptide with two targets
- **WHEN** the source gives a drug two mechanisms, each an agonist of a named receptor
- **THEN** the card carries the kind of molecule and both mechanisms

#### Scenario: Drug with no mechanism on record
- **WHEN** the source knows a drug and gives it no mechanism
- **THEN** the card carries the kind of molecule and no mechanism

#### Scenario: Procedure
- **WHEN** an intervention is a procedure the drug source does not know
- **THEN** no drug card is made

### Requirement: A target card states what the target is
When a drug card names exactly one target that is a single human protein, a card SHALL carry that protein's name, its gene symbol and the source's description of its function, with the description's own source and licence. A drug with several targets, or a target that is not a single protein, SHALL give no target card.

#### Scenario: Drug with one protein target
- **WHEN** a drug's only mechanism names one human protein
- **THEN** a target card carries the protein's name, gene symbol and function description

#### Scenario: Drug with two targets
- **WHEN** a drug's mechanisms name two proteins
- **THEN** no target card is made

### Requirement: A fact is carried only under an accepted licence
A card fact SHALL be exported only when its source and licence are recorded as accepted in the project's list of sources. A fact whose source is not so recorded SHALL NOT be exported, and the export SHALL carry no card that would then be empty.

#### Scenario: Share-alike source not yet accepted
- **WHEN** the drug source's share-alike parts are not recorded as accepted
- **THEN** the export carries no mechanism from that source

### Requirement: Cards do not change the status
Background cards and term links SHALL NOT be inputs to a claim's status or to its evidence stage.

#### Scenario: Card for an approved drug class
- **WHEN** a claim gains a card whose definition mentions approved uses
- **THEN** the claim's status and explaining events are unchanged
