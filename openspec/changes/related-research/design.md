# Design

## Context

See proposal.md for the motivation. What the code holds today:

- `resolve/service.py` searches the registry with `[entity.name, *entity.synonyms]` and looks up a paper only by DOI. The live lookup already asks the model for search phrases; resolution does not.
- `EntityMatch` is keyed by entity, source name and external identifier, carries a score and a one-line `record_summary`, and follows the review states. Trial candidates hang off the intervention entity.
- `decide_many` answers one choice for up to twenty items per backend call. The `openai-decisions` backend sends them as `choice` questions.
- `EuropePmc.trial_numbers` reads registry numbers from a paper's abstract and treats more than three as a review.
- Extraction already returns people, institutions and companies. Nothing looks them up, and nothing limits who counts as a person.
- The production database holds real claims, so schema changes are new migrations.

Observed 2026-11-13, with a generic client name and no key:

- OpenAlex `GET /works?search=median nerve stimulation tourette`: 994 results; the first five include the Nottingham sham-controlled trial report (2023) and a 2026 paper by the same senior author, each with an ORCID and a ROR identifier on the authorship. Response headers give the cost (0.001 US dollars) and the remaining allowance.
- Europe PMC, same words: 42 results, with funders and publication types. The probe sorted by citations, so its ranking was not compared fairly.
- ROR `GET /v2/organizations?affiliation=University of Nottingham`: score 1.0, `chosen: true`, with website and a Wikidata identifier.
- ClinicalTrials.gov: the figures in proposal.md.

## Goals / Non-Goals

**Goals:**

- A claim with a description for an intervention reaches the trials a person would find.
- Papers reach the claim page without a new kind of evidence event and without touching `status/`.
- Every new step fits a seam that exists: a source client, a candidate match, a decision step, a review queue row, an export field.

**Non-Goals:**

- Calibrated probabilities. The scores are the model's own, as for trials; the reasons are what a reader can check.
- Organisations inferred from paper affiliations, and pages per organisation. Both need a decision on wording first (see Open Questions).
- A second literature source for coverage. One search source is enough to measure whether the section is worth having.

## Decisions

**Search phrases are their own field, not synonyms.** A new array column on `entity`, filled from a new `intervention_search_phrases` field in the extraction schema (the lookup's wording for the field is reused). Synonyms are names and the spec forbids descriptions among them; the site and the export treat synonyms as names. Alternative considered: put phrases in `synonyms` and filter at display. Rejected: it breaks "Other names are names" and every reader of that column would need the filter.

**A phrase is searched only within the indication.** The name as written keeps today's behaviour (unnarrowed up to 100 hits). A phrase is broader by nature, so it always carries `query.cond`, and the existing rule for more than a hundred hits or none applies.

**OpenAlex for the search, Europe PMC for the detail.** OpenAlex ranks by relevance over title, abstract and full text and returns institutions with ROR identifiers on each authorship, which the "named institution" reason needs. Europe PMC stays the source for a paper's registry numbers, looked up by DOI or PubMed number after approval, because that client and its behaviour are already recorded. Alternative considered: Europe PMC keyword search only, with no new client or key. Kept as the fallback if OpenAlex's terms or allowance change; the literature search sits behind one function so the source can be swapped.

**Paper candidates are `EntityMatch` rows on the intervention entity**, with `source_name` "openalex" and the DOI in lower case as `external_id` (the OpenAlex identifier when a paper has no DOI). This reuses the uniqueness rule, the review queue, rule rejection and the archive. Alternative considered: a `paper` entity per candidate. Rejected: twenty entities per claim, most of them rejected, and paper entities mean "a paper the article named".

**Reasons are stored on the match** as a new array column of codes, computed by a pure function from the paper record, the claim and its entities. The export passes the codes; the site owns their wording and fails the build on an unknown code, as it does for status labels.

**One decision step, four options.** `paper_match` with the options in the spec, sent through `decide_many`, so twenty papers are one Decisions call. The record text is title, year, kind, journal and abstract. Alternative considered: two questions per paper (a predicate and a relation). Rejected: the `decide` interface is one choice per item, and four options carry both answers.

**The origin paper suggestion is a second step, `origin_paper`**, asked once per claim after papers are approved: the item is the claim, the options are its approved papers dated on or before the first report plus "none". It is skipped when no paper qualifies. The suggestion is a queue row; `set_origin_paper` stays an operator or assistant action.

**Approval by rule needs a reason as well as a score.** `PAPER_ACCEPT_ABOVE`, empty by default. The existing `MATCH_REJECT_BELOW` applies unchanged. This follows the working rule that nothing is approved by score alone when the score could be about the wrong thing.

**Approved papers are exported as `related_research` on the claim**, not as evidence events. `status/` is not touched and the status explanation is unchanged.

**Organisations use ROR only.** It covers universities, hospitals, funders and companies, needs no key, is CC0, and returns a Wikidata identifier and website in the same record. The score is ROR's own; `chosen: true` scores 1. Alternative considered: Wikidata search for companies. Deferred: ROR's record already links to Wikidata, and a second client is not needed to store an identifier.

**People are restricted, not expanded.** The extraction prompt and schema description limit people to researchers, and a validator drops a single given name. Existing person entities are listed for the operator before any is deleted.

## Risks / Trade-offs

- [OpenAlex changes its allowance or requires payment] → the client reads the allowance headers, stops for the run when it is used up, and the search function can be pointed at Europe PMC.
- [A search phrase pulls in trials of a related but different intervention] → every candidate is still scored for the claim's indication, and the phrase rule drops phrases with more than a hundred hits.
- [The model's score is high for a paper that only mentions the intervention] → approval by rule needs a reason computed without the model; the page shows both.
- [Abstracts are copyrighted] → used in memory and in the HTTP cache for scoring, never exported; fixtures have abstracts replaced, as registry fixtures do.
- [A reader takes a listed paper as proof] → the section's wording says what a paper is and is not, and the reasons describe what was found.
- [Deleting person entities removes one a later feature wanted] → the names remain in the article; extraction can be run again under the new rule.

## Migration Plan

1. One Alembic migration adds `entity.search_phrases` and `entity_match.reasons`, both arrays with an empty default. Reversible by dropping the columns.
2. A claim still awaiting review gets phrases when `thenwhat prepare` reads its articles. A decided claim is never read again, so the operator gives it phrases with `thenwhat entity phrase`. Claims without phrases behave as today.
3. The export gains `related_research`; the site ships the section in the same deploy as the schema, so an older export still builds.
4. Rollback: leave `OPENALEX_API_KEY` empty. Paper search then refuses and nothing else changes.

## Open Questions

- Should an approved report of a study in people move a claim off "No trial record found"? Not needed for this change, which leaves status alone; it would be its own change to `status-derivation`.
- Pages per institution or company, and whether a list of a group's claims with their statuses reads as a verdict. A later change, after the operator decides the wording.
