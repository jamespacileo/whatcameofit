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
The phrase for completed SHALL say that the registry lists the study as ended and that this is not a statement of what it found. The phrase for unknown SHALL say that the registry's record has not been confirmed and SHALL say nothing of the trial itself. A state phrase that carries verdict wording SHALL fail the site build, and so SHALL any other fixed wording of a trial page or of a listed trial's search row that carries a word for how a trial turned out or a word of advice: "option", "available", "eligible", a word for recruiting or joining, "should", "recommend". The site's two notices, which name advice and treatment options to disclaim them, are the one exception.

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
A lead sponsor who is a person SHALL NOT be shown, on the page of a trial a claim cites as on the plain page. A sponsor is a person when the registry classes it as an individual, which its API writes "INDIV", or when the record's responsible party is a sponsor-investigator, whatever the class: the rule `trial-facts` uses, held once for the Worker and once for the bulk load. When a record states why a trial was stopped, the page SHALL show that statement in the registry's words, attributed to the registry record, and SHALL NOT reword it.

#### Scenario: A trial sponsored by a person
- **WHEN** a record's lead sponsor is classed as an individual
- **THEN** the page shows no sponsor

#### Scenario: A sponsor-investigator classed as other
- **WHEN** a record's lead sponsor is classed "OTHER" and its responsible party is a sponsor-investigator
- **THEN** the page shows no sponsor and no name of the investigator

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

### Requirement: An export waits for the refresh of a changed cited trial
`thenwhat export` SHALL write no export while a published claim is due for its registry refresh because a trial it cites changed. It SHALL say how many claims are due and name the command that refreshes them. No other reason for a claim to be due SHALL hold an export.

#### Scenario: A cited trial is terminated
- **WHEN** a load stored that a cited trial was terminated and the citing claim has not been refreshed since
- **THEN** the export is refused, says one claim is due for its registry refresh, and names the command

#### Scenario: The claim has been refreshed
- **WHEN** every claim made due by a changed trial has been refreshed
- **THEN** the export is written, and the claim page and the trial page built from it agree

#### Scenario: An uncited trial changed
- **WHEN** a load changed only trials that no claim cites
- **THEN** the export is written

### Requirement: A trial listing built into the site
The site SHALL be built with a listing of a set of stored trials the operator names: for each, its identifier, title, acronym, phases, state, the day the registry last changed its record, its conditions, the names of its interventions, and the address of a published claim that cites it when one does; and, once for the file, the set's name and the latest day its records were read. The listing SHALL hold registry facts only, as codes and the registry's own text, SHALL hold no trial outside the named set, and SHALL be fetched only when a reader searches. A search for a listed trial's identifier, or for words of its title, its acronym, an intervention's name or a condition, SHALL be answered with that trial, after any claim that matches: a trial no claim cites leads to its trial page and carries the line that no news report is linked yet; a trial a published claim cites leads to that claim. Listed trials SHALL be ordered by a fixed rule over the words they hold, and no score SHALL be shown.

#### Scenario: A search for an identifier no claim cites
- **WHEN** a reader searches for the identifier of a listed trial that no claim cites
- **THEN** the search answers with that trial's page

#### Scenario: A search for an acronym
- **WHEN** a reader searches for the acronym of a listed trial
- **THEN** that trial is the first listed trial in the answer, after any claim that matches

#### Scenario: Words no claim holds
- **WHEN** a reader searches for the name of an intervention that no tracked claim holds and two listed trials test
- **THEN** the search says nothing tracked matches and shows the two listed trials under it

#### Scenario: A listed trial a claim cites
- **WHEN** a search finds a listed trial that a published claim cites
- **THEN** the trial's row leads to that claim and does not read that no news report is linked

#### Scenario: A trial outside the named set
- **WHEN** the listing is built for trials under way in phase 2 or 3 and a stored trial is completed in phase 1
- **THEN** the listing does not hold it

#### Scenario: A page that needs no search
- **WHEN** a reader opens a claim page and never searches
- **THEN** the listing is not fetched

### Requirement: The listing is written by its own command and staged with the export
The pipeline SHALL write the listing by a command of its own, `thenwhat trials-listing`, for a named set, sending no request and changing nothing in the database. The listing SHALL have a schema file checked into the site, a test SHALL fail when the schema file and the pipeline's model differ, and the site build SHALL fail on a listing that does not match the schema. The listing SHALL be staged for publication by the command that stages the export, beside it, and staging SHALL refuse a listing that does not match the schema, that holds no trial, that is larger than 8 MiB, or that names a claim the staged export does not publish. A site built with no listing beside its export SHALL build, open no page for an uncited trial, and leave search as it was.

Settled by the build on 2026-11-17: the set listed is `active-since-2025` (phase 2 or 3, under way or not yet started, record changed by the registry on or after 1 January 2025), which held 23,328 trials on the working database that day; its listing is one file of 7,009,433 bytes (6.68 MiB; 1.93 MB with gzip, 1.18 MB with Brotli), so it is not split.

#### Scenario: An unknown set
- **WHEN** the command is asked for a set that is not named
- **THEN** it writes nothing and lists the sets

#### Scenario: A listing written against another export
- **WHEN** the listing names a claim as citing a trial and the staged export does not publish that claim
- **THEN** staging is refused, the staged listing is unchanged, and the message says to write both again

#### Scenario: A listing too large to be one file
- **WHEN** a listing is larger than 8 MiB
- **THEN** staging is refused and says to list a smaller set or split it

#### Scenario: No listing
- **WHEN** the site is built from an export with no listing beside it
- **THEN** the build passes, a listed identifier no claim cites answers not found, and a search fetches an empty listing

### Requirement: Before the store, an uncited trial's page is the plain page, read from the registry on request
Until trial pages are answered from the store, the page of a listed trial that no published claim cites SHALL be answered by reading the trial's own record from the registry on request, as `trial-records` says, and SHALL be the plain page: the facts this capability names and nothing else. It SHALL NOT show the record's summary, an intervention's description, a planned or posted outcome, a location, a contact or who may take part. It SHALL name each intervention with the registry's word for its kind. A state the registry gives that the mapping of `trial-facts` does not hold SHALL be worded by one fixed phrase that says the page has no words for it, and SHALL NOT be guessed. A record that says results are posted and gives no date for it SHALL be worded by one fixed phrase that says results are posted. Whether a trial is cited SHALL be read from the published export, so that a trial's page and the claim pages built from that export never disagree about it.

#### Scenario: A listed trial no claim cites
- **WHEN** a reader opens the page of a listed trial that no published claim cites and the registry answers
- **THEN** the page shows the trial's state in its fixed phrase, its phase, conditions, interventions, enrolment, sponsor, dates and whether results are posted, the line that no news report is linked yet, and no summary, outcome, location or contact

#### Scenario: A state the mapping lacks
- **WHEN** the registry gives a trial a state that is none of the mapped ones
- **THEN** the page reads that it has no words for the state the registry gives and that the registry's record shows it

#### Scenario: A trial cited since the listing was written
- **WHEN** the listing says no claim cites a trial and the published export the site was built from holds a claim that does
- **THEN** the trial's page lists that claim and does not read that no news report is linked

### Requirement: Uncited trial pages are kept out of search engines until the operator says otherwise
The page of a trial that no published claim cites SHALL be marked not to be indexed and SHALL NOT be in the sitemap, until a setting the operator controls says otherwise. The operator decided on 2026-11-17 that these pages are not indexed until the wording has been read on real pages; no such setting is built yet, and every trial page is marked not to be indexed.

#### Scenario: The sitemap
- **WHEN** the sitemap is built and 25,898 uncited trials are listed
- **THEN** the sitemap holds none of their pages
