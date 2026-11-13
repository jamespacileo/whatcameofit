# Spec Delta

## ADDED Requirements

### Requirement: A promise on the card is marked as a promise
When a claim has a dated promise, the card SHALL show the year promised by on the site's pale amber with a dashed rule, in all three shapes. No other part of the card SHALL use that colour. A claim with no dated promise SHALL have a card with no amber on it.

#### Scenario: Claim with a dated promise
- **WHEN** a claim's latest promise names 2025
- **THEN** each shape of its card shows "Promised by 2025" on pale amber, and the status in the site's blue

#### Scenario: Claim with no dated promise
- **WHEN** a claim has no promise with a date
- **THEN** its card shows no "Promised by" fact and no amber

### Requirement: The claim page shows the card it offers
The claim page SHALL show the square card beside the sentence to copy, with a text alternative built from the same facts as the card.

#### Scenario: Reader looks before sharing
- **WHEN** a reader reaches "Pass it on" on a claim page
- **THEN** the square card is visible beside the sentence, and a screen reader is given the card's facts as text
