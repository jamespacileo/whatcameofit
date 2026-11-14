## ADDED Requirements

### Requirement: Every status has a guide entry
The site SHALL publish a guide entry for each status a claim can have. The entry SHALL show the status's label, gloss and meaning from the same source the claim pages read, its place on the path where it has one, how many published claims have that status, and a link to the list of them. The build SHALL fail when a status has no entry.

#### Scenario: A status with claims
- **WHEN** eight published claims have the status "Phase 2 trial"
- **THEN** the entry for that status shows the label, gloss and meaning as a claim page words them, says eight claims have it, and links to those claims

#### Scenario: A status with no claim
- **WHEN** no published claim has the status "Origin paper retracted"
- **THEN** its entry is still published and says that no tracked claim has this status now

#### Scenario: A status is added without an entry
- **WHEN** the site is built and a status has no guide entry
- **THEN** the build fails and names the status

### Requirement: An entry says what a word does not tell the reader
Each guide entry SHALL state what the word means in one sentence, then what records it rests on, then what it does not tell the reader. An entry SHALL describe records and SHALL NOT say what a reader should do about their own care, whether a treatment works, or whether it is available. The build SHALL fail when an entry holds verdict wording or advice wording.

#### Scenario: A status entry
- **WHEN** a reader opens the entry for "Phase 3 trial"
- **THEN** it says a large late-stage trial in people has started, and says that this is not a result and not an approval

#### Scenario: Advice wording
- **WHEN** an entry's text says a reader should ask for, join or avoid something
- **THEN** the build fails and names the entry

### Requirement: An entry on how research is recorded cites its sources
An entry that states how trials, registries, regulators or journals work SHALL list at least one public source for it, each with its name, its address and the day it was checked. The build SHALL fail when such an entry has no source.

#### Scenario: Sources are listed
- **WHEN** a reader opens the entry for "Trial registry"
- **THEN** the page lists the sources its statements rest on, each linked and dated

#### Scenario: An entry without a source
- **WHEN** an entry on the research shelf is built with no source
- **THEN** the build fails and names the entry

### Requirement: An entry says whether a person has checked it
A guide entry that no person has checked SHALL carry a notice saying so, placed after the entry's answer and never before it.

#### Scenario: An unchecked entry
- **WHEN** an entry is published before the operator has read it
- **THEN** the page says it has not yet been checked by a person, under the one-sentence answer

### Requirement: An entry shows the word at work
A guide entry SHALL show up to three published claims to which its word applies now, in the same list form as a topic page, and SHALL link the rule that uses the word on the method page. When no published claim applies, the entry SHALL say so in one sentence.

#### Scenario: Claims to show
- **WHEN** a reader opens the entry for "No signal" and five published claims carry that note
- **THEN** three of them are listed, newest report first, with a link to the rest

### Requirement: The guide is reached from where a word is met
A claim page's status panel SHALL link to the entry for its status. The no-signal note SHALL link to its entry. The notice that a page has not been checked by a person SHALL link to its entry. Each status on the method page SHALL link to its entry. The sentence of meaning shown beside a status SHALL remain where it is.

#### Scenario: From a claim page
- **WHEN** a reader opens the status panel on a claim page whose status is "Preclinical only"
- **THEN** the panel holds the meaning as before and a link to the guide entry for that status

### Requirement: The guide has an index
`/guide` SHALL list every entry under its shelf, each with its title as the link and its one-sentence answer. Statuses SHALL be listed in path order, then those off the path. With scripting on, a field SHALL narrow the list as the reader types; without it every entry is listed.

#### Scenario: Finding a word
- **WHEN** a reader types "retract" in the field
- **THEN** the list is narrowed to the entries whose title or answer holds those letters

### Requirement: Readers cannot edit the guide
The guide SHALL be built from files held with the site. The site SHALL offer no means for a reader to add to or change an entry other than the corrections address.

#### Scenario: A reader finds an error
- **WHEN** a reader believes an entry is wrong
- **THEN** the page offers the corrections link, where one is configured, and nothing else
