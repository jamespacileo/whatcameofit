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

### Requirement: The store is kept in two tiers
The store SHALL be kept as a hot tier in D1, holding every table something on Cloudflare reads, and a bulk tier kept as one SQLite file of the same schema in R2, holding the rest. No row of the hot tier SHALL reference a row of the bulk tier; a hot record that names a bulk one SHALL name it by its natural key as text. A payload SHALL be kept in each tier whose rows point at it. A load of either tier SHALL be verified by one checksum a table, computed by the same single statement on the store file and on the loaded store, without reading the rows back.

#### Scenario: A build in two tiers
- **WHEN** the whole tracker is built from Postgres
- **THEN** a hot file and a bulk file are written, each with the schema whole and only its own tier's rows, and the hot file names no row it does not hold

#### Scenario: A load checked
- **WHEN** the hot file is loaded into D1 and each table's checksum statement is run there
- **THEN** each table's checksum from D1 equals the one from the file, and a table loaded short is named

#### Scenario: The day's changes
- **WHEN** the day's changes are pushed to the store
- **THEN** records of hot kinds and their payloads go through the ingest service to D1, and records of bulk kinds are merged into the bulk file by its one writer and kept as the day's delta beside the last bulk build

#### Scenario: The bulk tier restored
- **WHEN** the bulk file is downloaded and its deltas are replayed in order
- **THEN** each table's checksum equals that of the file the daily job merged in place

#### Scenario: The daily bulk merge runs twice
- **WHEN** the job runs again with the same day's delta path
- **THEN** that delta still contains every change since the day's starting point, including changes written before a restart

#### Scenario: A restore stops between batches
- **WHEN** a restore commits the first batch of a delta and stops
- **THEN** replaying the delta applies all remaining batches once

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

#### Scenario: An article discrepancy and another change on one claim
- **WHEN** the store kept the first of two source articles at a shared address key and the same claim also has an unexpected status or a changed title on a retained article
- **THEN** the comparison identifies the remaining change and exits with an error even with `--allow-named`

#### Scenario: A difference the comparison can explain
- **WHEN** a claim differs because the database holds two of its source articles at one address key, or only in the order of its intervention's other names
- **THEN** the claim is listed with that cause, the comparison still exits with an error, and with `--allow-named` it exits successfully only when every difference has a named cause

#### Scenario: Comparing against a store file built elsewhere
- **WHEN** the comparison is given a store file and its folder of payload objects (`--store`, `--payloads`)
- **THEN** the store's export is read from that file, the database's export is of every claim, and no store file is made

#### Scenario: Comparing against the store itself
- **WHEN** the comparison is given the name of the D1 database (`--d1`)
- **THEN** the rows an export reads are fetched with read-only queries into a store file, a payload object the local folder lacks is fetched from the bucket named, every payload is checked against its checksum, and the comparison is of that file

#### Scenario: D1 changes while its pages are being copied
- **WHEN** a transaction commits on D1 between the first and last page of the copy
- **THEN** the export reports that the copy must be retried and preserves the previous local snapshot

#### Scenario: A store that holds only the hot tier
- **WHEN** the store file or database holds only the tables an export reads (no registry trial, lead, share, ledger entry, usage or measure)
- **THEN** the export is the same as from a store that holds every table, a trial's facts on a claim's page coming from the raw payload of the claim's own evidence event, and a comparison against the database reads no other table

#### Scenario: A store missing what an export reads
- **WHEN** the store lacks a table or a column the export reads
- **THEN** the export is refused before anything is read, naming each missing table and column

### Requirement: A deployment can rehearse taking its export from the store
Until the cut-over, CI SHALL be able to take an export from the store, hold it to the schema the site reads and to the checks a published snapshot must pass, and report how its claims compare with the committed snapshot. The rehearsal SHALL be off unless a repository setting turns it on, SHALL only read the store, and SHALL change nothing the site is built or deployed from: the committed snapshot remains the source.

#### Scenario: A rehearsal
- **WHEN** the setting is on and a run on `main` starts
- **THEN** a separate job writes the store's export to its own workspace, fails when the export breaks the schema, holds no claim or fails a deployment check, and the deploy job neither waits for it nor reads what it wrote

#### Scenario: The setting is off
- **WHEN** the setting is absent or not `true`
- **THEN** the job does not run and no request reaches the store
