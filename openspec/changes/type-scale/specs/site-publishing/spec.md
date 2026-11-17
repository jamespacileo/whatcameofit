# Spec Delta

## ADDED Requirements

### Requirement: The shared stylesheet's font sizes come from one scale
Every font size in the site's shared stylesheet SHALL be one of the type scale's steps or named roles, a title's fluid size, or inherited. The steps and roles SHALL each be defined once. A build's tests SHALL fail when a rule writes a font size of its own. No text SHALL be drawn under 12 pixels.

#### Scenario: A new rule with its own size
- **WHEN** a rule is added to the shared stylesheet with `font-size: 0.9rem`
- **THEN** the site's tests fail and name the size

#### Scenario: A claim page
- **WHEN** a reader opens a claim page with every kind of section
- **THEN** its text is drawn in no more than ten sizes
