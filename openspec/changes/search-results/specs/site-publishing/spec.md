## ADDED Requirements

### Requirement: A search is answered with its closest match first
A search typed in the lookup box SHALL be answered with every matching claim on one row each: its status in words, its place on the path, when it was first reported, its headline as a link, the treatment and what it is claimed for, and its topic. Matches SHALL be ordered by a fixed rule over the words they hold: the searched words side by side, then all of them, in the claim's own headline, then in a report's headline, then in the treatment and condition, the search index's order breaking a tie. The first SHALL be labelled the closest match. A word search SHALL NOT draw any one claim as the full answer a tracked article gets. The searched words SHALL be marked where they stand in a match. The answer SHALL end with a link to the page of each topic among the matches. No score SHALL be shown, and no mark, colour or order SHALL rank a treatment.

#### Scenario: Several matches
- **WHEN** a reader searches for "regrowing teeth" and one matching claim's headline says it "regrows teeth" while the search index lists another first
- **THEN** the claim whose headline holds the words side by side is first, labelled "Closest match", with its status in words
- **AND** the other matches follow one to a row, each with its status in words

### Requirement: On the home page a search answers in the list's place
On the home page a search's answer SHALL stand in the place of the day-by-day list, in the same sheet, until the reader clears it or asks something else, and the list SHALL come back unchanged when it is cleared. Under the box one line SHALL say where the answer is. The answer SHALL say how many claims match once, beside the one control that clears the search. Where the matches belong to two topics or more, they SHALL be counted by topic, under the answer's heading and, on a wide screen, in the side column, and each topic SHALL narrow the answer to its matches and be kept in the page's address. On any other page the same answer SHALL stand under the box.

#### Scenario: Clearing a search
- **WHEN** a reader presses "Clear search" beside the answer's count
- **THEN** the box is empty, the page's address carries no words, and the day-by-day list is shown as before

#### Scenario: Narrowing by topic
- **WHEN** a search matches claims in two topics and the reader presses one topic in the side column
- **THEN** only that topic's matches are shown, the answer says how many of all the matches they are, and the page's address names the topic

### Requirement: A search says what each match was found in
Under each match a search SHALL name every report headline and trial title of that claim that holds the searched words, up to a fixed number, each with its kind in words, the matched text with the words marked, and where it is from: for a report the outlet's name, its icon where the site holds one, and the date; for a trial the registry, the identifier and the phase. Every result SHALL remain a claim, led by its status.

#### Scenario: A report headline holds the words
- **WHEN** a reader searches for "regrowing teeth" and a matching claim's report is headlined "New drug to regrow lost teeth"
- **THEN** under that claim a line reads "Report headline" with the headline quoted, "regrow" and "teeth" marked, the outlet's icon and name, and the report's date

### Requirement: An exact headline or a trial identifier is answered with that thing first
Words that are the whole headline of a tracked report SHALL put that report's claim first: the answer SHALL say a tracked report has this headline, show the report with the words marked, then the claim drawn as a tracked article's answer is drawn. A search that is a trial registry's identifier SHALL be answered from the trials matched to tracked claims, not from the word search: the trial's registry record, then each claim it is matched to, and a sentence saying a trial on record is not a treatment option. An identifier with no trial on record SHALL be answered with a sentence saying so and, where the registry's address is built from the identifier alone, a link to the record on the registry.

#### Scenario: A trial identifier
- **WHEN** a reader searches for "NCT01814436"
- **THEN** the answer shows that trial's registry record and the one claim it is matched to, and no claim that only shares the prefix "NCT"

#### Scenario: An identifier not on record
- **WHEN** a reader searches for an identifier no tracked claim has
- **THEN** the answer says no trial with that identifier is matched to a claim tracked here, and links to it on its registry

### Requirement: A search with no result points to the link
A search that finds no tracked claim SHALL say that nothing tracked here matches the words, in wording that cannot be read as a claim's status, and SHALL say that pasting the article's link is the way to check a story.

#### Scenario: No match
- **WHEN** a reader searches for words no tracked claim holds
- **THEN** the answer reads "Nothing tracked here matches" with the words, and names pasting the article's link
