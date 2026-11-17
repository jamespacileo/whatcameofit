# Spec Delta

## Purpose

Names the one store, on the Cloudflare platform, that holds the tracker's records and is the only authority for them, what it holds and never holds, and how it is recovered.

## ADDED Requirements

### Requirement: One authoritative store
The tracker's claims, source articles, reported statements, evidence events, registry trials, papers, entities, matches, decisions, model usage and link leads SHALL be held in one store on the Cloudflare platform. No other database SHALL be treated as authoritative. A copy on a device SHALL be disposable: losing it SHALL lose no record the store holds.

#### Scenario: A device is wiped
- **WHEN** a device that has pushed its work is erased
- **THEN** every record it pushed is still in the store and nothing the site shows changes

#### Scenario: Two devices disagree
- **WHEN** a device's working copy holds a claim in a state the store does not
- **THEN** the store's state is the one the export and the site use

### Requirement: Raw payloads are kept with their fetch time
For every evidence event and every registry trial the store SHALL keep the raw payload as the source gave it and the time it was fetched. Where the payload is kept apart from the record, the record SHALL hold where it is and a checksum of it, and a payload that does not match its checksum SHALL be reported and never used.

#### Scenario: A large registry record
- **WHEN** a registry record with posted results is larger than a row may be
- **THEN** its payload is kept whole, the record points to it, and the fetch time is stored

#### Scenario: A payload that was altered
- **WHEN** a payload read back does not match the checksum on its record
- **THEN** the read fails with an error that names the record, and no status is derived from it

### Requirement: What the store never holds
The store SHALL NOT hold the text of an article or of a post, the author of a post, a reader's network address, anything that identifies a reader, text a reader pasted, or an image a reader's browser sent. It SHALL NOT hold a subscriber's email address under this change.

#### Scenario: After a lookup of pasted text
- **WHEN** a reader pastes an article's text and asks for a search
- **THEN** no row and no stored object holds any of that text

### Requirement: The store is kept in the European Union
The store and the raw payloads SHALL be created under the European Union jurisdiction, so that they are stored and run only there. A store found not to be under it SHALL NOT be used.

#### Scenario: Creating the store
- **WHEN** the store is created for preview or production
- **THEN** its jurisdiction is the European Union, and the deployment check reads that back before any record is written

### Requirement: The store is not served
The store SHALL be reachable only by the site's own service through its binding, and by a device holding a token for the ingest address. It SHALL NOT be reachable as a database from the public internet, and no token SHALL permit an arbitrary statement.

#### Scenario: A device's token
- **WHEN** a device's token is used to ask for anything but registering a run, handing over records, taking a work slice or reading the reference export
- **THEN** the request is refused

#### Scenario: A token is revoked
- **WHEN** the operator revokes one device's token
- **THEN** that device's requests are refused and every other device's still work

### Requirement: The store can be put back
The store SHALL be restorable to its state at a chosen time within the last 30 days. Before a migration or a run larger than a set number of records, a restore point SHALL be recorded with the run.

#### Scenario: A bad run
- **WHEN** a run is found to have merged wrong records
- **THEN** the operator can restore the store to the point recorded before that run

### Requirement: Every record says where it came from
Every record the store holds SHALL carry the run that first added it and the run that last changed it. A run SHALL record the kind of writer, the device or the class of reader request, the code's commit and the time.

#### Scenario: Asking what a device added
- **WHEN** the operator asks which records one device's runs added on one day
- **THEN** the store answers from the records alone

### Requirement: An export from the store is the same as before
`thenwhat export` taken from the store SHALL produce the export the site reads, in the schema the site reads, with the publication gate applied as `site-publishing` requires.

#### Scenario: After migration
- **WHEN** the same records are exported from the database used before this change and from the store
- **THEN** the two exports hold the same claims, events and codes

### Requirement: The export is assembled once, from either store
The export SHALL be assembled by one piece of code that asks a reader for records and never a table. There SHALL be two readers, one over the database used before this change and one over a SQLite file that has the store's schema, and both SHALL hand over the same kinds of record in the same stated order. What a claim's entry contains, how its lists are ordered and how its status is derived SHALL be the assembly's alone, so that two exports can differ only in what a reader hands over. `thenwhat export --store <file>` SHALL read such a file, with `--payloads <folder>` naming where the payloads kept as objects are found.

#### Scenario: Same records, same export
- **WHEN** the same records are held by the database and by a store file, and each is exported at the same time
- **THEN** the two exports are the same byte for byte once both are put in the comparison's canonical order, in every part: claims, `archived`, `moved`, outlets, verticals, statements, promises, papers, trials and organisations

#### Scenario: Archived, merged and held claims
- **WHEN** the records include an archived claim that was published, a claim merged into another, a claim whose slug a rename replaced, and a claim awaiting audit
- **THEN** both exports list the archived claim under `archived`, the merged claim's slug and the former slug under `moved`, and neither publishes the claim awaiting audit

#### Scenario: Every status
- **WHEN** the records hold one claim for each rule that derives a status
- **THEN** both exports give each claim the same status and name the same events as its cause

#### Scenario: A payload kept as an object
- **WHEN** an event's raw payload is larger than the store keeps in its own table
- **THEN** the reader takes it from the folder or bucket by the key the store names, and the export is the same as from the database

#### Scenario: A payload that is missing or altered
- **WHEN** a payload the export needs is absent, or its bytes do not have the checksum it is named by
- **THEN** the export is refused, naming the payload, and no file is written

#### Scenario: Reading only
- **WHEN** an export is taken from a store file
- **THEN** the file is opened for reading only and is unchanged afterwards: a status the assembly derives and a first published time are not written back, and the claims published for the first time are reported for the writer that states publications

#### Scenario: Not a store file
- **WHEN** the file named does not have the tables the export reads
- **THEN** the export is refused, naming the tables that are missing

### Requirement: The two exports are compared
`thenwhat export-compare` (`make export-compare`) SHALL take the export from the database and the export from a store file, compare them in canonical form, and exit with an error when they differ. Canonical form SHALL leave out only what cannot be equal by construction: the time the export was made, the numbers each store gives its own rows (an event's id, and every reference to it, is renumbered by the event's content), and the order of entries that tie on everything but a row's number. Until the store gives a snapshot, the command SHALL make the store file itself, from the database's records in the natural-key form the pipeline writes and through the store's own merge.

#### Scenario: The nightly comparison
- **WHEN** the daily job runs the comparison and the two exports are the same
- **THEN** the command exits successfully and reports how many claims were compared, which the cut-over rule counts towards its seven nights

#### Scenario: A difference is named
- **WHEN** one claim's entry differs between the two exports
- **THEN** the command exits with an error and names the claim and the places in its entry that differ

#### Scenario: What the comparison looks past
- **WHEN** two exports differ only in the time they were made, in the ids of events, or in the order of entries that tie
- **THEN** they compare as the same

#### Scenario: Comparing changes neither store
- **WHEN** the comparison is run against the working database
- **THEN** the database is read in a read-only transaction that is rolled back, nothing is written to it, and the store file it makes is removed unless it is asked to be kept
