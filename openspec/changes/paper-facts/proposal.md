# Proposal

## Why

A claim page shows a paper as a title and a link, or as a bare DOI. It does not say what kind of publication it is, where it appeared, or whether the study was in people or in animals, which is the first thing a reader asks of a breakthrough. And the papers most worth listing are ones the pipeline already holds a pointer to and never reads: of the 221 trials with a stored registry record on 14 November 2026, 58 name a paper as reporting their results (49 listed by the sponsor, 75 linked by the registry, 124 in all, 523 references with a PubMed number). `referencesModule` is read nowhere in the code.

Paper search itself belongs to `related-research` and is not repeated here. This change is about the papers a page already has a rule-based reason to list, and about saying of every listed paper what its index record states.

## What Changes

- Papers that a trial's registry record lists as reporting its results are attached to that trial by rule, with no search and no model, and shown with it.
- Every paper a claim page lists (the origin paper, follow-up papers, a trial's results papers, and related research once `related-research` exports it) is exported once, as a paper, with the roles it plays for the claim.
- Each paper carries what its Europe PMC record states: title, journal, year, the kinds of publication, whether it is open access, whether it is marked retracted, and whether its index terms say the study was in people, in animals or both.
- The record a paper's facts are read from is stored with its fetch time, without its abstract and without its authors.
- The claim page gains a "Papers on record" section in place of "Matched papers", with each paper once, and a line that counts the records of studies in people and of studies in animals.
- The open data file carries the papers.

Not in this change: finding papers by search, scoring them or choosing the origin paper (`related-research`); authors, affiliations or citation counts; abstracts in any form; papers a trial lists as background reading; any change to status, including for a retracted paper that is not the origin paper.

## Capabilities

### New Capabilities

- `paper-facts`: what a paper's index record says of the paper itself (kind of publication, journal, year, studied in people or animals, retracted), which papers a trial's registry record names as its results, and how both are stored and published with a claim.

### Modified Capabilities

- `site-publishing`: the claim page lists each paper once with its roles and facts, and counts its records of studies in people and in animals.
- `source-clients`: a paper is looked up by its PubMed number as well as by its DOI, and a stored paper record is refreshed when it is old.
- `open-data`: the data file holds the papers the claim pages show.

## Impact

- Pipeline: a new pure module that reads facts from a Europe PMC record; `sources/europepmc.py` gains a lookup by PubMed number; `events/trial_facts.py` reads `referencesModule`; `events/fetch.py` stores paper records; `export/build.py` gains `papers` on each claim and paper references on each trial. One new migration for a `paper_record` table.
- Requests: one Europe PMC request per distinct paper, about 150 on the first run for today's database (124 results papers and 19 origin papers, less overlap), cached and refreshed no more than monthly. No key. No model call.
- Site: `site/src/pages/[slug].astro`, a `Paper.astro` entry, a wording module for the paper codes, `site/src/lib/open-data.ts`, the method page, `site/export.schema.json`, `site/data/seed-export.json`.
- Coordination with `related-research`: its tasks 7.1 and 7.2 export approved papers as `related_research` and add their own section. With this change they export into `papers` with the role "related" and are shown as one group of "Papers on record". Whichever lands second takes that step; the task text there is updated by this change's task 1.3.
- Docs: `GLOSSARY.md` gains "Paper facts" and "Results paper"; `docs/sources.md` records which Europe PMC fields are republished and the terms read for them.
