# Tasks

## 1. Terms, vocabulary and coordination

- [x] 1.1 Read ClinicalTrials.gov's data element definitions for a reference's type and record in `docs/sources.md` what `RESULT`, `DERIVED` and `BACKGROUND` each mean in the registry's own words, with the address and date read; verify the entry exists before any wording for "how listed" is written
- [x] 1.2 Read Europe PMC's current terms for republishing publication types, journal titles and subject headings, and record them in `docs/sources.md` with the fields this change republishes and the fields it never stores; verify the entry carries the date read
- [x] 1.3 Add "Paper facts" and "Results paper" to `GLOSSARY.md`, and edit `openspec/changes/related-research/tasks.md` 7.1 and 7.2 so approved papers are exported into `papers` with the role "related" and shown as a group of "Papers on record"; verify `openspec validate related-research --strict` still passes

## 2. Reading the facts

- [x] 2.1 Record Europe PMC fixtures with a generic client name and abstracts replaced: a randomised trial report, a preprint, a paper with "Humans" and "Animals" headings, and a known retracted paper; verify each loads in a test and holds no abstract text
- [x] 2.2 Add a pure function from an index record to paper facts: title, journal, year, open access; verify on the recorded fixtures
- [x] 2.3 Map publication types to the twelve kind codes in their fixed order, ignoring a type with no mapping; verify the Phase 3 randomised trial fixture gives randomised trial, clinical trial, article, and an unknown type adds no code
- [x] 2.4 Read people, animals or both from the "Humans" and "Animals" headings only, and the retracted mark from the publication type; verify each of the four heading cases, that "Mice" alone states nothing, and the retracted fixture. If the retracted fixture carries no mark, remove the retraction requirement from the spec delta and say so in design.md
- [x] 2.5 Read results references from a registry record in `events/trial_facts.py`: PubMed number and how listed, for `RESULT` and `DERIVED` only; verify on `study_NCT01596231_results.json` (one registry-linked paper), on a record with background references only, and that no citation text is returned

## 3. Storing records

- [x] 3.1 Add the `paper_record` table and its migration; verify it applies and reverses against the test database
- [x] 3.2 Add the lookup by PubMed number to the Europe PMC client; verify a known number, an unknown number and a malformed number on recorded fixtures
- [x] 3.3 At fetch, store a reduced record (no abstract, authors, author identifiers or affiliations) for the origin paper, each approved follow-up paper and each results paper of an approved trial, replacing a stored record only when it is older than the configured age; verify the stored payload names no author, a second fetch within the age makes no request, and a paper the index does not hold is stored as not held
- [x] 3.4 Add the setting for the refresh age to `config.py` and `.env.example`; verify the default of thirty days in a test

## 4. Export

- [x] 4.1 Export `papers` on each claim, one per identifier, with roles merged across DOI and PubMed number, `facts_as_of` and facts; verify export tests for an origin paper a trial also lists, a paper behind a rejected follow-up event, and a paper the index does not hold
- [x] 4.2 Export each trial's results paper identifiers; verify a trial with one sponsor-listed and one registry-linked paper
- [x] 4.3 Verify by test that a claim's status and explaining events are the same with and without papers, including a retracted results paper
- [x] 4.4 Regenerate `site/export.schema.json` and `site/data/seed-export.json`, and verify the checked-in `site/data/published-export.json` still validates against the new schema

## 5. Measurement before the page

- [ ] 5.1 Run a fetch against the real database and record in `docs/lookup.md`: papers stored, papers the index does not hold, requests made and the time taken
- [ ] 5.2 From that run, record how many papers carry "Humans" or "Animals", how many carry a kind other than article, and how many are marked retracted. If fewer than half carry either heading, change the count line in the site-publishing delta to count trials only before task 6.3

## 6. Site

- [ ] 6.1 Add the paper types to `site/src/lib/export.ts` and a wording module for kinds, roles, how a paper was listed and the people or animals statement, with a function naming any unworded code; verify a site test fails the build on an unknown kind and on wording containing "proves"
- [ ] 6.2 Add "Papers on record" to the claim page to `DESIGN.md`, grouped by role, each paper once, with the date its record was read, in place of "Matched papers"; link each results paper to its trial entry and each trial entry to its papers; verify in the browser at phone and desktop widths on a claim with an origin paper and on the claim with the most results papers
- [ ] 6.3 Add the count of records in people and in animals to the claim's facts; verify a claim with trials and a mouse paper, and a claim with neither shows no count
- [ ] 6.4 Carry papers into the open data file; verify the open data test finds a results paper with its trial and finds no author
- [ ] 6.5 Describe papers on the method page: where the facts come from, what "listed by the sponsor" and "linked by the registry" mean, and that a paper is not a trial record; verify the site build and the verdict-wording test
- [ ] 6.6 Build the site from an export without `papers`; verify the build succeeds and the page shows the present "Matched papers" section

## 7. Integration

- [ ] 7.1 Run `make check`, then compare the built entries of five papers with their Europe PMC pages, field by field; record any mismatch as a failing test before fixing it

## Workflow follow-up

- Archive the change after the operator has reviewed the first deployed pages.
