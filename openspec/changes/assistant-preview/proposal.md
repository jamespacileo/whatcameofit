# Proposal

## Why

On 2026-11-11 the operator left for an hour or two and asked the assistant to keep going and make decisions until the proof of concept was complete. The proof of concept needs claims with statuses on the local site, and statuses come only from reviewed matches and events. The project's rule is that a model's decision is never recorded as a person's, and nothing unreviewed reaches the public site. There was no honest way to do both.

## What Changes

- A fourth decider, **assistant**, for review decisions an AI assistant makes while working through the queue. `review approve`, `review reject` and `review stage` take `--as-assistant`. Such a decision is never recorded as the operator's and never becomes a human label.
- The export leaves out every claim on which an assistant's decision still stands (on the claim, one of its matches or one of its events). `export --preview`, or `EXPORT_PREVIEW=1`, includes them and marks the export as a preview.
- Every exported claim says whether a person checked it. Seed-loaded claims say no, as they always should have.
- A preview build shows a band on every page, asks search engines not to index it, and each unchecked claim page and extension popup says it has not been checked by a person.
- The operator makes a decision their own by repeating it without the flag. When no assistant decision is left on a claim, it is published like any other.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `review`: a decision records which of four deciders made it; the assistant's decisions label nothing.
- `site-publishing`: the publication gate excludes assistant-decided claims; previews are marked.

## Impact

- **Database:** migration 0002 widens the decider check on three tables. The first migration is no longer regenerated: the database now holds real claims.
- **Export:** two new fields, `preview` and `checked_by_person`. Schema, seed export and test fixture regenerated.
- **Site and extension:** a band, a note and a `noindex` tag, all absent from a normal build.
- **Risk:** a preview export copied to a public host. Mitigation: the band and note are built into every page of it, and the default export never contains assistant-decided claims.
