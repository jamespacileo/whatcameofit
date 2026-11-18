# Spec Delta

## MODIFIED Requirements

### Requirement: The record band has three tones and the status card is one of them
On a claim page at a width where the section list stands beside the sheet, the band SHALL be drawn in three tones of navy: the sides; one main surface, lighter than the sides, from the masthead to the sheet and as wide as the sheet; and the status card, which SHALL stand on that surface and SHALL be darker than the sides. The title and the status card SHALL stand on the same surface. Adjacent tones SHALL differ by at least 1.3:1. The main surface SHALL be darker than the accent. The status card SHALL NOT be white on a screen in either theme. Text and marks inside the card and on the main surface SHALL meet 4.5:1 against their ground, and a panel opened from the card SHALL be drawn in the page's own colours. Beside the card the title SHALL be set larger than the status label. On paper the band and the card SHALL have no fill.

#### Scenario: Wide screen, light theme
- **WHEN** a reader opens a claim page at 1400 pixels wide in the light theme
- **THEN** the title and the status card stand on one surface lighter than the band's sides and as wide as the sheet, the status card is a darker navy with white lettering, and the status label's info panel opens white with dark lettering

#### Scenario: A sentence-long headline
- **WHEN** a claim's headline is longer than 70 characters and the page is 1400 pixels wide
- **THEN** the title is set larger than the status label beside it

#### Scenario: Phone
- **WHEN** the page is read at 375 pixels wide
- **THEN** the band is one surface a step lighter than the masthead and the status card is the darker tone on it
