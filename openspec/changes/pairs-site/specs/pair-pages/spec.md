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
