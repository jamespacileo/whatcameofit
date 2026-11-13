# Proposal

## Why

A claim with no approved trial shows "No trial record found" and nothing else, even when the registry and the literature hold its record. The claim `tourette-syndrome-wrist-nerve-stimulation` shows both gaps (checked 2026-11-13):

- The registry was searched for "Wrist-worn median nerve stimulation device" as written. That returned three unrelated trials (two nausea bands, one tremor device), all rejected by rule. A search for "median nerve stimulation" within Tourette syndrome returns three trials, one of them run by Nottingham University Hospitals NHS Trust (NCT05269953). The pipeline never made that search: only the live lookup asks the model for search phrases.
- OpenAlex returns the group's sham-controlled trial report and two further papers in its first five results for the same words. The pipeline looks for papers only when an article gives a DOI.

The same claim also holds two person entities who are not researchers: the reporter, and the first name of the fifteen-year-old the report features.

## What Changes

- Extraction gives up to three search phrases for an intervention that has no product name, and resolution searches the registry with them, within the claim's indication.
- Resolution searches the literature for papers about the claim's intervention and indication, and stores each as a candidate match with a score and the reasons for it.
- A registry number stated in an approved paper becomes a trial candidate.
- The paper most likely to be the one first reported on is suggested as the origin paper, which lets the existing follow-up and retraction checks run for claims whose article gave no DOI.
- Institutions and companies an article names are looked up in open organisation registries and stored as candidate matches.
- The claim page lists approved papers under their own heading, each with its score and reasons. They are not evidence events and do not change the status.
- Extraction records as people only those named as doing the research. Stored person entities that are anyone else are removed.

Not in this change: pages for institutions, companies or people; organisations derived from paper affiliations; any change to how status is derived; searching the web with a model.

## Capabilities

### New Capabilities

- `related-research`: finding, scoring, approving and showing papers about a claim that the article did not cite by DOI.

### Modified Capabilities

- `claim-extraction`: search phrases are part of a draft; only researchers are recorded as people.
- `entity-resolution`: the registry is also searched by search phrase; institutions and companies get candidate matches from organisation registries.
- `source-clients`: literature search by words; organisation lookup by name.
- `site-publishing`: the claim page shows related research.

## Impact

- New source clients: OpenAlex (free key, a daily allowance of 1 US dollar at the date checked, 0.001 per search) and ROR (no key). Each needs its entry in `docs/sources.md` before its client is written. New setting `OPENALEX_API_KEY`.
- Pipeline: `extract/schema.py`, `resolve/service.py`, `decide/steps.py`, `sources/`, `review/queue.py`, `export/build.py`, one new migration (search phrases on an entity; reasons on a match).
- Site: claim page, `site/export.schema.json`, `site/data/seed-export.json`.
- Model cost: one decision call per twenty papers. About 15,000 input tokens for a claim with twenty candidates, 0.0015 US dollars at the Decisions price recorded in `docs/sources.md`.
- Data: person entities for non-researchers are deleted from the database after the operator has seen the list.
