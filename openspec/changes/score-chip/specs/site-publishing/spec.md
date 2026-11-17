# Spec Delta

## ADDED Requirements

### Requirement: A score is one chip that opens its meaning
Wherever a claim page or a trial page shows a score (a registry record's, a paper's or a trial's match to the claim, a background term's match, how sure the check of a reported statement is, a lower-band reading), it SHALL be drawn as the same chip: the band in words and the percentage, in sight, with nothing to press before either is read. The chip SHALL open a panel, on hover with a mouse, on a press and from the keyboard, that says what the score is about and that it says nothing about the treatment. The chip's text SHALL say what was matched ("Match to this claim: high, 92%"); the opening words MAY be left undrawn where the row itself says what is matched, and SHALL then remain for a screen reader and on paper. A possible record's chip SHALL say "Possible match" in sight. A lower-band reading's chip SHALL say "Low confidence" in words, and the sentence that it does not decide the status SHALL stay in sight beside it. No colour, fill, meter or mark SHALL say how high a score is. This replaces the requirement "A match score reads as a note about the match".

#### Scenario: Matched registry record
- **WHEN** a claim page lists a registry record matched at 0.92
- **THEN** a chip at the end of its title's line reads "High, 92%", a screen reader hears "Match to this claim: high, 92%", and opening it gives how the record was read and that the score says nothing about whether the treatment works

#### Scenario: Possible registry record
- **WHEN** a claim page lists a candidate scored 0.31
- **THEN** its chip reads "Possible match: low, 31%" in sight, before its phase and state

#### Scenario: Background term
- **WHEN** "At a glance" shows a condition matched to a vocabulary term at 0.98
- **THEN** the chip stands beside the row's value and reads "High, 98%", and the row's disclosure line no longer carries the score

#### Scenario: Lower-band reading
- **WHEN** a claim's evidence stage was read at 0.41 and not confirmed
- **THEN** the chip is outlined in dashes and reads "Low confidence · 41%", and "Not confirmed, so it does not decide the status." is in sight without opening anything

#### Scenario: On a phone
- **WHEN** a chip is pressed at 375 pixels wide
- **THEN** its press area is at least 44 pixels tall and the panel opens within the screen

### Requirement: Only a score is drawn as a score chip
Words that say how a background term was found and carry no percentage SHALL open the same panel as a score chip but SHALL NOT be drawn with the chip's outline. Inside a score chip the percentage SHALL be set apart from the band's words in the markup, and the text read out and printed SHALL remain the whole phrase.

#### Scenario: A drug row in "At a glance"
- **WHEN** a treatment's drug record was found by its exact name and its kind term matched at 0.98
- **THEN** "Drug record: by exact name" is drawn as plain underlined words that open a panel, and "Kind term: high, 98%" is drawn as a chip

