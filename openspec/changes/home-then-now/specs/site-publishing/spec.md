# Spec Delta

## ADDED Requirements

### Requirement: The home page draws one claim, reported and on record
Under its box the home page SHALL draw one published claim, chosen by the site's rule for its example and never by hand: the earliest report's title as a quotation with its outlet and its day, the number of whole years between that day and the day the registries were last checked, and the claim's status as the site labels it, with its place on the path and the day of its latest record. The card SHALL lead to the claim's page. The years SHALL NOT be stated for a report under a year old. The card SHALL NOT be drawn below 40rem. The home page's title and section headings SHALL be set in the heading face.

#### Scenario: A report of five years ago
- **WHEN** the example claim was first reported on 31 March 2021 and the registries were last checked on 17 November 2026
- **THEN** the card says "5 years on" between the outlet's title and the claim's status

#### Scenario: On a phone
- **WHEN** the home page is read at 375 pixels wide
- **THEN** the card is not drawn and a row of the list starts on the first screen

### Requirement: The home page's card is drawn once, in the order it is read
When the home page opens, the card's arrow SHALL be drawn from the report to the record and the marker SHALL then land on the claim's place with one ring, once. Every word of the card SHALL be readable from the first paint. With reduced motion asked for, with no script and on paper the card SHALL be shown in its finished state and nothing SHALL move.

#### Scenario: Reduced motion
- **WHEN** a reader who has asked for reduced motion opens the home page
- **THEN** the arrow and the marker are drawn whole and nothing moves

