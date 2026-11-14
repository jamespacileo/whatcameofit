## ADDED Requirements

### Requirement: A wait is marked by the mark, and never delays the answer
While the popup checks a page, searches the registry or reads an image, it SHALL show one line: the mark, then what is being waited for. For a reader who has not asked for reduced motion the capsule SHALL pass beneath the glass for as long as the wait lasts; with reduced motion the mark SHALL be still. The answer SHALL replace the line as soon as it is ready and SHALL NOT wait for the motion.

#### Scenario: Checking a page
- **WHEN** the popup is opened and the page is being checked
- **THEN** the view is one line holding the mark and "Checking this page…"

### Requirement: The tick is drawn for a claim just followed
When a reader presses "Keep me up to date", the line that replaces the control SHALL show a tick that is drawn, for a reader who has not asked for reduced motion. When the popup is opened on a claim already followed, the tick SHALL be shown without motion.

#### Scenario: Just followed
- **WHEN** a reader presses "Keep me up to date" on a tracked claim
- **THEN** the line reads "You follow this claim." and its tick is marked to be drawn

#### Scenario: Already followed
- **WHEN** the popup is opened on a claim the reader follows
- **THEN** the tick is not marked to be drawn
