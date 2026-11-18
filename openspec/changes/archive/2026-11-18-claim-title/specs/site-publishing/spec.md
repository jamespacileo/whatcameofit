# Spec Delta

## ADDED Requirements

### Requirement: A claim page is titled by its claim
The title of a claim page SHALL be the claim's intervention followed by its indication, each worded as the record gives it, with the intervention the more prominent. The page SHALL NOT set the claim's headline, or the title of any news report, as its own title. A news report's title SHALL appear on the page only as a quotation with its outlet and date.

#### Scenario: A claim reported as an approval
- **WHEN** a reader opens the page of a claim for erenumab, for preventing migraine, whose reports say it was approved and whose status is Phase 3 trial
- **THEN** the title reads "erenumab" and under it "Preventing migraine in people who have at least four migraines a month", and the words "EU approves" appear only inside a quoted report's title

#### Scenario: Read aloud
- **WHEN** a screen reader reads the title
- **THEN** it reads the intervention, "for", and the indication as one heading

#### Scenario: The indication is readable on paper

- **WHEN** a reader prints the intervention-and-indication heading from either screen theme
- **THEN** the printed heading distinguishes the indication clearly on paper with background graphics disabled
