# Delta for site-publishing

## ADDED Requirements

### Requirement: The box and its answer stay in step
On the home page, once the box has answered, nothing the page sets under the box SHALL be drawn between the box and its answer until the search is cleared. A field emptied by the reader SHALL leave no answer and no searched words in the page's address.

#### Scenario: An answer under the box
- **WHEN** a reader pastes the address of a tracked article on the home page
- **THEN** the answer follows the field and its one line of help, and the words to try, the tally and the example are not drawn

#### Scenario: The field emptied
- **WHEN** a reader with an answer on screen empties the field with Escape, its cross or the delete key
- **THEN** the answer is gone, the list is back in its place, and the address holds no searched words

#### Scenario: Going to the answer
- **WHEN** a search on the home page answers in the list's place, on a screen 34rem wide or more
- **THEN** the line under the box ends in a link, and taking it puts the reader on the answer's heading

### Requirement: Search history redraws each answer
Each lookup and clear SHALL add one history step. Back and Forward SHALL restore that step's answer, chosen topic and loaded result pages. Changing the topic or loading more results SHALL update the current step. A pasted article address SHALL stay in page memory and SHALL NOT enter the page's address or saved history state.

#### Scenario: Back
- **WHEN** a reader searches for "tooth regrowth" and presses Back
- **THEN** the page stays, the field is empty and the list is back; Forward draws the answer for "tooth regrowth" again

#### Scenario: Back to a pasted link
- **WHEN** a reader pastes an article's address, clears its answer and presses Back in the same page
- **THEN** the field and answer return without putting the article's address in the page's address, and Forward clears them again

#### Scenario: A topic that first appears in a later batch
- **WHEN** the page opens a search address with a topic whose first match is after the first twenty claims
- **THEN** it reads enough results to draw the answer with that topic selected

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

### Requirement: A search's count is of every claim found
The count SHALL be the number of claim pages the index found. While more remain, the heading and the line under the box SHALL state how many are shown and how many were found. The list SHALL offer the next twenty and say how many remain. Each batch SHALL follow the existing rows without reordering them and put the reader on its first claim. A topic change SHALL preserve the pending batch, and a topic or batch that arrives late SHALL NOT replace a topic chosen or a search asked after it.

#### Scenario: More found than drawn
- **WHEN** the index finds 161 claims for "cancer" and the page draws 20
- **THEN** the count reads "First 20 of 161 tracked claims", and the list ends with "Show 20 more" over "141 more tracked claims hold these words."

#### Scenario: The next twenty
- **WHEN** the reader presses "Show 20 more"
- **THEN** forty claims are drawn, the first twenty where they were, the count reads "First 40 of 161 tracked claims", and the page has not moved

#### Scenario: All drawn
- **WHEN** the index finds 3 claims
- **THEN** the count reads "3 tracked claims"

#### Scenario: The topic changes while the next twenty are loading
- **WHEN** the reader asks for more results and chooses a topic before they arrive
- **THEN** the next batch is added once to the claims it was asked for, and the answer is drawn with that topic selected

### Requirement: An exact headline keeps the index count
An exact report headline's claim SHALL be shown first and SHALL count once if the index found it. An exact headline outside the index SHALL be shown above the indexed matches without changing their count.

#### Scenario: Exact headline among the later matches
- **WHEN** the index finds 40 claims, including the exact headline's claim in the second batch
- **THEN** the exact claim leads the first twenty, the count reads "First 20 of 40 tracked claims", and the next batch has the other twenty

### Requirement: A treatment suggested for another name says that name
Where the typed words are in none of a treatment's first name but in another of its names, its suggested row SHALL give the first name followed by the name the words are in.

#### Scenario: A brand name typed
- **WHEN** a reader types the start of a treatment's second name
- **THEN** the row reads the first name, then the second name in brackets

### Requirement: A result says where its claim stands right after its headline
In a search's answer each result SHALL give, in this order in the page itself, the claim's headline, where the claim stands, the treatment and what it is claimed for, and what the searched words were found in. On a screen narrower than 34rem these SHALL be drawn in that order in one column, with one report or trial named and the rest counted.

#### Scenario: A phone
- **WHEN** a reader on a phone searches for "cancer"
- **THEN** each result shows its status under its headline, before any report

### Requirement: A suggested row that opens a page is marked
A suggested row that opens a page SHALL end in an arrow and SHALL be named to a screen reader as opening its page. A row that searches in place SHALL have no arrow and SHALL be named to a screen reader as searching here.

#### Scenario: A topic and a condition
- **WHEN** a topic and a condition are offered for what is typed
- **THEN** the topic's row ends in an arrow and is named "Opens its page."; the condition's row has no arrow and is named "Searches here."

### Requirement: Topics beside a search count every claim found
Each topic and "All results" SHALL show the total claim pages the index found, without reading those pages for their counts. Picking a topic SHALL show its claims, loading the first twenty as needed. The answer SHALL show how many claims are drawn, the topic's total if more remain, and the total across all topics.

#### Scenario: More found than read
- **WHEN** the index finds 59 claims for "vaccine" and the page has read 20
- **THEN** the topics' counts add up to 59, and "All results" reads 59

#### Scenario: A topic with no claim among those read
- **WHEN** the reader picks a topic that holds 3 of the 59 claims, none of them among the 20 read
- **THEN** those 3 claims are read and shown, and the count reads "3 of 59 tracked claims, in" the topic's name

#### Scenario: A topic that holds more than twenty
- **WHEN** the reader picks a topic that holds 33 of the 59 claims
- **THEN** 20 are shown, the count reads "First 20 of 33 in" the topic's name ", of 59 tracked claims", and "Show 13 more" draws the rest of that topic's

### Requirement: The field's example words are chosen by rule
At build, the example SHALL use the first eligible claim in the site's example order. Its treatment name SHALL have one to three plain words, fit the field, appear in its own headline, and appear whole in no other claim's headline, treatment names, condition or report titles. A search for the words SHALL lead with that claim. If none qualifies, the field SHALL offer a link alone.

#### Scenario: The example searched
- **WHEN** a reader types the field's example words and looks them up
- **THEN** the closest match is the claim the words were chosen from

#### Scenario: No claim passes
- **WHEN** no published claim's treatment name passes the rule
- **THEN** the field's example reads "https://…" and no words

### Requirement: A searched word no claim holds is named
Where a search by words finds claims and the search index holds one of the words nowhere, neither whole, in another of its forms, nor as the start of a longer word, the answer SHALL name that word under its heading and say that the claims shown were found without it.

#### Scenario: A mistyped word
- **WHEN** a reader searches for "lung cancercancer"
- **THEN** the answer says no tracked claim holds “cancercancer”, and that the claims shown were found without that word

#### Scenario: The start of a word
- **WHEN** a reader searches for "canc", which starts a word that claims hold
- **THEN** no word is named

### Requirement: The suggestions have room and stand clear of the field's line
The suggestions SHALL start under the line that says where a pasted link goes. Where they do not fit between there and the bottom of what the reader can see, the box SHALL be brought to the top of the screen. The panel's height SHALL be taken from the part of the screen not covered by an on-screen keyboard.

#### Scenario: The box low on the screen
- **WHEN** a reader types in the home page's box at 1280 by 720
- **THEN** the box moves to the top of the screen and every suggested row is in view

### Requirement: On a touch screen a typed search puts the reader on its answer
On a screen worked by touch, a search by words that has answered SHALL move the reader from the field to the answer's heading. On a screen narrower than 34rem the line under the box that says where the answer is SHALL NOT be drawn, and SHALL still be announced to a screen reader.

#### Scenario: A phone
- **WHEN** a reader on a phone types "cancer" and sends it
- **THEN** the field is left, the keyboard closes, the answer's heading follows the field's line of help, and the reader is on that heading

### Requirement: A search is named in the page's title
While a search by words is answered the page's title SHALL begin with the searched words, and SHALL return to the page's own title when the search is cleared. A pasted article address SHALL NOT enter the title.

#### Scenario: Searched and cleared
- **WHEN** a reader searches for "vaccine" and then clears the search
- **THEN** the title begins “vaccine” while the answer is shown, and is the page's own title afterwards
