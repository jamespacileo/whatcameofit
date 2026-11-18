# Spec Delta

## ADDED Requirements

### Requirement: The record band has three tones and the status card is one of them
On a claim page at a width where the section list stands beside the sheet, the band SHALL be drawn in three tones of navy: the sides, a lighter main column aligned with the sheet below it, and the status card lighter still. The status card SHALL NOT be white on a screen in either theme. Text and marks inside the card SHALL meet 4.5:1 against the card, and a panel opened from the card SHALL be drawn in the page's own colours. On paper the band and the card SHALL have no fill.

#### Scenario: Wide screen, light theme
- **WHEN** a reader opens a claim page at 1400 pixels wide in the light theme
- **THEN** the title stands on a column lighter than the band's sides, the status card is a lighter navy with white lettering, and the status label's info panel opens white with dark lettering

#### Scenario: Phone
- **WHEN** the page is read at 375 pixels wide
- **THEN** the band is one navy and the status card is the lighter tone on it

### Requirement: At a glance is two columns on a wide screen
From 60rem wide, the terms of "At a glance" SHALL be laid out in two columns, each term a cell with its label over its value. A cell whose card is open SHALL take the full width. Below 60rem the terms SHALL be one column.

#### Scenario: Two terms
- **WHEN** a claim has a treatment and a condition and the page is 1400 pixels wide
- **THEN** the two stand side by side, and opening "Why this term" on one gives that term the full width
