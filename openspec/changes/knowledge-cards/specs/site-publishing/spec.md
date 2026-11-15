# Spec Delta

## ADDED Requirements

### Requirement: Background cards on the claim page
A claim page SHALL show the claim's background cards in an "At a glance" section, placed before the record in brief: a framed list of rows, each a label and its value, for the treatment (its name, its other names and an exact or broader card), the kind of treatment (a kind card), the drug record (a drug card), a target (labelled as named in the treatment's name or as what the drug's record says it acts on) and the condition the claim is for (its words and its card), followed by the claim's own facts (first reported, evidence when first reported, records of studies). A row whose card is missing SHALL be left out, except the treatment and the condition, which come from the claim. Each card SHALL show its label, its definition open and marked as the source's words, the source's name, a link to the source's record and the date the record was read. The section's note on what the cards are SHALL be shown only when the claim has a card. Decided by the operator on 2026-11-15, from the knowledge-card sketches (`.impeccable/mocks/knowledge-card/`), replacing a folded "Background" section after the records.

#### Scenario: Claim with a condition card only
- **WHEN** a reader opens a claim that has a card for its condition and none for its intervention
- **THEN** "At a glance" shows the treatment's name, and the condition's words with its card and the definition open, and no kind, drug or target row

#### Scenario: Claim with no card
- **WHEN** a claim has no card
- **THEN** "At a glance" shows the treatment, the condition and the claim's facts, no card and no note on cards

### Requirement: The band names what the treatment is
When a claim has at least one background card, the record band SHALL end with one row, ruled off under the title and the status, naming the treatment, its kind (a drug card's kind of molecule, or else a kind card's label) when a card gives it, a target when a card gives it, and the condition, each a link to its row in "At a glance". A value taken from a card SHALL carry the card's score as a word and a percentage, or what stands for it on a card made by rule. The row SHALL hold no definition and no reason, and SHALL NOT sit inside the status panel.

#### Scenario: Device with a kind card
- **WHEN** a reader opens a device claim whose kind card scores 0.81 and which has a condition card
- **THEN** the band's row reads Treatment, Kind with "High match · 81%", and Claimed for, and pressing Kind moves to the kind row of "At a glance"

#### Scenario: Claim with no card
- **WHEN** a claim has no card
- **THEN** the band has no such row

### Requirement: A card shows how sure its link is
Each card made from a scored link SHALL show the score as a word and a percentage, with its reasons in the site's words available on request, and SHALL say when its term is broader than the claim's condition or intervention, when it is the kind of intervention and not the intervention itself, and when a target is one the report names and not one a drug's record gives.

#### Scenario: Kind card
- **WHEN** an intervention card is made from a kind link with a score of 0.9
- **THEN** the card says its term is the kind of treatment this is, not the treatment itself, and shows "High match · 90%"

#### Scenario: Registry type as a reason
- **WHEN** a reader asks why a kind card's term was chosen and the registry lists the intervention as a device in three of the claim's trials
- **THEN** the card says so in the site's words

#### Scenario: Target the report names
- **WHEN** a target card is made from a gene named in the intervention
- **THEN** the card says the gene is named in the intervention's name, shows the score, and does not say the intervention works through it

#### Scenario: Broader term
- **WHEN** a condition card is made from a broader term with a score of 0.9
- **THEN** the card says the term is broader than the claim's condition and shows "High match · 90%"

#### Scenario: Reason shown on request
- **WHEN** a reader asks why a card's term was chosen
- **THEN** the card says the registry files five of the claim's six trials under it

### Requirement: A card's words are its source's
A definition SHALL be shown as its source wrote it, marked as the source's words, and SHALL NOT be reworded by the site. The site SHALL add no explanation of a condition or a treatment of its own. The site SHALL word each card kind, reason, registry type and molecule kind code itself and SHALL fail the build on a code it has no wording for.

#### Scenario: Definition in the vocabulary's style
- **WHEN** a definition uses the vocabulary's own capitalised cross-references
- **THEN** the card shows it unchanged and names the vocabulary as its source

#### Scenario: Code without site wording
- **WHEN** the export carries a molecule kind the site has no wording for
- **THEN** the site build fails and names the code

### Requirement: Background is not advice and not evidence
"At a glance" SHALL say that the cards describe terms, are not about the claim's evidence and are not medical advice. A card SHALL NOT state that the intervention treats the condition, and the site SHALL NOT place a card, or any definition or reason, inside the status panel.

#### Scenario: Card for a drug class with approved uses
- **WHEN** a card's definition mentions what a class of drugs is used for
- **THEN** the definition is shown as the source's words in "At a glance", with the section's note, and nothing of it is in the status panel

### Requirement: Card sources are credited
Every page that shows a card SHALL credit the card's source in the terms the source asks for, including the version or date of a vocabulary. The footer's list of data sources SHALL include each source a published card comes from.

#### Scenario: Vocabulary that asks for its version to be stated
- **WHEN** a page shows a card from a vocabulary whose terms ask for the version used
- **THEN** the card names the vocabulary and its version or date
