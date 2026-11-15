## ADDED Requirements

### Requirement: A search is answered with its best match first
A search typed in the lookup box SHALL be answered with its best match drawn as a tracked article's answer is drawn: the status in words, its place on the path, the claim's headline, what the status means, when it was first reported and a link to the claim's page, labelled as the best match. Every other match SHALL follow on one line each with its status in words, its place on the path, its headline as a link, the treatment and what it is claimed for, its topic and when it was first reported. The searched words SHALL be marked where they stand in a match. The answer SHALL end with a link to the page of each topic among the matches. Matches SHALL keep the search index's order, and no mark, colour or order SHALL rank a treatment.

#### Scenario: Several matches
- **WHEN** a reader searches for "tooth regrowth" and three claims match
- **THEN** the first is drawn with its status, its place on the path and what the status means, labelled as the best match
- **AND** the other two follow one to a line, each with its status in words

### Requirement: On the home page a search answers in the list's place
On the home page a search's answer SHALL stand in the place of the day-by-day list, in the same sheet, until the reader clears it or asks something else, and the list SHALL come back unchanged when it is cleared. Under the best match it SHALL show the report row the list draws for that claim. Under the box one line SHALL say how many claims match and where the answer is, with a control that clears the search. Where the matches belong to two topics or more, the side column SHALL count them by topic, and each topic SHALL narrow the answer to its matches.

#### Scenario: Clearing a search
- **WHEN** a reader presses "Clear" under the box after a search
- **THEN** the box is empty, the page's address carries no words, and the day-by-day list is shown as before

#### Scenario: Narrowing by topic
- **WHEN** a search matches claims in two topics and the reader presses one topic in the side column
- **THEN** only that topic's matches are shown, and the answer says how many of all the matches they are
