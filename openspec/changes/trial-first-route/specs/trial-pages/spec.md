# Spec Delta

## Purpose

Says what a registered trial is on the site whether or not a claim cites it: one page of what its registry record states, worded without verdict or advice, and never a claim.

## ADDED Requirements

### Requirement: One page for each trial
A trial SHALL have one address on the site, made from its registry identifier, whether or not any claim cites it. A trial that gains or loses a citing claim SHALL keep its address. The page SHALL be about one registry record and SHALL NOT be a claim: it SHALL carry no status, no status gloss, no overlay, no record strip, no topic and no match score, and it SHALL NOT be counted in any total or list of claims.

#### Scenario: A trial no claim cites
- **WHEN** a reader opens the page of a stored trial that no published claim cites
- **THEN** the page shows the trial's registry facts and no status of any kind

#### Scenario: A trial gains a claim
- **WHEN** a claim citing a trial is published after the trial's page was first opened
- **THEN** the trial's page has the same address and now lists that claim

#### Scenario: The site's count of claims
- **WHEN** 25,000 trials have pages and 708 claims are published
- **THEN** every total of claims the site shows is 708

### Requirement: What a trial page states
A trial page SHALL state, from the trial's stored registry record: the identifier followed by the registry's name; the title; the trial's state; its phases; its conditions and interventions in the registry's words; its enrolment, marked planned or actual; its lead sponsor's name; and a link to the record at the registry.

#### Scenario: A trial under way in phase 3
- **WHEN** a reader opens the page of a stored phase 3 trial
- **THEN** the page shows its identifier with the registry's name, its title, state, phase, conditions, interventions, enrolment and sponsor, and a link to the registry's record

### Requirement: Dates and the posting of results
A trial page SHALL state the trial's start, primary completion and completion dates, whether the record holds posted results and the date they were first posted, the date the record was read and the date the registry last changed it.

#### Scenario: A record with results posted
- **WHEN** a trial's record says results were first posted on 3 March 2025
- **THEN** the page states that results were first posted on the registry record on that date, and nothing about what they show

### Requirement: Facts are stated as the record gives them
Every fact on a trial page SHALL be read from the stored registry record by fixed rules, and no model SHALL be asked. A fact the record does not state SHALL be shown as not stated and SHALL NOT be inferred. A date the registry marks estimated SHALL be marked estimated, and a date given as a month SHALL NOT be given a day.

#### Scenario: A record with no completion date
- **WHEN** a trial's record gives no completion date
- **THEN** the page shows the completion date as not stated

#### Scenario: A completion date that is an estimate
- **WHEN** a record gives a primary completion date of June 2027 marked estimated
- **THEN** the page shows "Jun 2027 (estimated)" and no day

### Requirement: A trial's state is worded by the site and says nothing of recruitment
A trial page SHALL show the trial's state as one of not started, under way, completed, suspended, terminated, withdrawn or unknown, by the mapping `trial-facts` defines, each with one fixed phrase the site holds. The page SHALL NOT show the registry's own status word where that word says whether a trial is recruiting.

#### Scenario: A recruiting trial
- **WHEN** a trial's record has the overall status recruiting
- **THEN** the page reads that the registry lists the study as started and not yet finished, and the word "recruiting" is not on the page

### Requirement: A state phrase claims no more than the registry does
The phrase for completed SHALL say that the registry lists the study as ended and that this is not a statement of what it found. The phrase for unknown SHALL say that the registry's record has not been confirmed and SHALL say nothing of the trial itself. A state phrase that carries verdict wording SHALL fail the site build.

#### Scenario: A completed trial
- **WHEN** a trial's record has the overall status completed
- **THEN** the page reads that the registry lists the study as completed and that this says the study ended, not what it found

#### Scenario: A state phrase with verdict wording
- **WHEN** the site is built and the phrase for unknown contains the word "abandoned"
- **THEN** the build fails and quotes the phrase

### Requirement: A phase the registry does not give
When a record's phase is the registry's "not applicable" or is empty, the page SHALL say that no phase is given and SHALL NOT show a phase.

#### Scenario: A device study
- **WHEN** a trial's record gives the phase as not applicable
- **THEN** the page reads that the registry gives no phase for this study

### Requirement: Sponsor and reason for stopping
A lead sponsor that the registry classes as an individual SHALL NOT be shown. When a record states why a trial was stopped, the page SHALL show that statement in the registry's words, attributed to the registry record, and SHALL NOT reword it.

#### Scenario: A trial sponsored by a person
- **WHEN** a record's lead sponsor is classed as an individual
- **THEN** the page shows no sponsor

#### Scenario: A terminated trial with a stated reason
- **WHEN** a terminated trial's record states "Sponsor decision"
- **THEN** the page shows "Sponsor decision" as the reason the registry record gives

### Requirement: No word for how a trial turned out
A trial page SHALL NOT state or imply how a trial turned out. It SHALL NOT use "successful", "failed", "positive", "negative", "promising" or any like word of a trial or its results. It SHALL NOT state that results are late, overdue or missing, or how long a record has gone without change. It SHALL NOT carry a sponsor's description of a result.

#### Scenario: A completed trial with results posted four years after completion
- **WHEN** a trial completed in 2019 and its results were first posted in 2023
- **THEN** the page states both dates and no word about the time between them

#### Scenario: A page built with an outcome word
- **WHEN** the site is built and a trial page's fixed wording contains the word "successful"
- **THEN** the build fails and quotes the wording

### Requirement: Nothing about taking part
A trial page SHALL NOT state whether the trial is open to participants, where it runs, whom to contact or who may take part. It SHALL carry the site's notices, including that a registered trial is not a treatment option.

#### Scenario: A trial with forty sites
- **WHEN** a trial's registry record lists forty locations and a contact
- **THEN** the page shows no location and no contact, and carries the notice that a registered trial is not a treatment option

### Requirement: No lead and no regulator's decision on an uncited trial
A trial page SHALL NOT show a link lead, an article lead, a count of either, or anything from a lead's title. It SHALL NOT show a regulator's decision except as the status of a claim that cites the trial.

#### Scenario: A trial that a stored lead is linked to
- **WHEN** a link lead is strongly linked to a trial and no claim cites the trial
- **THEN** the trial's page shows no lead and reads that no news report is linked yet

#### Scenario: A drug later approved
- **WHEN** a regulator has approved a drug and no claim cites the trial of it that a reader opens
- **THEN** the trial's page shows no approval

### Requirement: The page says when no report is linked
When no published claim cites a trial, its page SHALL say, in one fixed line the site holds, that no news report is linked to the record yet. When at least one published claim cites it, the page SHALL list those claims, each with the status its claim page shows, apart from the claims it is only a possible match for, and SHALL NOT show the line. A claim that is pending, rejected, archived or awaiting audit SHALL NOT be listed and SHALL NOT remove the line.

#### Scenario: An uncited trial
- **WHEN** no published claim cites a trial
- **THEN** its page reads "No news report is linked to this record yet."

#### Scenario: A trial cited only by a claim awaiting audit
- **WHEN** the only claim that cites a trial is awaiting audit
- **THEN** the trial's page still reads that no news report is linked yet and names no claim

### Requirement: Primary outcomes are shown only from a full record
A trial page SHALL state planned or posted primary outcomes only when it has the trial's full registry record, stored or read from the registry for the page, and then by the rules `trial-facts` defines. Without one, the page SHALL state only whether results are posted and when.

#### Scenario: Results posted, no full record
- **WHEN** a page is answered from a trial's list record, which says results are posted, and no full record is stored for the trial
- **THEN** the page states that results were posted and the date, and names no outcome

### Requirement: One record for a trial on every page
For one registry identifier, a trial page and every claim page that lists the trial SHALL state the trial's state, phases, dates and posting of results from the same stored record, the one fetched most recently, and SHALL show the date it was read. A trial page SHALL show a citing claim's status only as the export gives it and SHALL derive no status.

#### Scenario: Two stored copies of one trial
- **WHEN** a claim's event stores a trial's record fetched in March and the corpus holds the same trial fetched in October
- **THEN** the claim page and the trial page both state the trial's facts from the October record

#### Scenario: A cited trial is terminated
- **WHEN** the daily load stores that a cited trial was terminated
- **THEN** no export is written until the citing claim's registry evidence has been refreshed, and the pages built from that export agree

### Requirement: A trial listing built into the site
The site SHALL be built with a listing of a set of stored trials the operator names: for each, its identifier, title, state, phases and start date, and the date the records were read. The listing SHALL hold registry facts only, SHALL hold no trial outside the named set, and SHALL be fetched only when a reader searches. A search for a listed trial's identifier or for words of its title SHALL be answered with that trial's page, after any claim that matches.

#### Scenario: A search for an identifier no claim cites
- **WHEN** a reader searches for the identifier of a listed trial that no claim cites
- **THEN** the search answers with that trial's page

#### Scenario: A trial outside the named set
- **WHEN** the listing is built for trials under way in phase 2 or 3 and a stored trial is completed in phase 1
- **THEN** the listing does not hold it

#### Scenario: A page that needs no search
- **WHEN** a reader opens a claim page and never searches
- **THEN** the listing is not fetched

### Requirement: Uncited trial pages are kept out of search engines until the operator says otherwise
The page of a trial that no published claim cites SHALL be marked not to be indexed and SHALL NOT be in the sitemap, until a setting the operator controls says otherwise.

#### Scenario: The sitemap
- **WHEN** the sitemap is built and 25,898 uncited trials are listed
- **THEN** the sitemap holds none of their pages
