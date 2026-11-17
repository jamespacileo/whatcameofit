# Spec Delta

## ADDED Requirements

### Requirement: A control a script works holds its place while the page loads
A control that only a script can work SHALL take its place in the page from the first paint and SHALL be out of sight, and out of reach of a keyboard and a screen reader, until its script is ready. Where scripts do not run, the control SHALL be left out of the page.

#### Scenario: The home page while its scripts load
- **WHEN** a reader opens the home page and its scripts have not yet run
- **THEN** the kind field, the span field, the status field, the list tabs and the words to try each hold their place, and nothing below them moves when they come into sight

#### Scenario: A reader without scripts
- **WHEN** a reader opens the home page in a browser that runs no scripts
- **THEN** none of those controls is shown and none leaves a gap

### Requirement: Text holds its place when a face arrives
Each of the site's faces SHALL name a fallback drawn from a font already on the device and scaled to the face's widths and line height. A device without that font SHALL use the next font named.

#### Scenario: A slow connection
- **WHEN** a page is painted before a face has arrived
- **THEN** its text is drawn in the fallback, and its lines keep their height when the face takes over

### Requirement: A page a reader points at is fetched ahead
The site SHALL fetch a page of its own when a reader points at or focuses a link to it, and SHALL NOT fetch ahead a page on another site.

#### Scenario: Pointing at a claim
- **WHEN** a reader on the home page points at a claim's link
- **THEN** that claim's page is fetched before the link is pressed
