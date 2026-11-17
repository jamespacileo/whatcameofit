# Spec Delta

## Purpose

Says how the tracker looks for papers and news about a trial from the trial's own end: what a trial's fingerprint is, which trials are looked for, which sources are asked in what order, how a hit is tied to a trial, and that every article found goes through the path every lead goes through.

## ADDED Requirements

### Requirement: A trial's fingerprint
A trial's fingerprint SHALL be built by fixed rules from its stored registry record and SHALL hold: its registry number; its other identifiers as the record gives them; its acronym; the development codes among its intervention names and other names; its telling names; and its lead sponsor's name when the sponsor is not a person. No model SHALL be asked. A fingerprint SHALL be built again when a load changes a field it is read from.

#### Scenario: A phase 3 trial with an acronym and a code
- **WHEN** a stored trial's record gives the acronym "VOLGA" and an intervention's other name "MEDI4736"
- **THEN** its fingerprint holds its registry number, the acronym and the code

#### Scenario: A record changes
- **WHEN** a load adds an other name to a trial's intervention
- **THEN** the trial's fingerprint is built again and holds the new name if it is a code or a telling name

### Requirement: Which terms may be searched for
A fingerprint term SHALL be marked as fit to search for only when it is the registry number, a development code, a telling name, or an acronym that is fit.

#### Scenario: A code and a study's ordinary name
- **WHEN** a trial's fingerprint holds the code "TARA-002" and the acronym "HOPE"
- **THEN** the code is fit to search for and the acronym is not

### Requirement: When an acronym is fit
An acronym SHALL be fit only when all of these hold: it is not an ordinary word or a place or person's name, by the project's word list; it is not a word of any stored trial's conditions; the titles of no more than the configured number of other stored trials hold it; and it either carries a digit or a hyphen beside at least three letters, or is at least five letters long.

#### Scenario: An acronym that is a river
- **WHEN** a trial's acronym is "VOLGA"
- **THEN** the acronym is not fit to search for

### Requirement: A term that is not fit is never sent alone
A term that is not fit SHALL stay in the fingerprint, SHALL be used only to confirm a hit that a fit term found, and SHALL never be sent to a source by itself.

#### Scenario: A river and a code
- **WHEN** a trial's fingerprint holds the acronym "VOLGA", which is not fit, and the code "MEDI4736", which is
- **THEN** the code is sent, the acronym is not, and a headline that holds both is tied on the code

#### Scenario: An acronym that is a disease's abbreviation
- **WHEN** a trial's record gives "NSCLC" as its acronym and thousands of stored trials hold it in their titles
- **THEN** the acronym is not fit to search for

#### Scenario: An acronym with a number
- **WHEN** a trial's acronym is "KEYNOTE-789"
- **THEN** the acronym is fit to search for

#### Scenario: A trial with no fit term but its number
- **WHEN** a trial's fingerprint has no fit acronym, code or telling name
- **THEN** it is searched for by its registry number only, in the sources that search by number

### Requirement: Which trials are looked for
Coverage SHALL be looked for only for trials in a named set. Since 2026-11-17 the target is `active-or-ended-this-year` (see "The trial target set rolls with the year"); the two dated sets it replaced as the target SHALL remain: `active-since-2025`, trials not started or under way in phase 2 or 3 whose registry record changed on or after 1 January 2025; and `completed-with-results-since-2025`, trials the registry lists as completed, with an actual completion date on or after 1 January 2025, whose record holds posted results. A set's date SHALL be part of its name, so that a later date is a new set and no set changes its meaning. A route that yields news SHALL NOT be asked for a trial that a published claim cites. A route that yields papers SHALL be asked for every trial of the set, cited or not.

#### Scenario: A trial a claim already cites
- **WHEN** a trial in the named set is cited by a published claim
- **THEN** no news source is asked for it, and the paper index is still asked for the papers that carry its number

#### Scenario: A trial completed in 2024 whose results were posted in 2026
- **WHEN** a stored trial's actual completion date is in 2024 and its results were first posted in 2026
- **THEN** it is not in `completed-with-results-since-2025`

### Requirement: The trial target set rolls with the year
The set that coverage is looked for SHALL be `active-or-ended-this-year`: every stored trial the registry lists as not yet recruiting, recruiting, enrolling by invitation or active and not recruiting, in any phase and whenever its record was last updated; and every stored trial the registry lists as completed, terminated, withdrawn or suspended whose completion date is in the current calendar year. The year SHALL be given to the rule by the command that runs, which reads it from the clock; the rule itself SHALL read no clock. The two dated sets SHALL keep their names and their rules, and everything that names one SHALL go on working. Every trial of `active-since-2025` SHALL be in the target set.

#### Scenario: A trial under way in phase 1
- **WHEN** a stored trial is recruiting in phase 1 and its record was last updated in 2019
- **THEN** it is in `active-or-ended-this-year` and in neither dated set

#### Scenario: A trial that ended this year
- **WHEN** a stored trial is listed as terminated with a completion date of February of the current year
- **THEN** it is in `active-or-ended-this-year`

#### Scenario: A trial that ended last year
- **WHEN** a stored trial is listed as completed with a completion date of December of last year
- **THEN** it is not in `active-or-ended-this-year`

#### Scenario: The year turns
- **WHEN** the same stored trials are chosen in the following year
- **THEN** the trials that ended in the earlier year are no longer in the set, and nothing stored for them is removed

#### Scenario: A set named before the change
- **WHEN** a command or a setting names `active-since-2025`
- **THEN** it selects the trials it selected before the target set was added

#### Scenario: The rolling set without a year
- **WHEN** the rule of `active-or-ended-this-year` is asked for with no year
- **THEN** it is refused, and no clock is read in its place

### Requirement: The paper index is asked for the target set, ended and resulted trials first
The step that asks the paper index SHALL ask for every trial of `active-or-ended-this-year` whose number is the registry's the index names, and for the trials of the two dated sets, so that no trial once in scope leaves it. Trials that ended in the year and trials with results posted SHALL be asked first. The step's rules for the index SHALL be unchanged: its allowance, its off-peak hours for a large job, and stopping when the index fails.

#### Scenario: A trial under way in phase 1 is asked
- **WHEN** the step runs and a trial under way in phase 1 has not been asked for
- **THEN** it is asked for, after the trials that ended this year and the trials with results posted

### Requirement: A coverage report counts what is held for the set
A command SHALL count, for the trials of `active-or-ended-this-year` under way, those completed in the year and those terminated, withdrawn or suspended in the year, and for all of them: the trials, those with results posted, those whose registry record lists a paper as a result or links one, those with a paper found by number, those a published claim cites, and those whose record the registry has not updated since before last year. It SHALL print counts only, name no trial, send no request and change nothing. A count SHALL say what is held and nothing of how any trial turned out. It SHALL also print how many trials in scope the paper index has not been asked about, about how many requests that needs, how long at the configured interval, how many off-peak nights under the allowance, and what a key would allow and which settings the operator would set to use one; it SHALL NOT set or need a key.

#### Scenario: A coverage report for the set
- **WHEN** the operator asks for the coverage of the set
- **THEN** each group and the whole set are printed with their six counts, and no source is asked

#### Scenario: An estimate before the paper index is asked
- **WHEN** 76,000 trials in scope have not been asked about, fifty go in one search and requests are half a second apart under an allowance of 5,000 a day
- **THEN** the report says about 3,040 requests, about 25 minutes and one off-peak night, and that a key would allow ten requests a second

### Requirement: A coverage set says which trials, and is refused when it cannot be chosen
A set SHALL say only which trials are looked for and nothing of how any trial turned out. Both sets SHALL be refused while stored trials carry no date of last change. A name the command does not know SHALL be refused with the list of sets.

#### Scenario: Before the wider load
- **WHEN** the operator names `active-since-2025` and no stored trial has a date of last change
- **THEN** the command refuses and says the wider load has not run

#### Scenario: A set the command does not know
- **WHEN** the operator asks for the set `successful`
- **THEN** no source is asked and the command lists the sets it has

### Requirement: Routes are asked in a fixed order, free and deterministic first
The routes SHALL be, in this order: the registry record's own references and links; papers that carry the trial's registry number; stored leads matched on the fingerprint; the batched news search; press-release wires; full-text news search; and a mentions index.

#### Scenario: Two routes are due for one trial
- **WHEN** a trial is due for the papers that carry its number and for the batched news search
- **THEN** the paper index is asked before the news index

### Requirement: A route runs only when it is on and still needed
A route SHALL be run only when it is turned on, and the wires, the full-text news search and the mentions index SHALL be off until the operator turns each on. A route SHALL NOT be asked for a trial that an earlier route has already given an article a published claim was drafted from.

#### Scenario: A route that is off
- **WHEN** coverage is looked for and the mentions index is not turned on
- **THEN** no request is sent to it and the plan says the route is off

#### Scenario: An earlier route sufficed
- **WHEN** a stored lead matched a trial, was read, and its claim is published
- **THEN** the batched news search does not include that trial

### Requirement: A source is checked before it is asked
No client SHALL be written for a source, and no request sent to it by the pipeline, until its current terms, authentication, limits and price have been read and noted in `docs/sources.md` with the date and the pages read. A source whose terms forbid automated requests, or do not say, SHALL NOT be asked, and the note SHALL say so.

#### Scenario: A wire whose terms forbid automated access
- **WHEN** a press-release wire's terms or its robots file forbid automated requests to its search
- **THEN** no client is written for its search and `docs/sources.md` records why

#### Scenario: A wire that publishes feeds
- **WHEN** a wire forbids automated use of its search and publishes subject feeds that its terms let a program read
- **THEN** only the feeds are read, and a release is tied to a trial only when its headline holds a fit term of the trial

#### Scenario: A route turned on without a note
- **WHEN** a route is turned on and `docs/sources.md` has no dated entry for its source
- **THEN** the command refuses and names the missing entry

### Requirement: Papers the registry record names
The papers a trial's registry record lists as reporting its results, or that the registry links from the paper index by the trial's number, SHALL be attached to the trial by rule, as results papers, with the kind the registry gives. Papers the record lists as background SHALL NOT be attached. No search, score or model SHALL be used.

#### Scenario: A record with one results paper and four background papers
- **WHEN** a trial's record lists one paper of the kind result and four of the kind background
- **THEN** one results paper is attached to the trial and the four are not

### Requirement: A listed paper is named by one rule and kept in one store
The papers of a stored trial SHALL be read from its record by the same rule that reads them for a trial a claim cites: one for each PubMed number, the sponsor's listing kept when a paper is listed both ways, a reference with no PubMed number left out. A paper so named SHALL become a paper record only through the one store of paper records, which asks the paper index once for a paper and keeps "not held" as an answer. It SHALL NOT be a match, SHALL carry no score, SHALL NOT be an evidence event, and SHALL NOT be a related paper of any claim. Reading what a record lists SHALL send no request.

#### Scenario: A trial a claim comes to cite
- **WHEN** a stored trial's listed paper already has a paper record and a claim later cites the trial
- **THEN** the claim's refresh finds that record and stores no second one

#### Scenario: A paper listed both ways
- **WHEN** a record lists one paper as a result and the registry also links it from the paper index
- **THEN** it is named once, as listed by the sponsor

#### Scenario: Counting a set
- **WHEN** the operator counts what the records of a set list
- **THEN** the trials with a paper of each kind, the papers and the links by domain are printed, and no request is sent

### Requirement: Links the registry record gives
A link a trial's registry record gives to an article on a listed outlet SHALL become a link lead with the reason that the registry record gives the address. Any other link SHALL be counted by domain and not kept.

#### Scenario: A record that links a press release
- **WHEN** a trial's record links an address on a listed press-release wire
- **THEN** a link lead is stored for the address with the reason that the registry record gives it

#### Scenario: A record that links the sponsor's site
- **WHEN** a trial's record links an address on a domain that is on no list
- **THEN** no lead is stored and the domain is counted

### Requirement: Papers that carry the trial's number
A paper whose index record carries a trial's registry number in the field its publisher supplied for it SHALL be attached to the trial as a paper that gives the number, with no score. The index SHALL be asked for the numbers of many trials in one request, within its noted limits, and a paper SHALL be given to a trial only when the paper's own record, read back from the index, carries that trial's number exactly. A paper that only mentions the number in its text SHALL NOT be attached. A paper whose record carries more than three registry numbers SHALL NOT be attached. A paper so attached SHALL NOT be called a results paper unless the registry record names it as one.

#### Scenario: A paper that gives one trial's number
- **WHEN** the paper index returns a paper whose record carries a trial's number and no other
- **THEN** the paper is attached to that trial as a paper that gives its number

#### Scenario: Fifty trials in one request
- **WHEN** fifty trials are due and the index answers one request with three papers
- **THEN** each paper is given only to the trials whose numbers its own record carries, and the trials no paper names are recorded as asked with nothing found

#### Scenario: A paper that cites the trial in passing
- **WHEN** a full-text index finds a trial's number in the text of a paper whose own record does not carry it
- **THEN** the paper is not attached to the trial

#### Scenario: A review that lists twelve trials
- **WHEN** a paper's record carries twelve registry numbers
- **THEN** it is attached to none of them

### Requirement: The paper index is asked as its usage policy asks
Every request to the paper index SHALL name the software and give its developer's contact address, and no request SHALL be sent while either is not configured. A key SHALL be sent when one is configured and SHALL NOT be required. Requests SHALL stay under the index's limit for a client with no key. Requests sent during the hours the index asks large jobs to avoid SHALL be counted together for every process and across runs, and once they reach the number the index calls a large job, a run SHALL stop with its trials still due. When the index cannot be reached, fails, answers in a form not understood, or holds more papers than one answer returns, the run SHALL end with its trials still due and no attempt counted, and the trials of the request SHALL NOT be asked one by one. The plan SHALL show the requests the due trials need as asked in batches.

#### Scenario: No contact address
- **WHEN** the step is run and no contact address is configured
- **THEN** no request is sent and the command names the missing setting

#### Scenario: A large job at midday
- **WHEN** a hundred requests have been sent on a weekday morning in the index's time zone, by any number of workers and runs
- **THEN** the next run stops before sending one, says when to run again, and the trials not yet asked stay due

#### Scenario: The index is down
- **WHEN** a search for fifty trials is answered with a server error
- **THEN** the run ends after that one request, the fifty trials stay due and no attempt is counted against any

### Requirement: What is stored of a paper found by number
A paper found for a trial SHALL be stored with the trial, the source's name, the paper's index number, the paper's record as reduced, and the time it was fetched. The reduced record SHALL hold no abstract and no author. Storing it SHALL create no claim, match, evidence event or paper record.

#### Scenario: A paper is found
- **WHEN** the index returns a paper whose record carries a due trial's number
- **THEN** one row ties the trial to the paper with the source, the reduced record and the fetch time, and nothing else is created

### Requirement: Nothing found is an answer
"No paper found" for a trial SHALL be stored as an answer in the work ledger and SHALL NOT be asked again before the configured age. Until an age is configured, a trial that has been asked SHALL NOT be asked again at the step's version.

#### Scenario: Asked last week, nothing found
- **WHEN** the paper index returned nothing for a trial last week and the configured age is thirty days
- **THEN** it is not asked again for that trial

### Requirement: A paper on a trial page is a paper, not a report of how the trial turned out
A trial page SHALL list the papers attached to the trial under two fixed headings the site holds, one for papers the registry record names and one for papers that give the trial's number, each with its paper facts and a link. The page SHALL state nothing of what a paper found. A paper SHALL NOT remove the line that no news report is linked.

#### Scenario: A trial with a results paper and no claim
- **WHEN** a trial has one results paper attached and no published claim cites it
- **THEN** its page lists the paper with its title, journal and year, and still reads that no news report is linked yet

### Requirement: Stored leads matched on the fingerprint
The offline linking SHALL link a stored lead to a trial on the trial's registry number, a development code, its acronym and the other names of its interventions, each as its own reason with its own strength, by the rules of `trial-report-links`. A registry number in a lead's title or address SHALL link the lead exactly to that one trial with no condition word needed. An acronym SHALL link only when it carries a number, and its link SHALL be named, not strong: on the working database on 2026-11-17 no stored lead held such an acronym, and of twelve links judged on acronyms without a number, one named a treatment and none a study.

#### Scenario: An acronym in a headline
- **WHEN** a stored lead's title holds "KEYNOTE-789" and a word of the conditions of the stored trial with that acronym
- **THEN** the lead has a named link to that trial with the acronym recorded

#### Scenario: A registry number in an address
- **WHEN** a stored lead's address holds a trial's registry number
- **THEN** the lead is linked exactly to that trial alone

### Requirement: One news search carries many trials
The news search for a set SHALL send the fit terms of many trials in one request, as alternatives, restricted to the configured collections and outlets and to the configured period, within the source's allowance. The number of trials a request carries SHALL be a setting. A trial whose terms were sent and answered SHALL be recorded as searched at that step version whether or not anything was found.

#### Scenario: Ten trials in one request
- **WHEN** ten trials of a set are due for the news search and the setting is ten
- **THEN** one request is sent and all ten are recorded as searched

### Requirement: An answer that is cut short or does not come leaves nothing half done
A request whose answer is cut short SHALL be asked again in parts until no part is cut short. A request that is not answered in time SHALL leave its trials due and SHALL NOT be recorded as searched. A search SHALL stop when the source's allowance is used up and say how many trials are left.

#### Scenario: A request that times out
- **WHEN** the source does not answer a request of ten trials within its time
- **THEN** none of the ten is recorded as searched and all ten stay due

#### Scenario: An answer cut short
- **WHEN** the source returns as many stories as a request may return and says there are more
- **THEN** the request's trials are asked again in two halves, and none is recorded as searched from the first answer

#### Scenario: The allowance runs out
- **WHEN** the source's allowance is used up part way through a set
- **THEN** the search stops, says how many trials are left, and those trials stay due

### Requirement: A hit is tied to a trial only on what the headline or address holds
A story a batched search returns SHALL be tied to a trial only when its headline or its address holds, as whole words, a fit term of that trial. A story that holds no fit term of any trial in the request SHALL be counted and dropped, and its address SHALL NOT be stored. A story that holds fit terms of several trials SHALL be tied to each. A tied story SHALL be stored as an article lead of the trial with its address, outlet, title and date, the term it was tied on, and no text.

#### Scenario: A headline that names the code
- **WHEN** a returned story's headline holds "TARA-002" and one trial in the request has that code
- **THEN** an article lead is stored for that trial with the term "TARA-002"

#### Scenario: A story that matched in its text only
- **WHEN** a returned story's headline and address hold no fit term of any trial in the request
- **THEN** nothing is stored for it and it is counted as not tied

#### Scenario: A headline that names two trials
- **WHEN** a returned story's headline holds the acronyms of two trials in the request
- **THEN** an article lead is stored for each

### Requirement: Wires and full-text search are asked by number or fit term, and the page confirms
A press-release wire or a full-text news search SHALL be asked only for a trial's registry number or a fit term, within the source's noted limits and only in the way its noted terms allow. A hit SHALL be stored as a lead with the reason that the source returned it for that term, and SHALL be tied to the trial as a candidate only. The tie SHALL be confirmed only when the article's page, read through the page reader, gives the trial's registry number or a fit term of it.

#### Scenario: A release found by number
- **WHEN** a wire's search returns a release for a trial's registry number
- **THEN** a link lead is stored with that reason, and the trial is a candidate of whatever claim the read drafts

#### Scenario: The page does not give the number
- **WHEN** such a lead is read and its page gives neither the number nor a fit term of the trial
- **THEN** the trial is not handed to preparation as a candidate, and the lead's detail says the tie was not confirmed

### Requirement: Every article found goes through the existing path unchanged
An article that any route finds SHALL be a link lead or an article lead and nothing more until it is read. It SHALL go through every step a backfill's link lead goes through, by the same rules: screening, triage, the page reader, the same-claim decision, drafting or joining, `thenwhat prepare --pending`, and the audit hold until `thenwhat audit clear` releases it. It SHALL be read only when triage passed it or held it.

#### Scenario: An article found by the batched search
- **WHEN** the batched search ties a story to a trial and triage passes its headline
- **THEN** the article is read through the page reader, a claim is drafted or joined, prepared and held awaiting audit, and no export publishes it before it is cleared

#### Scenario: An article triage rejects
- **WHEN** a route finds an article and triage rejects its headline
- **THEN** it is not read, whatever route found it

#### Scenario: An article about a claim that exists
- **WHEN** a found article reports a treatment and condition a published claim already holds
- **THEN** the same-claim decision adds it to that claim as any lead's article is added

### Requirement: A route creates leads and nothing else
No route SHALL create a claim, a source article, a match or an evidence event by itself, and no route SHALL fetch a news page other than through the page reader. The trial that led to an article SHALL be handed to preparation as a candidate, scored for the claim's indication, and SHALL NOT be approved for having led to the article.

#### Scenario: The trial that led to the article
- **WHEN** a found article's read drafts a claim
- **THEN** the trial is a candidate of the claim, scored for the claim's indication, and is not approved for having led to the article

#### Scenario: A route finishes
- **WHEN** a route has run for a set and nothing has yet been read
- **THEN** the store holds new leads, and no claim, source article, match or evidence event that it did not hold before

### Requirement: A search is planned, run by the operator, and never by a load
Before a route is run for a set, the command SHALL print how many trials are due, how many requests each route would send against what is left of each source's allowance, and what reading the expected hits would cost against the route's share of the ceiling. It SHALL send nothing a source's allowance does not cover. No load and no daily run SHALL start a route.

#### Scenario: A plan for the active set
- **WHEN** the operator asks for the plan of `active-since-2025`
- **THEN** the counts of trials, requests by source, allowance left and expected cost are printed and no request is sent

#### Scenario: A daily run
- **WHEN** the daily run loads changed trials that are in a named set
- **THEN** those trials are due for the routes and no route is started
