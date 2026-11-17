# Delta for site-publishing

## ADDED Requirements

### Requirement: The box and its answer stay in step
On the home page, once the box has answered, nothing the page sets under the box SHALL be drawn between the box and its answer until the search is cleared. A field emptied by the reader SHALL leave no answer and no searched words in the page's address. Each search looked up, and a search cleared, SHALL be a step in the browser's history, and going back or forward SHALL draw that step's answer again. Narrowing an answer by topic SHALL NOT add a step. A pasted article address SHALL NOT enter the page's address.

#### Scenario: An answer under the box
- **WHEN** a reader pastes the address of a tracked article on the home page
- **THEN** the answer follows the field and its one line of help, and the words to try, the tally and the example are not drawn

#### Scenario: The field emptied
- **WHEN** a reader with an answer on screen empties the field with Escape, its cross or the delete key
- **THEN** the answer is gone, the list is back in its place, and the address holds no searched words

#### Scenario: Back
- **WHEN** a reader searches for "tooth regrowth" and presses Back
- **THEN** the page stays, the field is empty and the list is back; Forward draws the answer for "tooth regrowth" again

#### Scenario: Going to the answer
- **WHEN** a search on the home page answers in the list's place
- **THEN** the line under the box ends in a link, and taking it puts the reader on the answer's heading

### Requirement: A failure offers the same question again
A search or a lookup that could not be read SHALL say so, SHALL offer a control that asks the same question again, and SHALL say where every tracked claim is listed. It SHALL NOT tell the reader to type in the box.

#### Scenario: The lookup file cannot be read
- **WHEN** a reader pastes an article's address and the lookup file cannot be fetched
- **THEN** the page says the lookup is not available right now, offers "Try again", and links to the topics

### Requirement: The box says where a pasted link goes
Under the field, wherever the box is drawn, one line SHALL say that a pasted link is compared in the reader's browser. Where the site is built with no registry search it SHALL say the link is sent nowhere; where it is built with one it SHALL say the link is sent only if the reader asks for that search.

#### Scenario: No registry search
- **WHEN** the site is built with no lookup service
- **THEN** the line reads "A pasted link is compared in your browser and sent nowhere."

### Requirement: An untracked article is offered a date to come back on
An article the site does not track SHALL be offered a calendar file, made on the reader's device, to check it again in six months or a year, whether or not a registry search is offered or asked for.

#### Scenario: Not tracked, no registry search
- **WHEN** a reader pastes the address of an article the site does not track, on a site built with no lookup service
- **THEN** "Check again later" follows the answer with both dates
