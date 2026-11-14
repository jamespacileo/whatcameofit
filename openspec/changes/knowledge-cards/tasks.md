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

## 3. Export

- [ ] 3.1 Export at most one card for the condition and one for the intervention, exact before broader, highest score first, with label, definition word for word, link, source, vocabulary version, score, reasons and date read; verify export tests for exact and broader both approved, only a broader term, and a term with no definition
- [ ] 3.2 Export a fact only from a source the list marks accepted, and no card that would then be empty; verify by test with a source marked not accepted
- [ ] 3.3 Verify by test that status, explaining events and evidence stage are the same with and without cards
- [ ] 3.4 Regenerate `site/export.schema.json` and `site/data/seed-export.json`, and verify the checked-in `site/data/published-export.json` still validates

## 4. Site

- [ ] 4.1 Add the card types to `site/src/lib/export.ts` and a wording module for card kinds, reasons and molecule kinds with a function naming any unworded code; verify a site test fails the build on an unknown code
- [ ] 4.2 Add "Background" to the claim page to `DESIGN.md`, after the records: each card's label, its definition in a disclosure marked as the source's words, the source's credit and version, the score and reasons, the date read, and the section's note that cards describe terms and are not advice or evidence; verify in the browser at phone and desktop widths on a claim with one card and a claim with two, and that a claim with none has no section
- [ ] 4.3 Add each card source to the footer's data sources from the export, and carry cards into the open data file with the sources left out named; verify the footer test and the open data test
- [ ] 4.4 Explain background cards on the method page: where they come from, how a term is chosen and scored, and that the words are the source's; verify the site build and the verdict-wording test

## 5. Measurement before release

- [ ] 5.1 Run `thenwhat terms --missing` on the real database and record in `docs/lookup.md`: candidates gathered, approved exact, approved broader, rejected, claims with a condition card, claims with an intervention card, model cost and requests made. If fewer than one claim in three has a condition card, stop and report before the site tasks ship
- [ ] 5.2 Read every approved link beside its claim and record how many are wrong or misleading; reject those. If more than one in twenty is wrong, raise the threshold and run again
- [ ] 5.3 Read ten definitions as a reader would and record any that read as advice or as a statement that a treatment works; bring those to the operator before release

## 6. Drug and target cards

- [ ] 6.1 Bring the share-alike question to the operator with the entry from 1.2, and record the decision as an ADR in `docs/adr/`; do not start 6.2 to 6.5 without it
- [ ] 6.2 Write the Open Targets client: a drug whose own name equals a given name, with kind of molecule and mechanisms, and a single-protein target's name, gene symbol and function description; verify on recorded fixtures a named drug with two mechanisms, a drug with none, and a procedure's name that returns nothing
- [ ] 6.3 Export a drug card and, for exactly one single-protein target, a target card, each only as the ADR allows; verify a drug with one target, a drug with two, and that no phase, approval or indication is exported
- [ ] 6.4 Show both cards on the claim page and keep share-alike facts out of the data file, naming the source left out; verify in the browser and by the open data test
- [ ] 6.5 Run on the real database and record how many claims gained a drug card and a target card

## 7. Integration

- [ ] 7.1 Run `make check`

## Workflow follow-up

- Archive the change after the operator has reviewed the first deployed pages. Groups 1 to 5 can ship and be reviewed before group 6.
