# Proposal

## Why

A reader weighing a breakthrough asks who is behind it: which university or company did the work, who is running the trials, and whether the report they read came from a newsroom or from the institution's own press office. The pipeline already knows much of this and shows none of it. On 14 November 2026 the database held 271 institution entities on 74 claims and 42 company entities on 25, read from the articles, never looked up and never exported. Of the 222 trials on record, 207 have a lead sponsor that is an organisation, which the claim page now shows as a line inside each trial and nowhere else. And nothing marks a report that sits on the website of an organisation it names, though `docs/outlets.md` lists press offices among the outlets (kcl.ac.uk, newsroom.ucla.edu) and the seed claim's only report is on its university's own site.

`related-research` already plans the lookup itself: institution and company entities are sent to an open organisation registry and stored as candidate matches (its tasks 6.1 and 6.2, both open). It stops there on purpose, leaving showing them and any page per organisation to a later decision. This change is the showing, for one claim at a time.

## What Changes

- An organisation match the registry itself marks as its chosen answer is approved by rule. Any other stays pending and is not shown as identified.
- The lead sponsor of each approved trial, when it is an organisation, becomes an entity of the claim, marked as named by a registry record, and is looked up the same way.
- Each published claim exports its organisations once each, with the roles each plays for the claim (named in a report, sponsor of named trials), and, when identified, the registry's name, kind, country, website and record link with the match score.
- A source article on the website of an organisation the claim names is marked as published by that organisation.
- The claim page gains an "Organisations named" section, and the mark on such a report. An organisation that could not be identified is listed by the name the report gave, and says so.
- The open data file carries the organisations.

Not in this change: people in any form (researchers, authors, investigators), which the site treats as personal data; a page per organisation, or a list of an organisation's other claims; any score, rank or description of an organisation's standing; funders, which the paper records hold too rarely (one of three recorded fixtures) to show; journals, which belong to `paper-facts`; any change to status.

## Capabilities

### New Capabilities

- `organisations`: which organisations a claim names and in what role, how each is identified against an open registry, and what is published about it.

### Modified Capabilities

- `entity-resolution`: an organisation match the registry chose is approved by rule; a trial's organisation sponsor becomes an entity of the claim.
- `site-publishing`: the claim page lists the claim's organisations with their roles, and marks a report published by an organisation it names.
- `open-data`: the data file holds the organisations the claim pages show.

## Impact

- Depends on `related-research` tasks 6.1 and 6.2 (the organisation registry's terms in `docs/sources.md`, its client, and candidate matches for institution and company entities). They are done there, not repeated here.
- Pipeline: `claims/entities.py` and `events/fetch.py` (sponsor entities), `resolve/service.py` (the approval rule), `export/build.py` (`organisations` on each claim, a publisher mark on each article). One migration: where an entity was named (article, registry or both).
- Requests: one registry lookup per distinct organisation name, at most about 520 on the first run for today's database (313 entities and at most 207 sponsor names, fewer once repeated names are counted once), within the registry's stated 2,000 requests per five minutes, cached. No key. No model call.
- Site: `site/src/pages/[slug].astro`, a wording module for organisation kinds and roles, `site/src/lib/open-data.ts`, the method page, `site/export.schema.json`, `site/data/seed-export.json`.
- Docs: `GLOSSARY.md` gains "Organisation" and "Sponsor"; `PRODUCT.md` is unchanged.
