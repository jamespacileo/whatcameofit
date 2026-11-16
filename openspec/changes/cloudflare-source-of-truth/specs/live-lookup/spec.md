# Spec Delta

## MODIFIED Requirements

### Requirement: A lookup keeps nothing it read
A lookup SHALL NOT store any text of an article or a post, or anything a reader's browser sent. It SHALL NOT create or approve a claim, an evidence event or a match. Where records from lookups are turned on, it SHALL store only what `on-demand-records` allows: a link lead for the article, the registry trials retrieved, and its reading awaiting the rules. It MAY record that a model was called and what it cost.

#### Scenario: Nothing of the text is kept
- **WHEN** a lookup finds a trial
- **THEN** no stored record holds any text of the article, and the numbers of claims, approved events and approved matches are unchanged

#### Scenario: Records turned off
- **WHEN** records from lookups are not turned on and a lookup finds a trial
- **THEN** the numbers of claims, entities, matches, articles and link leads stored are unchanged

### Requirement: The lookup service reads politely and keeps nothing
The service SHALL obey a site's robots.txt and SHALL NOT fetch an article when the rules forbid it or cannot be read. It SHALL NOT fetch a local or private address. It SHALL say why it cannot answer with a code the site words. It SHALL limit how many searches one reader and all readers together can make per minute. It SHALL NOT log an address, a text or an answer, and SHALL NOT store a text, an answer as the reader saw it, or anything that identifies the reader. An article's address SHALL be stored only as `on-demand-records` allows.

#### Scenario: Article the site does not allow to be read
- **WHEN** the article's site forbids automated reading in robots.txt, or refuses robots.txt itself
- **THEN** the article is not fetched and the reader is asked to paste its headline and opening paragraphs

#### Scenario: Nothing a reader sends is written down
- **WHEN** a lookup succeeds or fails
- **THEN** nothing of the text sent appears in any log or record

#### Scenario: Pasted text with no address
- **WHEN** a reader sends text and no address
- **THEN** the answer is made from the text and no lead is stored
