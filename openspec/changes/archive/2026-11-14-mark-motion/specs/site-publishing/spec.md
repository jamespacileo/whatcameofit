## ADDED Requirements

### Requirement: The masthead's mark is drawn into the page and moves once a visit
Every page's masthead SHALL hold the reverse mark as a drawing in the page, with the same shapes as the generated reverse mark file. On the first page of a visit, for a reader who has not asked for reduced motion, the glass SHALL be lowered onto the capsule before the name's question mark is drawn and its dot lands, and the whole SHALL take no longer than two seconds. On later pages of the visit nothing in the masthead SHALL move on load. Hovering or focusing the name SHALL move only the capsule, which grows a little and settles. With reduced motion asked for, nothing in the masthead SHALL move. The mark SHALL be whole and in place from the first frame.

#### Scenario: The mark in the masthead
- **WHEN** any page is built
- **THEN** its masthead holds the mark as a drawing whose shapes are those of the reverse mark file

#### Scenario: A first page, then a second
- **WHEN** a reader opens one page and then another in the same visit
- **THEN** the glass, the question and the dot move on the first page and not on the second

### Requirement: A page or a search that finds nothing shows the path with no place marked
The not-found page, and a search with no result, SHALL show a drawing of the path's places with none of them marked and a glass at rest past the last. For a reader who has not asked for reduced motion the glass SHALL pass over the places once and come to rest; it SHALL NOT loop, and no place SHALL be marked at any moment. The drawing SHALL be hidden from screen readers, and the words beside it SHALL say what was not found.

#### Scenario: Unknown slug
- **WHEN** a reader opens an address with no page
- **THEN** the page says no page was found and shows the six places with none marked

#### Scenario: Search with no result
- **WHEN** a search finds nothing
- **THEN** the drawing is shown above the sentence that says so

### Requirement: The method page shows how a status is made as a drawing
Under its video the method page SHALL show a drawing in three parts: what was reported, what was recorded, and where that leaves the claim, with the status in words beside its place on the path. Its example SHALL be made up, and the page SHALL say so beside it. The drawing SHALL be complete without scripting, without motion and on paper. It SHALL move only when the reader presses its control, which SHALL be absent without scripting, with reduced motion asked for and on paper.

#### Scenario: The method page's drawing
- **WHEN** the method page is built
- **THEN** the drawing shows the status, its place on the path and the note that its records are made up, and its control starts hidden

### Requirement: Small drawings confirm a press
On a claim page, pressing "Follow" SHALL fill the bookmark, and for a reader who has not asked for reduced motion the bookmark SHALL land; it SHALL NOT move when a followed claim's page is opened. Saving a reminder SHALL be confirmed in the pill pressed, which SHALL read "Saved to your calendar" for about two seconds, SHALL tell a screen reader, and SHALL then offer its date again. A topic chip's drawing MAY be drawn again on hover or focus, by one technique for every topic. No drawing SHALL move on scroll.

#### Scenario: Following from a claim page
- **WHEN** a reader presses "Follow"
- **THEN** the pill reads "Following" with its bookmark filled

#### Scenario: A reminder is saved
- **WHEN** a reader presses "In a year"
- **THEN** the pill reads "Saved to your calendar", and two seconds later "In a year"
