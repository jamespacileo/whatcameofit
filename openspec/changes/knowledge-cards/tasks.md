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

Added after group 2 was built, from the measurement in design.md. Done before group 3, so the export is written once.

- [ ] 2a.1 Read how MeSH's lookup answers a name equal to an entry term and what a supplementary record holds (label, note, the heading it is mapped to), and add both to the MeSH entry in `docs/sources.md` with the date read; verify the entry states which request finds an entry term and which field, if any, is a supplementary record's definition
- [ ] 2a.2 Add "Entry term" and "Intervention kind" to `GLOSSARY.md`; verify both are used exactly in later code and output
- [ ] 2a.3 Extend the MeSH client to return terms with an entry term equal to a name, each with the entry term that was equal, and to read a supplementary record; verify on recorded fixtures "Ketogenic Diet" (entry term only), a supplementary record's label, and that a name contained in a longer entry term returns nothing
- [ ] 2a.4 Extend the candidate rule with the entry-term reason and leave search phrases out; verify on fixtures a name equal to an entry term and a search phrase equal to one that makes no candidate
- [ ] 2a.5 Add the list of kinds, each with one MeSH identifier, and fetch each kind's record; verify by test that every row has a stored record and that no two kinds share a term
- [ ] 2a.6 Add the `kind` fit and the `target` role to `claim_term` with a new migration; verify it applies and reverses against the test database with links already stored
- [ ] 2a.7 Add the `intervention_kind` step through the decision interface, run only for a claim with no approved exact intervention term; store the chosen kind's link with its score and the registry's type as a reason when a trial lists the intervention by an equal name; verify a device at 0.9, "none of these", a claim with an exact term that is skipped, the registry reason with its count, and that a backend failure stores nothing
- [ ] 2a.8 Mark Open Targets' target record accepted in the list of sources on its own line, apart from the ChEMBL-derived mechanisms, and write the target part of the Open Targets client: genes whose approved symbol or listed synonym equals a word, saying which, with the protein's name and function description; verify on recorded fixtures an approved symbol, a synonym, and a word whose search results are all unequal
- [ ] 2a.9 Add a pure function that takes the candidate words from an intervention's names (affixes removed as design.md lists them) and the `target_match` step with its two options; store each link with the role `target`; verify "Anti-CXCR3 antibody" at 0.95, "TMS" at zero and rejected, "APOE4" giving the gene, and that a link an operator rejected stays rejected
- [ ] 2a.10 Extend `thenwhat terms` to run 2a.4, 2a.7 and 2a.9 for the claims it is given, and list pending kind and target links in the review queue; verify the command's success and refusal tests and the queue test still pass

## 3. Export

- [ ] 3.1 Export at most one card for the condition and one for the intervention, exact before broader before kind, and at most one target card from a named gene with its score and reasons; highest score first, with label, definition word for word, link, source, vocabulary version, score, reasons and date read; verify export tests for exact and broader both approved, only a broader term, broader and kind both approved, only a kind, a named gene with no drug record, and a term with no definition
- [ ] 3.2 Export a fact only from a source the list marks accepted, and no card that would then be empty; verify by test with a source marked not accepted
- [ ] 3.3 Verify by test that status, explaining events and evidence stage are the same with and without cards
- [ ] 3.4 Regenerate `site/export.schema.json` and `site/data/seed-export.json`, and verify the checked-in `site/data/published-export.json` still validates

## 4. Site

- [ ] 4.1 Add the card types to `site/src/lib/export.ts` and a wording module for card kinds, how a link fits (exact, broader, kind), reasons, registry types and molecule kinds with a function naming any unworded code; verify a site test fails the build on an unknown code
- [ ] 4.2 Add "Background" to the claim page to `DESIGN.md`, after the records: each card's label, its definition in a disclosure marked as the source's words, the source's credit and version, the score and reasons, the date read, and the section's note that cards describe terms and are not advice or evidence; a kind card says it is the kind of treatment and not the treatment, and a target card from a named gene says the report names it and states no mechanism; verify in the browser at phone and desktop widths on a claim with one card, a claim with two, a claim with a kind card and a claim with a named-gene target card, and that a claim with none has no section
- [ ] 4.3 Add each card source to the footer's data sources from the export, and carry cards into the open data file with the sources left out named; verify the footer test and the open data test
- [ ] 4.4 Explain background cards on the method page: where they come from, how a term is chosen and scored, and that the words are the source's; verify the site build and the verdict-wording test

## 5. Measurement before release

- [ ] 5.1 Run `thenwhat terms --missing` on the real database and record in `docs/lookup.md`: candidates gathered, approved exact, approved broader, rejected, claims with a condition card, claims with an intervention card by exact, broader and kind, kinds chosen with their counts, claims given "none of these", named-gene candidates approved and rejected, model cost and requests made. If fewer than one claim in three has a condition card, stop and report before the site tasks ship
- [ ] 5.2 Read every approved link beside its claim and record how many are wrong or misleading; reject those. If more than one in twenty is wrong, raise the threshold and run again
- [ ] 5.3 Read ten definitions as a reader would and record any that read as advice or as a statement that a treatment works; bring those to the operator before release
- [ ] 5.4 Read every kind card beside its claim and record, per kind, how many are wrong and how many are true but say nothing useful; reject the wrong ones, and remove from the list a kind whose cards mostly say nothing
- [ ] 5.5 Read every approved named-gene link beside its claim and record how many are coincidences or name a gene the intervention does not act on; reject those. If more than one in twenty is wrong, raise the threshold and run again

## 6. Drug and target cards

- [ ] 6.1 Bring the share-alike question to the operator with the entry from 1.2, and record the decision as an ADR in `docs/adr/`; do not start 6.2 to 6.5 without it
- [ ] 6.2 Add the drug part to the Open Targets client from 2a.8: a drug whose own name equals a given name, with kind of molecule and mechanisms, and a single-protein target's name, gene symbol and function description; verify on recorded fixtures a named drug with two mechanisms, a drug with none, and a procedure's name that returns nothing
- [ ] 6.3 Export a drug card and, for exactly one single-protein target, a target card, each only as the ADR allows; verify a drug with one target, a drug with two, a drug's one target winning over an approved named gene, and that no phase, approval or indication is exported
- [ ] 6.4 Show both cards on the claim page and keep share-alike facts out of the data file, naming the source left out; verify in the browser and by the open data test
- [ ] 6.5 Run on the real database and record how many claims gained a drug card and a target card

## 7. Integration

- [ ] 7.1 Run `make check`

## Workflow follow-up

- Archive the change after the operator has reviewed the first deployed pages. Groups 1 to 5, with 2a, can ship and be reviewed before group 6.
