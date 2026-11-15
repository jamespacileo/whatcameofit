# Spec Delta

## ADDED Requirements

### Requirement: Background cards on the claim page
A claim page SHALL show the claim's background cards in an "At a glance" section, placed before the record in brief: a framed list of rows, each a label and a one-line value, for the treatment (its name and other names), the kind of treatment (a kind card's term), the kind of molecule (a drug card's kind of molecule and what its record says the drug acts on), a target (labelled "Gene named", or "Acts on" when the drug's record names it) and the condition the claim is for (its words), followed by the claim's own facts (first reported, evidence when first reported, records of studies). A row whose card is missing SHALL be left out, except the treatment and the condition, which come from the claim. A row with a card SHALL have one disclosure, closed until asked for, whose summary shows the card's score in sight, and which opens to the card: its label, its definition marked as the source's words, the source's name, a link to the source's record, the date the record was read, and the score's reasons. The section's note on what the cards are SHALL be at most three sentences with a link to the method page, and SHALL be shown only when the claim has a card. Decided by the operator on 2026-11-15, from the knowledge-card sketches (`.impeccable/mocks/knowledge-card/`) and, the same day, after a critique of the first build (`.impeccable/critique/`), which found the open cards made the section three screens long on a phone.

#### Scenario: Claim with a condition card only
- **WHEN** a reader opens a claim that has a card for its condition and none for its intervention
- **THEN** "At a glance" shows the treatment's name and the condition's words, the condition row has one closed disclosure whose summary reads "High match · 100%", and there is no kind, molecule or target row

#### Scenario: Claim with no card
- **WHEN** a claim has no card
- **THEN** "At a glance" shows the treatment, the condition and the claim's facts, with no disclosure and no note on cards

### Requirement: The band names what the treatment is
When a background card gives the treatment's kind or a target, the record band SHALL end with one row, ruled off under the title and the status, naming only those: the kind of molecule from a drug card, or else the kind of treatment from a kind card, and a target, each under the same label as its row in "At a glance" and each a link down to that row with a visible cue that it is one. The row SHALL NOT repeat the treatment's name or the condition, which the headline gives, and SHALL show no score, definition or reason beside the status: the score of each value is in sight on its row. Decided by the operator on 2026-11-15 after the critique, replacing a first build that showed scores in the band.

#### Scenario: Device with a kind card
- **WHEN** a reader opens a device claim whose kind card scores 0.81 and which has a condition card
- **THEN** the band's row reads "Kind of treatment" with the kind's term and no percentage, and pressing it moves to the kind row of "At a glance", whose summary reads "High match · 81%"

#### Scenario: Claim with only a condition card
- **WHEN** a claim's only card is for its condition
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
