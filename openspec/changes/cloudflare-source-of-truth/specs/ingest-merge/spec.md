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
The ingest service SHALL answer only a request that carries a token it knows, SHALL know a token only by its checksum, and SHALL never log or return one. Each token SHALL be of one kind, and a request outside that kind's scope SHALL be refused with nothing stored: a device's token registers runs for its own device and states no action; the daily job's states no action and records no decision by a person or an assistant; a lookup's stages only a link lead, its share, a payload, a registry trial, a reading, usage and a count of an unlisted domain; the consumer's records decisions by rule only; the export's states a publication by rule and nothing else; the operator's may state every action. A token SHALL reach only runs it could have registered.

#### Scenario: A backfill tries to clear an audit
- **WHEN** a device's token stages an action that clears an audit, archives, publishes, merges or renames
- **THEN** the chunk is refused, nothing is staged, and the claim is as it was

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

### Requirement: The door holds a run to stated bounds
The ingest service SHALL refuse, before storing anything, a body that does not state its length or its content type, a chunk, a run or a payload larger than the bound set for it, and a record of a kind the store does not have. Each bound SHALL be below the platform's documented limit for what it protects, and the documentation page SHALL be named beside it.

#### Scenario: A run over the set size
- **WHEN** a writer registers a run stating more records than a run may hold
- **THEN** the registration is refused and says to split the run, parents first

#### Scenario: A chunk over its bound
- **WHEN** a chunk is larger in bytes or in records than a chunk may be
- **THEN** it is refused whole and nothing of it is staged

### Requirement: No field carries an article's text
The ingest service SHALL refuse a record that has a field no statement of the merge reads, and a record in which a string is longer than the store allows for it: 200 characters for a reported statement, as the schema states, and otherwise a bound far below an article's length. Only a field that holds a source's own structured record, on the one kind of record it belongs to, is bounded by the record's size instead. A refusal SHALL name the record's place and the field, and SHALL NOT repeat any value that was sent.

#### Scenario: A record with an extra field
- **WHEN** a source article is staged with a field holding the article's text
- **THEN** the chunk is refused, naming the field, and the answer holds none of the text

#### Scenario: A title as long as an article
- **WHEN** a record's title holds several thousand characters
- **THEN** the chunk is refused and nothing is staged

### Requirement: A report without applying leaves no run
When a writer asks for a run's report without applying, the service SHALL return the report with what it cannot see (what only a constraint of the store refuses; and a run that names one claim by two slugs for one record or whose actions depend on one another beyond a clear before a publication), and SHALL then drop the run and what it staged.

#### Scenario: After a dry run
- **WHEN** a report without applying has been returned
- **THEN** the store holds no trace of the run, and the same records can be registered again
