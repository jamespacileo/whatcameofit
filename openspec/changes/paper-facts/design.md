# Design

## Context

See proposal.md for the motivation. What the code and the data hold today:

- `events/fetch.py` looks the origin paper up in Europe PMC on every fetch, uses it to find follow-up papers and retraction notices, and stores nothing of it. A follow-up paper event stores the citing paper's whole Europe PMC record as its `raw_payload`, abstract and authors included.
- `EuropePmc.trial_numbers` already queries by `EXT_ID:<pmid> AND SRC:MED`; `EuropePmc.paper` queries by DOI only.
- `events/trial_facts.py` reads a registry record by fixed rules and skips every free-text description. It does not read `referencesModule`.
- The export lists papers only as crossref matches (a DOI and a title) and as follow-up events (a title and a link).
- `related-research` (tasks 3 to 8 open) will search for papers, score them, approve by rule and export them as `related_research` with title, year, kind, link, score and reasons.
- `docs/sources.md` on Europe PMC: no key, no stated rate limit, 2 requests a second by default, and "almost all material is copyright of publishers or authors, including abstracts… The site shows a paper's title and a link."

Measured on the real database, read-only, 2026-11-14: 221 trials hold a stored registry record; 77 list at least one paper and 58 list a results paper. The references are 49 of type `RESULT`, 75 `DERIVED` and 444 `BACKGROUND`; 523 of 568 carry a PubMed number. 24 claims have a paper entity, 19 of them with a DOI and an approved crossref match.

Observed in the three recorded Europe PMC fixtures: `pubTypeList` is present in all three ("Clinical Trial, Phase III; Randomized Controlled Trial; Journal Article" for a NEJM paper); `journalInfo`, `pubYear`, `isOpenAccess` and `citedByCount` in all three; `meshHeadingList` in one of three, with "Animals" and "Mice" and no "Humans"; `grantsList` in one of three. A registry reference observed in NCT01596231: `{pmid, type: "DERIVED", citation}`, where the citation is one string of authors, title and journal.

## Goals / Non-Goals

**Goals:**

- A results paper reaches the page because the trial's own record names it. No search, no score, no model.
- Every fact about a paper is one field of its index record, read by a rule a reader could repeat.
- The paper becomes one object in the export, as the trial did, so the page shows it once whatever brought it there.

**Non-Goals:**

- Reading a paper. No abstract or full text is parsed for outcomes, sample sizes or conclusions.
- Authors. The citation string in a registry reference and the author list in an index record are not carried anywhere.
- A second index. Crossref is asked only what it is asked today.
- Citation counts. A count reads as a ranking, and the site ranks nothing.

## Decisions

**Results papers are read from the stored registry record, by `events/trial_facts.py`.** The function gains a list of `(pubmed id, how listed)` for references of type `RESULT` and `DERIVED`; `BACKGROUND` is skipped. Only the PubMed number and the type are read: the `citation` string names authors and is left alone. Alternative considered: find results papers by searching the index for the trial's number. Rejected: it is the search `related-research` already owns, and the registry's own list needs no score.

**"How listed" is two codes, not a confidence.** `RESULT` becomes `listed_by_sponsor` and `DERIVED` becomes `linked_by_registry`. Both are statements of what the registry did, so neither gets a percentage. The site words the difference. Task 1.1 confirms the two types' meaning from the registry's own documentation before any wording is written; if `DERIVED` turns out to cover more than papers that cite the trial's number, the wording says exactly what it does cover.

**Paper records are stored in their own table.** `paper_record`: identifier (DOI in lower case, else `pmid:<number>`), source name, PubMed number, payload, fetched time; unique on identifier. Facts are derived from it at export by a pure function, as trial facts are. Alternative considered: derive from `http_cache`. Rejected: that cache expires, and an export must not depend on what happens to be cached. Alternative considered: hang the record on an `entity_match`. Rejected: a trial's results paper has no entity and no match.

**The stored payload is reduced before it is stored.** `abstractText`, `authorList`, `authorString`, `authorIdList`, `affiliation`, `investigatorList` and the full-text links are removed. The abstract is copyright and the names are personal data, and paper facts need neither. This differs from an evidence event, whose payload is stored unmodified; the table's docstring and `docs/sources.md` say so. Follow-up events keep their payload as they do today, because the follow-up rule needs the authors.

**Paper identity is the DOI, else the PubMed number.** A results paper arrives with a PubMed number and an origin paper with a DOI. The index record gives both, so a paper is keyed by its DOI once its record is read, and roles found under either identifier are merged onto one entry.

**The export gains `papers` on each claim and `papers` on each trial.** A claim's paper: identifier, link, roles, `facts_as_of`, and `facts` (null when the index does not hold it). A role is one of `origin`, `follow_up`, `trial_result` (with the trial's identifier and how it was listed) and `related`. A trial lists the identifiers of its results papers. Both fields default to empty, so `SCHEMA_VERSION` stays 1 and an older export still validates.

**`related-research` exports into `papers`.** Its approved papers become entries with the role `related`, carrying the score and reasons that change defines. Its own `related_research` list and section are not built separately. Whichever change lands second does the joining; task 1.3 edits the wording of `related-research` tasks 7.1 and 7.2 to say so, and touches nothing else there.

**Kinds are mapped from `pubTypeList` to twelve codes.** The registry's phase-specific trial types fold into `clinical_trial`; editorials, letters, comments and news into `comment`; "Journal Article" and "research-article" into `article`. A type with no mapping is ignored, not passed through, so the site never meets an unworded code from a new index label. The codes are emitted in a fixed order from most to least specific and the site shows the first.

**People or animals comes from two headings and nothing else.** "Humans" and "Animals" are the two MeSH check tags an indexer applies. Their presence is read literally: people, animals, or both. Nothing is guessed from "Mice", from a publication type or from a title. A paper with no headings yet, which is common for recent papers and preprints, says nothing. Alternative considered: Europe PMC's text-mined organism annotations. Rejected for now: they are mined from the text by a model, and this change is by rule; it is a contained later addition behind the same fact.

**Retraction is read from the index's publication type.** "Retracted Publication" marks the paper. No Crossref request is added. Task 2.4 verifies this on a record of a known retracted paper; if the index does not carry the mark reliably, the fact is dropped from this change and left to the existing origin-paper retraction events.

**The count of records in people is site arithmetic.** Trials plus papers filed as studies in people, and papers filed as studies in animals, counted from the export. The pipeline exports no summary.

**Paper wording lives in one site module**, as trial wording does: labels for kinds, roles, how a results paper was listed and the people or animals statement, one function naming unworded codes, and the same build-time check against verdict wording.

## Risks / Trade-offs

- [A registry-linked paper is about the trial but is not its results, such as a protocol paper] → the entry says how the paper was listed and shows its kind; nothing calls it "the results" unless the sponsor listed it as such.
- [A reader takes "randomised trial" as proof] → the entry names the kind and adds nothing; the section says a paper is not a trial record and does not set the status.
- [Most records lack subject headings, so the people or animals line is rare] → task 5.2 measures how many papers carry the two headings before the count line is designed in; if it is under half, the line counts trials only and says so.
- [About 150 requests on the first run] → the client's existing 2 a second pacing; under two minutes; later fetches ask only for records over thirty days old.
- [Europe PMC's terms on republishing index terms and publication types] → task 1.2 reads them and records them before the client is changed. Titles and links are already shown under the present reading.
- [The stored table grows without bound] → one row per paper a claim lists; 150 rows today.

## Migration Plan

1. One migration adds `paper_record`. Reversible by dropping the table; nothing else reads it.
2. Pipeline: results references in trial facts, the lookup by PubMed number, storage at fetch, then export. The first `thenwhat fetch` after deploy fills the table.
3. Site in the same deploy. An export without `papers` builds and shows the present "Matched papers" section.
4. Rollback: revert the deploy. The table can stay; nothing depends on it.

## Open Questions

- Whether a paper filed as a study in people should move a claim off "preclinical only". It is the same question `related-research` leaves open, it belongs to `status-derivation`, and nothing here depends on the answer.
