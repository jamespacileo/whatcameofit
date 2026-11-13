# Tasks

## 1. Search phrases

- [x] 1.1 Add `intervention_search_phrases` (at most three) to the extraction schema and prompt, dropping generic words; verify the extraction tests cover a device with no name and a named drug
- [x] 1.2 Add a migration for `entity.search_phrases` and `entity_match.reasons`; verify it applies and reverses against the test database
- [x] 1.3 Store phrases on the intervention entity when a draft is saved, apart from synonyms; verify the entry test
- [x] 1.4 Search the registry by each phrase within the indication in `resolve`, under the more-than-a-hundred-or-none rule; verify on a recorded fixture that a trial found only by a phrase becomes a candidate
- [x] 1.5 Add "Search phrase" to `GLOSSARY.md` and regenerate `site/export.schema.json` if the export shape changed; verify `make check`
- [x] 1.6 Add `thenwhat entity phrase` so an operator can give a decided claim a search phrase, since a decided claim's article is never read again; verify one success and one refusal
- [ ] 1.7 On the real database: apply migration 0008, give `tourette-syndrome-wrist-nerve-stimulation` the phrase "median nerve stimulation", run `thenwhat resolve` on it, and record in `docs/lookup.md` whether NCT05269953 is now a candidate (the registry returned it for that phrase within "Tourette syndrome" when asked directly on 2026-11-13)

## 2. People

- [ ] 2.1 Limit extraction's people to researchers and drop single given names; verify the test for an article naming a reporter, a patient and a professor
- [ ] 2.2 List stored person entities with their claim for the operator, and delete those the operator marks; verify one success and one refusal of the command

## 3. Literature search

- [ ] 3.1 Read OpenAlex's current terms, key rules, allowance and headers and add its entry to `docs/sources.md`; add `OPENALEX_API_KEY` to `.env.example`
- [ ] 3.2 Write the OpenAlex client: search by words with a limit, refusal without a key, a stop when the allowance is used up, the key kept out of cache keys and logs; verify on recorded fixtures with a generic client name and replaced abstracts
- [ ] 3.3 Store up to twenty paper candidates per claim on the intervention entity with a one-line record; verify the resolution tests for a claim with no DOI, a paper found twice and a search that finds nothing

## 4. Scoring, reasons and rules

- [ ] 4.1 Add the `paper_match` step with its four options through `decide_many`; verify one backend call and one log entry per paper
- [ ] 4.2 Write the pure function that gives a candidate's reason codes; verify each code and the no-reason case
- [ ] 4.3 Apply `MATCH_REJECT_BELOW` to paper candidates and add `PAPER_ACCEPT_ABOVE`, which needs a reason; verify a high score with no reason stays pending
- [ ] 4.4 Show paper candidates in the review queue with kind, year, reasons and an another-indication label; verify the queue test
- [ ] 4.5 Add "Related paper" to `GLOSSARY.md` and the two settings to `.env.example`

## 5. Papers to trials and origin paper

- [ ] 5.1 On approval of a paper, look its registry numbers up through Europe PMC and add trial candidates, none when it states more than three; verify both cases on fixtures
- [ ] 5.2 Add the `origin_paper` step over approved papers dated on or before the first report, shown as a queue suggestion; verify it is skipped when the claim has an origin paper or no paper qualifies

## 6. Organisations

- [ ] 6.1 Read ROR's terms and limits and add its entry to `docs/sources.md`
- [ ] 6.2 Write the ROR client and store a candidate match for each institution and company entity, scored by ROR's own measure; verify a known and an unknown name on fixtures, and that a person entity causes no request

## 7. Export and site

- [ ] 7.1 Export approved papers as `related_research` with title, year, kind, link, score and reason codes and no abstract; regenerate `site/export.schema.json` and `site/data/seed-export.json`; verify the export tests
- [ ] 7.2 Add the related research section to the claim page with the site's wording for each reason and the note that a paper is not a trial record; verify the build fails on an unknown reason code and that a claim with no paper shows no section
- [ ] 7.3 Describe the section on the method page; verify the site build

## 8. Measurement

- [ ] 8.1 Run paper search on every claim whose status is "No trial record found" or "preclinical only", and record in `docs/lookup.md` how many gained an approved paper, how many gained a trial candidate, and the spend
- [ ] 8.2 Choose `PAPER_ACCEPT_ABOVE` from the operator's decisions on that run, or leave it empty, and note the choice

## Workflow follow-up

- Archive the change after the operator has reviewed the first measured run.

## 9. Public on-demand integration

- [x] 9.1 Record current API terms, free quotas and secret setup.
- [x] 9.2 Add bounded, cached OpenAlex/ROR Worker clients with independent failure and free-only allowance checks.
- [x] 9.3 Enrich live lookups with paper metadata and explicitly named organisations; preserve trial scoring/status.
- [x] 9.4 Add collapsed source-attributed sections on the site and next extension build, and update privacy text.
- [x] 9.5 Verify offline behavior, real-provider end-to-end lookups, quota/caching and responsive UI.
- [ ] 9.6 Deploy through checked CI and verify the production result.
