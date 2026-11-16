# Proposal

## Why

A claim page lists registry records that are not trials on the page yet, and possible records that do not count toward the status. Each entry led with its registry identifier, which means nothing to most readers, carried a second link under it, and ran the record's title, conditions, interventions, phase and state together as one sentence. "Match to this claim" ended every row and the reason for the score was one press away. The one-line summary also said "recruiting", which the trial entries never say: a recruiting trial is "under way", so it is never presented as open to join.

On 2026-11-16 the operator compared five mocked variants (`.impeccable/mocks/registry-records/index.html`) and chose "A + C": title-led rows, grouped by how each record was read.

## What Changes

- The pipeline keeps each trial match's record field by field beside its summary: title, conditions, interventions, phases and state, the last two as the codes the trial facts use. A new command, `thenwhat entity record-facts`, reads them for matches stored before.
- The export carries them as `record` on each match; null until read.
- The claim page lists the records in groups by reading, closest to the claim first, each reading said once as the group's heading. Each row leads with the study's title (the link to the trial page here), then one line with the identifier (the link to the registry), phase, state and the match note, then "For" and "Tests".
- A record not yet read into fields shows its identifier and says so; the one-line summary is no longer shown.

Out of scope: trial entries, papers, the live lookup's answers, and the reported statements, which keep their own layouts.

## Capabilities

### Modified Capabilities

- `entity-resolution`: a trial match keeps its record field by field.
- `site-publishing`: registry records are grouped by reading and laid out field by field.

## Impact

- `pipeline/`: migration 0027, `facts_of` and `fill_record_facts` in `resolve/service.py`, the `entity record-facts` command, `ExportedMatchRecord` in the export.
- `site/`: `RegistryRecords.astro`, `lib/registry-records.ts`, reading headings in `lib/confidence.ts`, styles, `export.schema.json`, `seed-export.json`.
- The writer runs the migration and `thenwhat entity record-facts` before the next export; until then every record shows the not-read state.
