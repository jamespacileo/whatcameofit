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
