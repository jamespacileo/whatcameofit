## MODIFIED Requirements

### Requirement: Follow is explained and confirmed in sight
Where a claim page offers to follow, it SHALL say, beside the Follow control that stands with the page's reminders, what following does and that the list is kept in the reader's browser only. The page SHALL NOT repeat a Follow control with its words directly under the status, where the status's own Follow control already stands. Once the reader follows, the page SHALL say so in sight after the status, with a link to the list on the home page and that the list is kept in the reader's browser only, and the place beside the reminders SHALL say the same. Every Follow control on the page SHALL show the same state.

#### Scenario: Following from a claim page
- **WHEN** a reader presses Follow beside the status
- **THEN** every Follow control reads "Following", and a sentence after the status says the claim is listed on the home page, with a link there, and is kept in this browser only

#### Scenario: Before following
- **WHEN** a reader who does not follow the claim opens its page
- **THEN** the only Follow controls are the one beside the status and the one beside the reminders, and what following does is said beside the second
