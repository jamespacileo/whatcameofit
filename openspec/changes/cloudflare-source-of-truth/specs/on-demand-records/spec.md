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

### Requirement: A claim a reader's lead starts is published by rule
A lead from a reader SHALL go through the steps a lead from a file goes through. A claim drafted from it SHALL be approved only by the rules that approve any claim. It SHALL NOT be marked awaiting audit. Once approved it SHALL be in the next export, marked as not checked by a person. A claim that is not approved SHALL NOT be in any export.

#### Scenario: A reader asks about a new treatment report
- **WHEN** a reader's lookup leaves a lead, the lead is read, and a claim is drafted and approved by rule
- **THEN** the next export contains the claim, marked as not checked by a person

#### Scenario: The rules do not approve it
- **WHEN** the claim drafted from a reader's lead has no trial that tests its intervention for its indication and no confirmed evidence stage
- **THEN** it stays pending and no export contains it

#### Scenario: A backfill's claim beside a reader's
- **WHEN** one claim is drafted from a backfill's read batch and another from a reader's lead, and both are approved by rule
- **THEN** the first is awaiting audit and left out of the next export, and the second is in it

### Requirement: A reader's lead is processed within minutes and never while the reader waits
The answer a reader gets SHALL NOT wait on reading the article into a claim. A reader's lead SHALL be queued when it is stored and processed without anyone starting a run. A lead whose processing fails SHALL be tried again a set number of times and then left with its error, and SHALL NOT be lost.

#### Scenario: A slow outlet
- **WHEN** the article's outlet takes a minute to answer the page reader
- **THEN** the reader already has the automatic answer, and the lead is processed when the page arrives

#### Scenario: Processing stops at the spend ceiling
- **WHEN** the store-side share of the month's ceiling is used up
- **THEN** readers' leads stay queued or due, readers still get their answers, and processing resumes next month or when the share is raised

### Requirement: Claims published from readers' leads can be listed
The operator SHALL be able to list the claims published from readers' leads on a given day, with each claim's article and the rules that approved it.

#### Scenario: Looking over yesterday's
- **WHEN** the operator asks for the claims published from readers' leads yesterday
- **THEN** each is listed with its article, its matches and their scores

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
