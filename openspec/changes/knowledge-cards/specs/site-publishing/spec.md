# Spec Delta

## ADDED Requirements

### Requirement: Background cards on the claim page
A claim page SHALL show the claim's background cards under their own heading, after the records: at most one for the condition, one for the intervention, one for what a drug is and acts on, and one for a drug's target. Each card SHALL show its label, and its definition one press away, with the source's name, a link to the source's record and the date the record was read. A claim with no card SHALL show no such section.

#### Scenario: Claim with a condition card only
- **WHEN** a reader opens a claim that has a card for its condition and none for its intervention
- **THEN** the page shows one card, with the condition's label and its definition one press away

#### Scenario: Claim with no card
- **WHEN** a claim has no card
- **THEN** the page shows no background section and no placeholder for one

### Requirement: A card shows how sure its link is
Each card made from a scored link SHALL show the score as a word and a percentage, with its reasons in the site's words available on request, and SHALL say when its term is broader than the claim's condition or intervention.

#### Scenario: Broader term
- **WHEN** a condition card is made from a broader term with a score of 0.9
- **THEN** the card says the term is broader than the claim's condition and shows "High match · 90%"

#### Scenario: Reason shown on request
- **WHEN** a reader asks why a card's term was chosen
- **THEN** the card says the registry files five of the claim's six trials under it

### Requirement: A card's words are its source's
A definition SHALL be shown as its source wrote it, marked as the source's words, and SHALL NOT be reworded by the site. The site SHALL add no explanation of a condition or a treatment of its own. The site SHALL word each card kind, reason and molecule kind code itself and SHALL fail the build on a code it has no wording for.

#### Scenario: Definition in the vocabulary's style
- **WHEN** a definition uses the vocabulary's own capitalised cross-references
- **THEN** the card shows it unchanged and names the vocabulary as its source

#### Scenario: Code without site wording
- **WHEN** the export carries a molecule kind the site has no wording for
- **THEN** the site build fails and names the code

### Requirement: Background is not advice and not evidence
The background section SHALL say that the cards describe terms, are not about the claim's evidence and are not medical advice. A card SHALL NOT state that the intervention treats the condition, and the site SHALL NOT place a card inside or beside the status.

#### Scenario: Card for a drug class with approved uses
- **WHEN** a card's definition mentions what a class of drugs is used for
- **THEN** the definition is shown as the source's words under the section's note, away from the status

### Requirement: Card sources are credited
Every page that shows a card SHALL credit the card's source in the terms the source asks for, including the version or date of a vocabulary. The footer's list of data sources SHALL include each source a published card comes from.

#### Scenario: Vocabulary that asks for its version to be stated
- **WHEN** a page shows a card from a vocabulary whose terms ask for the version used
- **THEN** the card names the vocabulary and its version or date
