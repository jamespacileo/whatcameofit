# Spec Delta

## Purpose

Defines the one way records enter the truth store, whoever sends them: a reader's lookup, a backfill pushed from a device, a scheduled refresh or the migration. It makes every write safe to repeat and subject to the same rules.

## ADDED Requirements

### Requirement: Every write is a run
A writer SHALL register a run before handing over records, stating the kind of writer, the device's name or the class of reader request, the code's commit and the version of each step that produced the records. Records SHALL be accepted only for a registered run, and SHALL enter the store only by that run's merge.

#### Scenario: Records with no run
- **WHEN** records are handed over naming a run that was not registered
- **THEN** they are refused and nothing is stored

#### Scenario: A lookup writes
- **WHEN** a reader's lookup stores what it found
- **THEN** it does so as a run of the kind reader lookup, through the same merge a device's push uses

### Requirement: Records are matched by what they are
The merge SHALL match a claim by its slug, a source article by claim and address, an evidence event by claim and its dedupe key, a registry trial by registry and trial number, a paper by its identifier, an entity by its kind and name, a link lead by its address key, and a share by lead, platform, community and time. A record SHALL refer to another by these keys and never by a row identifier.

#### Scenario: A claim the store does not have
- **WHEN** a run holds a claim whose slug the store has no claim for
- **THEN** the claim and its records are added

#### Scenario: A new article for a claim the store has
- **WHEN** a run holds a source article for a claim the store already holds
- **THEN** the article is added to that claim and the claim's other records are left as they are

#### Scenario: Two writers found the same article
- **WHEN** a device's run and a reader's lookup both hold the same article for the same claim
- **THEN** the store holds one source article and one link lead, with each share once

### Requirement: Every writer writes a record in one form
A writer SHALL give each record its natural key and its fields in the one form the store compares, so that two writers, or one writer twice, produce the same store from the same rows. A source article's and an article lead's address key SHALL be the site's address comparison (`site/src/lib/article-key.mjs`, `pipeline/src/thenwhat/backfill/address.py`). A time SHALL be ISO-8601 in UTC to the microsecond with its offset, always the same width, because the merge orders times as text. A payload's checksum SHALL be the SHA-256 of its JSON text with keys sorted, no spaces and characters unescaped, in UTF-8, and its size the bytes of that text. An evidence event's content checksum SHALL be of its type, date, trial state, trial phases as a set, regulatory outcome and source identifier. A field with no value SHALL be left out of the record, never sent as a JSON null. A key of several parts SHALL join them with `|`, escaping a `|` or `\` inside a part with `\`, so two sets of parts never give one key. A decision whose decider was not recorded SHALL NOT be written as a person's. A link lead SHALL carry an address key of the current version, and one of an older version SHALL be refused until it is keyed again.

#### Scenario: Two devices write one article
- **WHEN** two devices hold the same article under addresses that differ only by tracking parameters
- **THEN** both records carry the same address key, and the store holds one source article

#### Scenario: A payload fetched as the same JSON
- **WHEN** two fetches give a payload with the same keys and values in another order
- **THEN** both records name the payload by the same checksum

#### Scenario: A registry lists phases in another order
- **WHEN** a later fetch lists an event's trial phases in another order and says nothing else new
- **THEN** the event's content checksum is the same, and the event is not kept apart as differing

### Requirement: A snapshot of the tracker can be pushed twice
Records gathered from a whole database, as the migration and a nightly comparison gather them, SHALL leave the store as it was when pushed a second time. A snapshot SHALL NOT carry, under a merged claim's slug, what that claim keeps for itself (its intervention, matches, terms, events, failure flags and measurements), its status time, its audit mark, its publication or its archive, because the store reads a merged claim's slug as the claim it was merged into; the merge itself archives the claim. A snapshot SHALL NOT carry a rename, which names the claim by a slug the store never held. Decisions, spend and measurements SHALL be pushed once, by the run that made them, since a merge keeps each run's and adds measurements to the day's totals.

#### Scenario: The same snapshot pushed again
- **WHEN** a snapshot is merged and then the same records are merged as another run
- **THEN** no claim, article, entity, match, event, trial or lead is added or changed, and only the second run's decisions and spend are kept beside the first's

#### Scenario: A merged claim in the snapshot
- **WHEN** a snapshot holds a claim merged into another
- **THEN** it carries the claim and its merge, and the claim that stayed gains none of its intervention, matches, events, status, audit mark or publication

#### Scenario: A snapshot is taken back into a database
- **WHEN** a snapshot's records are placed into a Postgres database that already holds rows in a table they fill
- **THEN** nothing is written and the tables already holding rows are named, since placing has none of the merge's rules for a row already held

### Requirement: A merge is whole or not at all, and safe to repeat
A run's merge SHALL apply all of its records or none. Merging a run already merged SHALL add and change nothing and SHALL say when it was first merged.

#### Scenario: A failure part way
- **WHEN** a merge fails on a late record
- **THEN** the store is as it was before the merge began

#### Scenario: The same run twice
- **WHEN** a writer retries a merge that had succeeded
- **THEN** nothing is added and the first merge's time is reported

### Requirement: Refusals
The merge SHALL refuse a run, applying nothing and saying why, when any step version it states is older than the version the store currently accepts, when a record lacks its natural key, or when the records handed over do not match the count and checksum the writer stated.

#### Scenario: A run from older code
- **WHEN** a run's triage version is lower than the store's
- **THEN** the merge is refused and names the step and both versions

#### Scenario: Records lost on the way
- **WHEN** fewer records arrive than the writer stated
- **THEN** the merge is refused

### Requirement: What was decided in the store is kept
The merge SHALL NOT unarchive a claim, a match or an event the store holds archived. It SHALL NOT replace a decision recorded by a person with one recorded by a rule, a model, the seed or an assistant. Where a run and the store hold different decisions on one record, the decision of the higher decider SHALL stand: a person's, then an assistant's, then a rule's or the seed's; between two of the same rank, the later. It SHALL NOT change a published claim's published time.

#### Scenario: A claim the operator archived
- **WHEN** a run holds new records for a claim the store holds archived
- **THEN** the claim stays archived, its new source articles are stored, and the report lists it

#### Scenario: An assistant and a rule disagree
- **WHEN** a run holds an approval by rule of a match the store holds rejected by an assistant
- **THEN** the assistant's rejection stands, whichever of the two runs was merged first

#### Scenario: A match a person rejected
- **WHEN** a run holds an approval by rule of a trial match that a person rejected
- **THEN** the rejection stands

### Requirement: Evidence that differs is not overwritten
When the store holds an approved evidence event and a run holds an event with the same dedupe key and different content, the merge SHALL keep the stored event, SHALL keep the run's event apart with the reason and the run it came from, where the audit can see both, and SHALL mark the claim awaiting audit. The run's event SHALL NOT be used to derive a status until a person or a rule accepts it.

#### Scenario: A trial's record changed between two fetches
- **WHEN** a run's event for a trial differs from the approved one stored
- **THEN** the stored event is unchanged, the run's is kept apart with its reason, the claim is held, and the report counts one conflict

#### Scenario: The same difference arrives twice
- **WHEN** two runs hold the same differing event for a claim
- **THEN** it is kept apart once

### Requirement: The audit mark is carried and never cleared by a merge
A claim that a run marks awaiting audit SHALL be awaiting audit after the merge. A merge SHALL never clear the mark. A claim a run states as cleared SHALL arrive cleared only when the store held no such claim before.

#### Scenario: A batch pushed before its audit
- **WHEN** a run of claims awaiting audit is merged and an export is taken
- **THEN** the export leaves those claims out and counts them as held

### Requirement: Writers do not block one another
Merges that touch different claims SHALL proceed without waiting for one another. Merges that touch the same claim SHALL be applied one after the other, and the result SHALL be the same in either order.

#### Scenario: A device pushes while a reader looks up
- **WHEN** a device's merge of 5,000 records is running and a reader's lookup stores a lead for an unrelated article
- **THEN** both complete, and the lookup is not refused or delayed past its own time limit

#### Scenario: Same claim, either order
- **WHEN** two runs that each add an article to one claim are merged in one order and, on a copy, in the other
- **THEN** the two stores hold the same records

### Requirement: A merge reports and reconciles
A merge SHALL report, for each kind of record, how many were added, how many matched a record already held, and how many were conflicts, and SHALL apply nothing when those do not sum to the records handed over. A writer MAY ask for the report without applying.

#### Scenario: A dry run
- **WHEN** a writer asks for a run's report without applying
- **THEN** the report is returned and the store is unchanged

### Requirement: Spend is recorded by who spent it
Model usage a run hands over SHALL be stored with the run's writer. The plan for a month SHALL show usage by device and by reader lookups, and their sum against the month's ceiling.

#### Scenario: Two devices and readers in one month
- **WHEN** two devices' runs and a day of lookups have been merged
- **THEN** the plan shows each device's spend, the lookups' spend, and the total

### Requirement: A writer is held to its scope
The ingest service SHALL answer only a request that carries a token it knows, SHALL know a token only by its checksum, and SHALL never log or return one. Each token SHALL be of one kind, and a request outside that kind's scope SHALL be refused with nothing stored: a device's token registers runs for its own device, states no action, records no decision by a person or an assistant, and hands over an approved claim only with its audit hold unless the store already holds that claim approved and released; the daily job's states no action and records no decision by a person or an assistant; a lookup's stages only a link lead, its share, a payload, a registry trial, a reading, usage and a count of an unlisted domain, and ties no lead to a claim; the consumer's records decisions by rule only; the export's states a publication by rule and nothing else; the operator's may state every action, and it alone records a decision by a person or an assistant. A token SHALL reach only runs it could have registered.

#### Scenario: A backfill tries to clear an audit
- **WHEN** a device's token stages an action that clears an audit, archives, publishes, merges or renames
- **THEN** the chunk is refused, nothing is staged, and the claim is as it was

#### Scenario: A device hands over a person's decision
- **WHEN** a device's token stages a claim, a match or a label marked as decided by a person or an assistant
- **THEN** the chunk is refused and nothing is staged

#### Scenario: A device approves a claim without its hold
- **WHEN** a device's token stages an approved claim with no audit hold, and the store does not already hold that claim approved and released
- **THEN** the chunk is refused and nothing is staged

#### Scenario: A lookup tries to archive
- **WHEN** a lookup's token stages an archive action, a claim, an evidence event or a match
- **THEN** the chunk is refused and nothing is staged

#### Scenario: Another device's run
- **WHEN** one device's token asks for, stages into, merges or drops a run another device registered
- **THEN** the service answers as if the run did not exist

#### Scenario: No token
- **WHEN** a request carries no token, a revoked one or one never issued
- **THEN** it is refused, whatever it asked for, and the answer does not say which

### Requirement: What is handed over is what was sent
A raw payload larger than a row may hold SHALL be handed over under its SHA-256 before the run that names it, and a body that does not match its checksum SHALL be refused and not stored. A payload kept in its record SHALL match the checksum and size the record states. Each chunk of records SHALL state the SHA-256 of its body, and a chunk that does not match SHALL not be staged. A run SHALL state a checksum of its chunks, the SHA-256 of their checksums sorted and joined by a line feed, and the service SHALL NOT merge a run whose chunks are not the ones it stated.

#### Scenario: A payload altered on the way
- **WHEN** a payload's body does not hash to the checksum it was put under
- **THEN** it is refused and no object is stored

#### Scenario: A chunk never arrived
- **WHEN** a run is asked to merge and one of its stated chunks was not staged
- **THEN** the merge is not tried and the answer says the checksum does not hold

#### Scenario: A chunk sent twice
- **WHEN** a writer sends the same chunk for the same run again
- **THEN** nothing more is staged and the run's checksum is unchanged

### Requirement: The store reads a record as the door read it
The ingest service SHALL stage the value it checked, written out again, and never the bytes that arrived. It SHALL refuse a body that is not UTF-8 and a record holding a string that the store's engine and the service could read differently. Every time in a record SHALL be in one form, UTC to the microsecond with its offset, or a day alone, and a time in another form SHALL be refused. Registering a run again SHALL write nothing, and SHALL be refused when it states a different writer, device, checksum, steps or counts.

#### Scenario: A key given twice
- **WHEN** a record gives `action` as an audit clear and then as a publication, and `decided_by` as a person and then as a rule
- **THEN** what is staged is a publication by rule, as the door checked it, and the claim stays held

#### Scenario: A long text behind a short one
- **WHEN** a record gives a title of several thousand characters and then a short one
- **THEN** only the short one reaches the store

#### Scenario: A time in another form
- **WHEN** a record's time ends in `Z` or is given to the second
- **THEN** the chunk is refused, naming the field

#### Scenario: A merged run registered again
- **WHEN** a run that was merged is registered again with more steps or counts
- **THEN** it is refused and the run's steps and counts are as they were

### Requirement: Bulk records wait in an inbox
When a reader's lookup's or the consumer's run that is merged hands over a record of a bulk kind, the ingest service SHALL keep that record as it was staged, with the payload records it names, until the daily job has read it and said it is folded into the bulk file. A run that is refused or undone SHALL leave none. Only the daily job's token and the operator's SHALL read or clear the inbox. A fold SHALL be recorded only when the delta object that holds it is in the bucket and listed beside its build, how far it folded SHALL be read from that list and not from the caller, and the inbox SHALL be cleared no further than the furthest fold recorded. Clearing SHALL remove the records up to the one named and, for each run folded whole, the rows that run added to D1's copies of the bulk tables, all or none, except a lead whose processing is still due, which is held until it is not.

#### Scenario: A lookup's lead and share
- **WHEN** a reader's lookup is merged with a lead and its share
- **THEN** the inbox gives both records as they were staged, and after the daily job clears them D1 holds neither the records nor the lead and share rows

#### Scenario: Clearing before the delta is uploaded
- **WHEN** the daily job asks to clear the inbox past the furthest fold recorded, or records a fold whose delta object is not in the bucket
- **THEN** it is refused and nothing leaves D1

#### Scenario: A lead the consumer has not processed
- **WHEN** the inbox is cleared and a reader's lead of a folded run still has its processing due
- **THEN** its records leave the inbox, the lead stays in D1 with its share, and a later clearing removes it once the processing is done or has failed for good

#### Scenario: A run cut by a page
- **WHEN** the inbox is cleared up to a record in the middle of a run
- **THEN** that run's earlier records leave the inbox and its rows stay in D1 until the rest are cleared

#### Scenario: Another token asks
- **WHEN** a device's, a lookup's, the consumer's or the export's token reads or clears the inbox
- **THEN** it is refused

### Requirement: The door holds a run to stated bounds
The ingest service SHALL refuse, before storing anything, a body that does not state its length or its content type, a chunk, a run or a payload larger than the bound set for it, and a record of a kind the store does not have. Each bound SHALL be below the platform's documented limit for what it protects, and the documentation page SHALL be named beside it.

#### Scenario: A run over the set size
- **WHEN** a writer registers a run stating more records than a run may hold
- **THEN** the registration is refused and says to split the run, parents first

#### Scenario: A chunk over its bound
- **WHEN** a chunk is larger in bytes or in records than a chunk may be
- **THEN** it is refused whole and nothing of it is staged

### Requirement: No field carries an article's text
The ingest service SHALL refuse a record that has a field no statement reading that kind of record reads, and a record in which a string is longer than the store allows for it: 200 characters for a reported statement, as the schema states, and otherwise a bound far below an article's length. Only a field that holds a source's own structured record, on the one kind of record it belongs to, is bounded by the record's size instead; a field a source's record can make long, such as a trial's joined arm names, has its own stated bound. A refusal SHALL name the record's place and the field, and SHALL NOT repeat any value that was sent.

#### Scenario: A record with an extra field
- **WHEN** a source article is staged with a field holding the article's text
- **THEN** the chunk is refused, naming the field, and the answer holds none of the text

#### Scenario: A title as long as an article
- **WHEN** a record's title holds several thousand characters
- **THEN** the chunk is refused and nothing is staged

### Requirement: No stored registry record names a person
The ingest service SHALL refuse a ClinicalTrials.gov record that names a person, whether it arrives in a payload record, in a source record or as a payload object: its officials and contacts, a site's contacts, the investigator a responsible party is, a sponsor or collaborator who is a person, the results' point of contact, and any email or phone. The refusal SHALL say which kinds of field were found and SHALL NOT repeat a name or a means of contact. Nothing of a refused record SHALL be stored.

#### Scenario: A lookup hands over a record as the registry gave it
- **WHEN** a lookup's token stages or puts a trial's record that still holds its overall officials
- **THEN** it is refused, naming the kind of field, and no row or object is stored

#### Scenario: The same record with its people removed
- **WHEN** the record is handed over with those fields removed
- **THEN** it is taken

### Requirement: The progress of a load of trials is shown as counts
The ingest service SHALL show how far the load of trials has come from the slices the store holds, which only the merge writes, with the rows of each table and the last merged run of each kind of writer, to the operator's and the daily job's tokens only. The answer SHALL hold counts, a slice's group and times, and SHALL NOT hold a trial's identifier or anything of a record. The service SHALL have no route of its own that writes progress. The page that shows it SHALL hold no count until a token is typed into it, SHALL keep that token for the browser tab only and SHALL never put it in an address, and SHALL load nothing from another origin.

#### Scenario: A slice moves on
- **WHEN** a run that states a slice's later stage is merged
- **THEN** the progress shows that stage reached for the slice, and its other stages as they were

#### Scenario: The page without a token
- **WHEN** anyone asks for the progress page
- **THEN** the same empty page is answered, with no count in it

#### Scenario: A slice of trials is pushed
- **WHEN** a device's run hands over the trials of a slice
- **THEN** they are not kept in the inbox of the bulk tier and are not removed from D1 when the inbox is cleared

### Requirement: The service is deployed one way and answers no stranger
The ingest service SHALL be deployed only by its deploy command, which SHALL refuse unless the database's jurisdiction reads back as the European Union and no migration is left to apply, SHALL set the tokens' secret without printing or logging it, and SHALL then ask the deployed service and fail unless every route answers 401 without a known token. The deployed service SHALL bound how often one address without a token, and one token, may ask.

#### Scenario: A migration is not applied
- **WHEN** the deploy command finds a migration the database does not have
- **THEN** nothing is deployed

### Requirement: A report without applying leaves no run
When a writer asks for a run's report without applying, the service SHALL return the report with what it cannot see (what only a constraint of the store refuses; and a run that names one claim by two slugs for one record or whose actions depend on one another beyond a clear before a publication), and SHALL then drop the run and what it staged.

#### Scenario: After a dry run
- **WHEN** a report without applying has been returned
- **THEN** the store holds no trace of the run, and the same records can be registered again
