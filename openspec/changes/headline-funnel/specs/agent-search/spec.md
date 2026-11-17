# Spec Delta

## Purpose

Says how a model with a search tool looks for reports of a trial: the service that hands a trial to an agent and takes back addresses, what it hands out, what it accepts and refuses, what it stores, and what it never exposes.

## ADDED Requirements

### Requirement: The service hands out one due trial at a time
The service SHALL hand an agent one trial that is due and hold it for that agent until the agent reports or the hold runs out. A trial SHALL be due when it is in the set the operator named, has a fit term or a candidate term, is cited by no published claim, and has no ledger entry for this step at its present version. No two agents SHALL hold one trial at once. A hold that runs out SHALL make the trial due again.

#### Scenario: Two agents ask at once
- **WHEN** two agents ask for a trial at the same moment
- **THEN** each is handed a different trial

#### Scenario: An agent that never reports
- **WHEN** an agent is handed a trial and does not report within the hold's time
- **THEN** the trial is due again and a later report under that hold is refused

#### Scenario: Nothing is due
- **WHEN** an agent asks and no trial of the set is due
- **THEN** the service says nothing is due and hands out nothing

### Requirement: What an agent is handed
An agent SHALL be handed what the trial's stored registry record states: its registry number, title, acronym, conditions, intervention names and other names, lead sponsor when the sponsor is not a person, phases, state and dates. It SHALL NOT be handed a claim, a source article, a stored lead, a match or a score.

#### Scenario: A trial a pending claim names
- **WHEN** a due trial's treatment is named by a claim that is not yet published
- **THEN** the agent is handed the registry record's fields and nothing of the claim

### Requirement: An agent reports addresses or that it found nothing
An agent SHALL report, for the trial it holds, between none and the configured number of addresses. An address SHALL be required for each; a headline, an outlet's name, a date and a kind MAY be given as hints. A report of none SHALL be recorded as nothing found, and the trial SHALL NOT be handed out again at that step version.

#### Scenario: Nothing found
- **WHEN** an agent reports no address for a trial
- **THEN** the ledger entry's outcome is nothing found and the trial is not due again at that version

#### Scenario: Three addresses
- **WHEN** an agent reports three addresses for a trial
- **THEN** the ledger entry's outcome is done and records how many searches the agent said it ran

### Requirement: What the service refuses
The service SHALL refuse, by rule and with the reason for each: an address that is not a web address; an address on a registry, a paper index or an encyclopedia; a headline longer than the configured length; and any field it does not name. A refused address SHALL NOT be stored, and the others in the report SHALL be stored. The service SHALL accept no field that could carry an article's text.

#### Scenario: A registry page among the addresses
- **WHEN** a report gives two news addresses and one address on a trial registry
- **THEN** the two are stored, the third is refused with its reason, and the agent is told which

#### Scenario: A snippet beside an address
- **WHEN** a report carries a field holding words of the article beside an address
- **THEN** the report is refused and says the field is not accepted

### Requirement: A reported address becomes a link lead with its reason
A reported address SHALL be stored as a link lead, once per address as the site compares addresses, with the reason that a search for that trial returned it, the name of the model that searched as the settings give it, and the hints as given. An address that is already a link lead SHALL gain the reason and no second record. An address that is already a source article SHALL be counted as tracked and stored as nothing.

#### Scenario: An address a headline file already gave
- **WHEN** a reported address is already a link lead made from a headline file
- **THEN** that lead records the search as a further reason

### Requirement: Hints are not trusted
A lead's outlet kind SHALL be set by rule from its domain, never from a hint. A hinted headline SHALL be used for triage and ordering only, and a hinted date for ordering only: the read takes the headline and the date from the page. A hint that an address is about the trial's own study SHALL be kept with the lead and SHALL decide nothing.

#### Scenario: A hint that the address is about this trial
- **WHEN** an agent marks an address as a report of the trial's own study
- **THEN** the mark is stored with the lead, and the trial is handed to preparation as a candidate like any other

### Requirement: An agent searches and opens no page
An agent SHALL be started with a search tool that answers from a search index and opens no page, in a sandbox that cannot write, with no other tool than the service's own. No news page SHALL be fetched on this route other than by the page reader when a lead is read.

#### Scenario: An address that does not exist
- **WHEN** an agent reports an address that leads nowhere
- **THEN** nothing is checked at report time, and the page reader's failure when the lead is read is recorded as any failed address is

### Requirement: The service exposes nothing but the two actions
The service SHALL offer only the handing out of a trial and the taking of a report. It SHALL NOT create or change a claim, a source article, a match, an evidence event or a status, SHALL NOT answer a query of the store, and SHALL NOT return an article's text.

#### Scenario: A report that names a claim
- **WHEN** a report carries a field asking that an address be added to a claim
- **THEN** the report is refused and no claim is changed

### Requirement: The service is reachable from its own machine only
The service SHALL listen on the loopback address of the machine that writes the pipeline's database and SHALL NOT be served to the home network or the internet.

#### Scenario: A request from another machine
- **WHEN** a request reaches the machine's network address from another machine
- **THEN** nothing answers it

### Requirement: The route stops at its allowance
Trials handed out SHALL be counted against a daily allowance for this route in the source allowances the operator sets. When it is used up, the service SHALL hand out nothing and say so, and trials SHALL stay due.

#### Scenario: The day's allowance is used up
- **WHEN** an agent asks and the day's allowance has been handed out
- **THEN** the service says the allowance is used up and hands out nothing

### Requirement: The search tool is checked before it is used
The service SHALL hand out nothing until `docs/sources.md` holds a dated entry for the search tool and the plan it runs on: what its terms say of automated use, its limits as read and as observed, and what a result carries. The model SHALL be named in the settings and never in code.

#### Scenario: No entry yet
- **WHEN** the service is started and `docs/sources.md` has no dated entry for the search tool
- **THEN** it refuses to hand out a trial and names the missing entry

### Requirement: The route creates leads and nothing else
A lead this route stores SHALL go through every step any link lead goes through, by the same rules, and SHALL be read only when triage passed it or held it. The trial that led to it SHALL be handed to preparation as a candidate, scored for the claim's indication, and SHALL NOT be approved for having led to it.

#### Scenario: A reported address that triage rejects
- **WHEN** triage rejects the hinted headline of a reported address
- **THEN** the address is not read

#### Scenario: A run finishes
- **WHEN** agents have reported for 200 trials and nothing has yet been read
- **THEN** the store holds new link leads and ledger entries, and no claim, source article, match or evidence event it did not hold before
