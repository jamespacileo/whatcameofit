# Spec Delta

## Purpose

Says what a reader's lookup, from the browser extension or the landing page, may add to the truth store, what it never adds, and what has to be true before anything it added is public.

## ADDED Requirements

### Requirement: A lookup of an untracked article leaves a link lead
When a reader asks for a search of an article the store does not track, and the article's outlet is on a list, the service SHALL store a link lead for the article with its address, outlet, title and date, and a share whose platform is reader. An article on an unlisted outlet SHALL be answered as before and SHALL leave no lead; it SHALL be counted by domain.

#### Scenario: A listed outlet
- **WHEN** a reader asks about an untracked article on a listed outlet
- **THEN** the reader gets the automatic answer as before, and the store holds one link lead for the address with one reader share

#### Scenario: The same article asked about twice
- **WHEN** two readers ask about the same article
- **THEN** the store holds one link lead for it

#### Scenario: An unlisted outlet
- **WHEN** a reader asks about an article on an outlet that is on no list
- **THEN** the reader gets the automatic answer and no lead is stored

### Requirement: Registry records a lookup found are kept
The registry trials a lookup retrieved SHALL be stored in the registry corpus with their raw payload and fetch time, whether or not any claim refers to them.

#### Scenario: A trial the corpus did not hold
- **WHEN** a lookup retrieves a trial the store has no record of
- **THEN** the trial is stored with its payload and fetch time, and is not an evidence event of any claim

### Requirement: A lookup's reading is not a claim
What a lookup read the article to report SHALL be stored with the lead as a reading awaiting the rules, with its scores and reasons. A lookup SHALL NOT create or approve a claim, an evidence event or a match, and SHALL NOT set or change a status.

#### Scenario: After a lookup that found one matching trial
- **WHEN** a lookup reads an article as reporting a treatment for a condition and finds one trial of it
- **THEN** the numbers of claims, approved events and approved matches in the store are unchanged

### Requirement: Nothing a lookup added is public by a new route
A lead from a reader SHALL go through the steps a lead from a file goes through. A claim drafted from it SHALL be approved only by the rules that approve any claim and SHALL be held awaiting audit until released. Until then no export SHALL contain it.

#### Scenario: A reader asks about a new treatment report
- **WHEN** a reader's lookup leaves a lead, the lead is later read, and a claim is drafted and approved by rule
- **THEN** the claim is awaiting audit and the next export leaves it out

### Requirement: Nothing about the reader is kept
A record a lookup leaves SHALL hold nothing that identifies the reader or the request: no network address, no identifier, no user agent, no text or image the reader's browser sent, and no time finer than the day.

#### Scenario: Inspecting a reader share
- **WHEN** the operator reads a share whose platform is reader
- **THEN** it holds the lead, the platform and a date, and nothing else

### Requirement: The reader is told
Where a lookup leaves records, the words beside the offer SHALL say that the article's address and the trial records found are kept so the tracker can follow the story, and that nothing about the reader is kept.

#### Scenario: Before a reader asks
- **WHEN** a search is offered for an untracked article
- **THEN** the offer says what is sent, what is kept and what is not

### Requirement: A reader cannot fill the store
The limits on searches by one reader and by all readers SHALL apply before any record is written. Leaving records SHALL be turned on by a setting that is off by default.

#### Scenario: Over the limit
- **WHEN** a reader's request is refused by the rate limit
- **THEN** nothing is written

#### Scenario: The setting is off
- **WHEN** records from lookups are not turned on
- **THEN** a lookup answers as it did before this change and writes nothing

### Requirement: A tracked address is answered from the store
When a reader asks about an address the store tracks, the service SHALL answer with the tracked claim's published state from the store, whether or not the site has been rebuilt since it was published. It SHALL never answer with a claim that is awaiting audit, pending or archived.

#### Scenario: Published an hour ago
- **WHEN** a claim was released from audit after the last build and a reader's extension asks about its article
- **THEN** the reader gets the tracked answer

#### Scenario: Held for audit
- **WHEN** the article belongs to a claim awaiting audit
- **THEN** the reader gets the same answer as for an untracked article
