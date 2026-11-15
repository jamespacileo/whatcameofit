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

### Requirement: A search says what each match was found in
Under each match a search SHALL name every report headline and trial title of that claim that holds the searched words, up to a fixed number, each with its kind in words, the matched text with the words marked, and where it is from: for a report the outlet's name, its icon where the site holds one, and the date; for a trial the registry, the identifier and the phase. Every result SHALL remain a claim, led by its status.

#### Scenario: A report headline holds the words
- **WHEN** a reader searches for "regrowing teeth" and a matching claim's report is headlined "New drug to regrow lost teeth"
- **THEN** under that claim a line reads "Report headline" with the headline quoted, "regrow" and "teeth" marked, the outlet's icon and name, and the report's date

### Requirement: An exact headline or a trial identifier is answered with that thing first
Words that are the whole headline of a tracked report SHALL put that report's claim first, and the answer SHALL say a tracked report has this headline. A search that is a trial registry's identifier SHALL be answered from the trials matched to tracked claims, not from the word search: the trial's registry record, then each claim it is matched to, and a sentence saying a trial on record is not a treatment option. An identifier with no trial on record SHALL be answered with a sentence saying so.

#### Scenario: A trial identifier
- **WHEN** a reader searches for "NCT01814436"
- **THEN** the answer shows that trial's registry record and the one claim it is matched to, and no claim that only shares the prefix "NCT"

#### Scenario: An identifier not on record
- **WHEN** a reader searches for an identifier no tracked claim has
- **THEN** the answer says no trial with that identifier is on record here
