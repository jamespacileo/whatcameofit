# Tasks

## 1. Sources and vocabulary

- [x] 1.1 Read NLM's current terms for MeSH data and its lookup and record services, and add the entry to `docs/sources.md`: terms, credit line, how the vocabulary's version is to be stated and which field gives it, any stated limit, the date read; verify the entry exists before the client is written
- [x] 1.2 Read Open Targets Platform's current licence page, API terms and limits, and add its entry, listing separately the licence of drug mechanisms (drawn from ChEMBL) and of target descriptions (drawn from UniProt); verify the entry names each licence with the address and date read
- [x] 1.3 Add "Background card" and "Subject term" to `GLOSSARY.md`; verify both are used exactly in later code and output
- [x] 1.4 Add the list of sources with licence, credit line, accepted or not, and whether facts may enter the data file, and make a source client refuse a request for a source the list does not hold; verify one refusal by test

## 2. Subject terms

- [x] 2.1 Write the MeSH client: a term by identifier with its definition, and terms whose label equals a name; verify on recorded fixtures with a generic client name a known identifier, an unknown one, and that "Obesity" does not return "Anti-Obesity Agents"
- [x] 2.2 Add `claim_term` and `term_record` with one migration; verify it applies and reverses against the test database
- [x] 2.3 Add a pure function that gathers a claim's candidates from its approved trials' stored records (condition and intervention terms carried by at least half the trials, with counts) and from exact labels, capped at the configured number; verify on fixtures a claim with six trials, a claim with no trial and a named drug, and a claim with no trial and a free-text condition
- [x] 2.4 Add the `term_match` step with its three options through `decide_many`; verify one log record per candidate and that a backend failure leaves the candidate without a score
- [x] 2.5 Store each candidate with its score, exact or broader, and reasons; approve at or above `MATCH_ACCEPT_ABOVE`, reject below `MATCH_REJECT_BELOW`; verify an exact term at 0.95, a broader term at 0.9, a wrongly filed term at zero, and that a link an operator rejected stays rejected
- [x] 2.6 Fetch and store the record of each approved term, refreshing one older than ninety days; verify a second run makes no request
- [x] 2.7 Add `thenwhat terms <slug…>` and `--missing`, and list pending links in the review queue; verify one success and one refusal of the command, and the queue test

## 2a. Entry terms, kinds and named genes

Added after group 2 was built, from the measurements and the code read recorded in design.md. Groups 3 to 5 were built meanwhile for exact and broader terms; group 5a carries these links through the export and the site.

Sources and words first:

- [x] 2a.1 Add to the MeSH entry in `docs/sources.md`, with the date read, what design.md records as observed: that `lookup/term` with `match=exact` finds an entry term and answers a term identifier, that a term's record names no owner, the SPARQL query that gives a term's descriptor or supplementary record, that a supplementary record's definition is its own `note`, and that no limit is stated for the SPARQL service; read NLM's page for the SPARQL service for any terms or limits before writing; verify the entry names both requests and the field
- [x] 2a.2 Add to the Open Targets entry in `docs/sources.md`: that the API answers POST and refuses GET, the fields a target carries (`approvedSymbol`, `approvedName`, `symbolSynonyms` with each one's source, `functionDescriptions`, `biotype`, `id`), that the description field is settled, and the line that no client is written before task 6.1 replaced by what 2a allows; verify the entry no longer lists the field as unchecked
- [x] 2a.3 Add "Entry term" and "Intervention kind" to `GLOSSARY.md`, and extend "Subject term" and "Background card" to cover a kind link and a named gene; verify each is used exactly in later code and output

Entry terms:

- [x] 2a.4 Extend the MeSH client: `terms_labelled` also asks `lookup/term`, resolves each found term to its record by one SPARQL query for all of them, and returns each record's identifier and label with the entry term that was equal (none when the label itself was); `term` reads a supplementary record and `describe` gives its `note` as the definition; verify on recorded fixtures (generic client name) "Ketogenic Diet" found by entry term only, "orforglipron" resolved to its supplementary record with its note, "Obesity" found once though label and entry term both match, a term whose owner the query does not return giving nothing, and that a name contained in a longer entry term returns nothing
- [x] 2a.5 Extend the candidate rule: `LabelMatch` carries the entry term, the new reason code holds the entry term and the name, a term found by both label and entry term carries the label reason only, entry-term matches rank with label matches ahead of registry terms under the cap, and search phrases are never compared; verify on fixtures a name equal to an entry term, a supplementary record as candidate, and a search phrase equal to an entry term that makes no candidate
- [x] 2a.6 Report, per claim, a name whose entry term could not be resolved, in the command's output and without failing the run; verify by the service test for that case

Data model:

- [x] 2a.7 Add `TermFit.KIND` and `TermRole.TARGET` and a new migration that drops and re-creates the two check constraints on `claim_term` with the new values; its downgrade refuses with a message while a row holds one; verify it applies and reverses against the test database with links already stored, and that the constraints test covers both new values
- [x] 2a.8 Replace the one MeSH reading of a stored record with one function per source that gives a record's label and definition (MeSH descriptor, MeSH supplementary record, Open Targets target); verify the existing term tests pass unchanged and a target record's first function description is returned word for word

Kinds:

- [x] 2a.9 Add the list of kinds from design.md, each a code with one MeSH identifier, as its own module; verify by test that codes and identifiers are unique, every identifier is a descriptor's, and the list has a stable order
- [x] 2a.10 Add the `intervention_kind` step through the decision interface: options are the kind codes and none of them, the state is the claim's headline, summary and intervention names, the log refers to the claim; verify one log record with every kind's probability, and that a backend failure is logged and returns no answer
- [x] 2a.11 Add the registry-type reason as a pure function over the claim's approved trial records: for an intervention whose name equals one of the claim's intervention names, its type and the number of such trials; verify three device trials give the type and the count three, and that a comparator's type is not read
- [x] 2a.12 In the terms service, for a claim with no approved exact intervention term, no kind link and no logged answer for the same list of kinds: ask for the kind; when one is chosen, fetch and store its term's record (stopping with an error that names the kind when the vocabulary returns nothing), and store the link with fit `kind`, the score, and the reasons, unless that term is already a link for the claim's intervention; decide it by the two thresholds; verify a device at 0.9 approved by rule, a score between the levels left pending, "none of these" storing nothing and not asked again, a kind added to the list asking again, a claim with an exact term skipped, the kind's term already rejected by the operator staying rejected, and the unknown identifier error

Named genes:

- [x] 2a.13 Add a cached POST to the base source client, keyed by source, address and body, with the same pacing, retries, User-Agent and refusal for an unlisted source as `_get`; verify two bodies at one address get their own answers, the same body twice sends one request, and an unlisted source is refused
- [x] 2a.14 Write the target part of the Open Targets client: for a word, the targets whose approved symbol or a listed symbol synonym equals it without regard to case, each saying which was equal and, for a synonym, the source that gives it; and a target's record by its identifier; verify on recorded fixtures (generic client name) "CXCR3" by symbol, "USAG-1" by synonym, a word whose hits are all unequal returning nothing, and a target with several function descriptions
- [x] 2a.15 Add a pure function that takes candidate words from an intervention's name and other names: split on spaces and brackets, a leading "anti-" and a trailing "-derived", "-mediated", "-targeting", "-based" or "-to-…" removed, kept when a letter is followed by two to nine letters, digits or hyphens with a capital or a digit among them; verify "Anti-CXCR3 antibody", "CPNE7-derived peptide", "APOE4-to-APOE3 base editing", and that "Aspirin" and "Vitamin C" give no word
- [x] 2a.16 Add the `target_match` step with its two options, its state (the claim's headline, summary and intervention names, the word, the gene's symbol and name) and a log record per candidate referring to the claim and the gene; verify two candidates give two records and a backend failure leaves one without a score
- [x] 2a.17 In the terms service, gather a claim's candidate genes (at most `TARGET_CANDIDATES_MAX`, three by default, symbol matches first), store each as a link with role `target`, source `opentargets`, the gene's identifier, the approved symbol as label and the reasons (the word, symbol or synonym, the synonym's source), score those without a score, decide by the two thresholds, and keep the record of each approved one; add the setting to `config.py` and `.env.example`; verify "Anti-CXCR3 antibody" at 0.95 approved, "TMS" at zero rejected by rule, "APOE4" giving the gene APOE, four gene-like words keeping three, a second run sending no request, and that a link an operator rejected stays rejected
- [ ] 2a.18 Bring to the operator whether Open Targets' own data (CC0) and UniProt's function descriptions (CC BY 4.0, credited) are accepted for the page and the data file, with the two entries in `docs/sources.md`; record the answer and its date there and in the list of sources, leaving `chembl` not accepted; do not start 5a.1's target card without a yes. Tasks 2a.13 to 2a.17 do not wait for it

Command and queue:

- [x] 2a.19 Add `--all` to `thenwhat terms` for every published claim, leave `--missing` as it is, and have the command run the term candidates, the kind and the named genes for each claim it is given, with a line per claim that counts each and names an approved kind and gene; verify one success and one refusal of the command, `--all` on a claim that already has scored candidates leaving them as they are, and that the command exits non-zero when any candidate stayed without a score
- [x] 2a.20 List pending kind and target links in the review queue with their role, fit and reasons, and let the operator approve or reject them as any term link; verify the queue test with one pending kind link and one pending target link
- [x] 2a.21 Update the pipeline `README.md` and the terms command's help for the kind and the named genes; verify `thenwhat terms --help` names all three and `--all`

## 3. Export

- [x] 3.1 Export at most one card for the condition and one for the intervention, exact before broader, highest score first, with label, definition word for word, link, source, vocabulary version, score, reasons and date read; verify export tests for exact and broader both approved, only a broader term, and a term with no definition
- [x] 3.2 Export a fact only from a source the list marks accepted, and no card that would then be empty; verify by test with a source marked not accepted
- [x] 3.3 Verify by test that status, explaining events and evidence stage are the same with and without cards
- [x] 3.4 Regenerate `site/export.schema.json` and `site/data/seed-export.json`, and verify the checked-in `site/data/published-export.json` still validates

## 4. Site

- [x] 4.1 Add the card types to `site/src/lib/export.ts` and a wording module for card kinds and reasons with a function naming any unworded code; verify a site test fails the build on an unknown code (molecule kinds are worded in 6.4, when the export first carries one)
- [x] 4.2 Add "Background" to the claim page to `DESIGN.md`, after the records: each card's label, its definition in a disclosure marked as the source's words, the source's credit and version, the score and reasons, the date read, and the section's note that cards describe terms and are not advice or evidence; verify in the browser at phone and desktop widths on a claim with one card and a claim with two, and that a claim with none has no section
- [x] 4.3 Add each card source to the footer's data sources from the export, and carry cards into the open data file with the sources left out named; verify the footer test and the open data test
- [x] 4.4 Explain background cards on the method page: where they come from, how a term is chosen and scored, and that the words are the source's; verify the site build and the verdict-wording test

## 5. Measurement before release

- [x] 5.1 Run `thenwhat terms --missing` on the real database and record in `docs/lookup.md`: candidates gathered, approved exact, approved broader, rejected, claims with a condition card, claims with an intervention card, model cost and requests made. If fewer than one claim in three has a condition card, stop and report before the site tasks ship
- [x] 5.2 Read every approved link beside its claim and record how many are wrong or misleading; reject those. If more than one in twenty is wrong, raise the threshold and run again
- [x] 5.3 Read ten definitions as a reader would and record any that read as advice or as a statement that a treatment works; bring those to the operator before release

## 5a. Export, site and measurement for entry terms, kinds and named genes

Groups 3 to 5 were built for exact and broader terms before group 2a was written. These carry 2a's links through them.

- [ ] 5a.1 Export the intervention's card exact before broader before kind, a kind card marked as the kind of intervention, and at most one target card from an approved named-gene link with its score and reasons; verify export tests for broader and kind both approved, only a kind, and a named gene with no drug record
- [ ] 5a.2 Export no target card while its source is not accepted, the approved link staying stored; verify by test with the target source marked not accepted
- [ ] 5a.3 Export a supplementary record's note as its card's definition and never the paper it was taken from, and a target card's first function description word for word with UniProt named as its origin; verify both by export tests
- [ ] 5a.4 Verify by test that status, explaining events and evidence stage are the same with and without kind and target links
- [ ] 5a.5 Regenerate `site/export.schema.json` and `site/data/seed-export.json`, and verify the checked-in `site/data/published-export.json` still validates
- [ ] 5a.6 Add to `site/src/lib/export.ts` and the wording module how a link fits (exact, broader, kind), the entry-term, kind and named-gene reasons and the registry's types; verify the site test fails the build on an unknown fit, reason or registry type
- [ ] 5a.7 Add to `DESIGN.md` and the claim page: a kind card says it is the kind of treatment and not the treatment, and a target card from a named gene says the report names it and states no mechanism; verify in the browser at phone and desktop widths on a claim with a kind card and a claim with a named-gene target card
- [ ] 5a.8 Credit Open Targets with the citation it asks for and UniProt for a target's description in the footer's data sources, and carry kind and target cards into the open data file; verify the footer test and the open data test
- [ ] 5a.9 Add to the method page what a kind card is and that the kind is chosen from a fixed list, and that a target card from a named gene means the report names the gene and not that the treatment is known to work through it; verify the site build and the verdict-wording test
- [ ] 5a.10 Run `thenwhat terms --all` on the real database and add to `docs/lookup.md`: new candidates from entry terms, claims with an intervention card by exact, broader and kind, kinds chosen with their counts, claims given "none of these", named-gene candidates approved and rejected, model cost and requests made
- [ ] 5a.11 Read every kind card beside its claim and record, per kind, how many are wrong and how many are true but say nothing useful; reject the wrong ones, and remove from the list a kind whose cards mostly say nothing
- [ ] 5a.12 Read every approved named-gene link beside its claim and record how many are coincidences or name a gene the intervention does not act on; reject those. If more than one in twenty is wrong, raise the threshold and run again
- [ ] 5a.13 Read every new approved link from an entry term beside its claim, as 5.2 did for the first run; reject the wrong ones

## 6. Drug and target cards

- [ ] 6.1 Bring the share-alike question to the operator with the entry from 1.2, and record the decision as an ADR in `docs/adr/`; do not start 6.2 to 6.5 without it
- [ ] 6.2 Add the drug part to the Open Targets client from 2a.14: a drug whose own name equals a given name, with kind of molecule and mechanisms, and a single-protein target's name, gene symbol and function description; verify on recorded fixtures a named drug with two mechanisms, a drug with none, and a procedure's name that returns nothing
- [ ] 6.3 Export a drug card and, for exactly one single-protein target, a target card, each only as the ADR allows; verify a drug with one target, a drug with two, a drug's one target winning over an approved named gene, and that no phase, approval or indication is exported
- [ ] 6.4 Word molecule kinds in the wording module, failing the build on an unworded one; show both cards on the claim page and keep share-alike facts out of the data file, naming the source left out; verify in the browser and by the open data test
- [ ] 6.5 Run on the real database and record how many claims gained a drug card and a target card

## 7. Integration

- [ ] 7.1 Run `make check`

## Workflow follow-up

- Archive the change after the operator has reviewed the first deployed pages. Groups 1 to 5 can ship as built; 2a and 5a follow as a second release and be reviewed before group 6. Within 2a the order is as listed; 2a.18 is the operator's and can be asked at any point.
