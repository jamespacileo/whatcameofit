# Spec Delta

## ADDED Requirements

### Requirement: A published pair has a page
Each pair in the bundle SHALL have a page at `/{address}` that shows its intervention and condition, its status with the events that produced it, each supporting trial with the arms that test the intervention, the registry's facts, its events, papers and posted results, and the history of the status.

#### Scenario: A pair with two trials
- **WHEN** a reader opens the page of a pair two trials support
- **THEN** the page shows the status, the events that produced it, and both trials with their arms and registry facts

#### Scenario: An address no pair has
- **WHEN** a reader opens an address the bundle does not hold and no claim had
- **THEN** the not-found page is shown

### Requirement: A pair page shows how sure each match is
A pair page SHALL show whether a person checked the pair, and the score and reasons of any match no rule holds as sure. It SHALL carry no verdict wording and SHALL NOT present a trial as a treatment option.

#### Scenario: An intervention keyed by a model's reading
- **WHEN** the pair's intervention was keyed by a decision model at 0.93
- **THEN** the page shows the score and that no person checked it

### Requirement: Every pair's files are rendered on request
The build SHALL make no file per pair. Every pair's page, open data record, embed and oEmbed description SHALL be rendered on request from the pair's file in the deployment's bundle version, by the shared renderers, into the frames the build leaves, and cached for no longer than a day. A pair's card addresses SHALL answer with the site's own card. The build's file count SHALL not grow with the number of pairs.

#### Scenario: Any pair
- **WHEN** a reader opens a pair's address, its record, its embed or its oEmbed description
- **THEN** each is made from the pair's file, with the page's canonical address, preview and oEmbed link, and the embed's footer notices

#### Scenario: The shared renderer is the page
- **WHEN** one pair's file is rendered by the shared renderer and served on request in a test
- **THEN** the two pages' contents are equal

#### Scenario: A pair's picture
- **WHEN** a pair's card address is asked for
- **THEN** the site's own card answers, and no picture is drawn per pair

#### Scenario: Searching by a treatment's name
- **WHEN** a reader searches the lookup box for a treatment's name
- **THEN** the pairs are found from the lookup file and the search detail, with no index built per pair

#### Scenario: A file that does not fit its schema
- **WHEN** the file read on request fails its validator
- **THEN** the reader gets the site's error page, and nothing from the file is shown

### Requirement: Old addresses answer
A claim's address whose pair is published SHALL answer with a permanent redirect to the pair's address. An archived claim's address SHALL answer 410 as before. A claim with no pair SHALL keep its page until the operator decides it.

#### Scenario: A moved claim
- **WHEN** a reader opens a claim slug the moved-addresses file maps to a pair
- **THEN** the answer is a 301 to that pair's address

#### Scenario: A claim whose slug equals its pair's address
- **WHEN** the two are the same
- **THEN** the pair page is served with no redirect

### Requirement: Listing pages list pairs
The home page, an intervention's page, a condition's page, a topic's page, the topics page, a clinical category's page and the changes feed SHALL list published pairs from the bundle. No listing SHALL show a pair the bundle does not hold.

#### Scenario: A condition's page
- **WHEN** a reader opens a condition with four published pairs
- **THEN** the page lists four pairs, each with its intervention and status

### Requirement: The extension's index keeps its shape
`/lookup.json` SHALL keep the keys the released extension reads, with each entry naming a pair's address.

#### Scenario: The released extension reads the new index
- **WHEN** the extension's tests run against an index made from the small bundle
- **THEN** they pass without a change to the extension

### Requirement: The lookup file keyed by pair
`/lookup/2.json` SHALL list every published pair under `pairs`, keyed by its address, with the same words as `/lookup.json` under the names a pair has (`title`, `condition`), and no field that only a claim had. It SHALL be one static file under 25 MiB at 30,000 pairs. The site's lookup box, its search and the lookup Worker SHALL read it; `/lookup.json` SHALL be built beside it, unchanged, until an extension release reads version 2.

#### Scenario: Both versions hold the same pairs
- **WHEN** the site is built from the small bundle
- **THEN** both files list every pair, and each pair's words in version 2 equal its words in version 1

#### Scenario: The box reads version 2
- **WHEN** a reader searches in the lookup box
- **THEN** the box reads `/lookup/2.json` and the search detail, and not `/lookup.json`

### Requirement: Pages show names, never codes
No page SHALL show a code where a name belongs: a MeSH descriptor's id, a tree number, a substance code or an intervention key stays in addresses and data files. A step of a path with no name in the bundle SHALL be left out rather than shown as its code.

#### Scenario: A condition's page
- **WHEN** a reader opens a condition's or a clinical category's page
- **THEN** the page names the condition and where it sits in MeSH, and shows neither its descriptor id nor a tree number

### Requirement: Every treatment, condition and group has a knowledge card
A treatment's, a condition's and a group's page SHALL open with a knowledge card built from fixed slots: what kind of thing it is, its facts, and one path for each place it sits in each tree that classifies it, each tree and level named in the site's words. A slot the bundle does not fill SHALL be left out, never filled from another source, and a card SHALL carry no verdict wording and no fact that implies a treatment works or is available.

#### Scenario: A condition in two branches of MeSH
- **WHEN** a condition's descriptor sits under two branches
- **THEN** its card shows a path for each branch, each step that has a page linked

#### Scenario: A treatment with no kind
- **WHEN** the rule gives a treatment no kind of treatment
- **THEN** its card shows no place in that tree

### Requirement: Treatments and conditions can be browsed by each of their trees
The site SHALL have a treatments index and a conditions index listing every tree on that side (conditions: body system from MeSH and health topic; treatments: kind of treatment, therapeutic use from WHO ATC with its credit, drug class, pharmacological action and combinations), each tree browsable from its top with the number of pairs beneath every node, and a page per node made on request from the lab's file for it.

#### Scenario: A drug class
- **WHEN** a reader opens a drug class's node
- **THEN** the page shows its card, its path in each tree it sits in, its narrower nodes with counts, and every pair whose treatment is a member at or beneath it

### Requirement: A reader can pick several treatments and conditions at any level
The explore page SHALL let a reader pick any number of nodes from any tree on either side by name, and list the pairs that match: a node includes everything beneath it, picks within one tree match any of them, picks in different trees must all match. The picks SHALL live in the address, the filtering SHALL run in the reader's browser from one cached file with no database read, and the page SHALL not be indexed with picks in its address.

#### Scenario: A class and a condition
- **WHEN** a reader picks a drug class and a condition
- **THEN** the page lists the pairs whose treatment is in the class and whose condition is at or beneath the condition, with counts beside the other choices
