# Tasks

Group 1 is the gate: no later group starts until 1.5 is done and the operator has said to go on. Groups 1 and 2 touch no code. Groups 3 and 4 are one pull request each and may be built for the public site alone if the operator answers open question 5 with yes. Group 5 depends on 3 and on the operator's answers to open questions 1 to 3.

## 1. Validation (operator, with the assistant's help)

- [ ] 1.1 Check each vendor named in `design.md` against its current public pages (what it covers, where its coverage starts) and correct the design where memory was wrong; verify each name in the alternatives table has a dated source line in the pull request
- [ ] 1.2 Write a one-page description of the offer and a sample early-stage list from the current export, by hand, in the site's wording; verify the neutral-wording check passes on its text
- [ ] 1.3 Hold five conversations: at least two with people who scout early research (a mid-size biotech or a competitive-intelligence consultancy), one with a technology transfer office, one with a research funder; verify notes for each record what they use today, what they would need the list to hold, which health area, and whether they would pay
- [ ] 1.4 Ask in the same conversations whether a licence to an aggregator or a direct subscription is the likelier route; verify the notes answer open question 6 or say why not
- [ ] 1.5 The operator answers open questions 1 to 6 in `design.md` and the answers are written into it, dated and in the operator's words; verify no question is left open, or the change is closed as not pursued

## 2. Terms and decisions (no code)

- [ ] 2.1 Read each source's current terms for paid reuse of facts derived from it (ClinicalTrials.gov, Europe PMC, Crossref, OpenAlex, ROR, MeSH, GSRS, RxNorm, Open Targets, and any other in `docs/sources.md`) and record the answer, dated, in each source's entry; verify every source the export reads has an answer before any client or route is written
- [ ] 2.2 Read whether listing article titles, outlets and addresses in a paid service needs a UK news licence (NLA, CLA) and record the reading in `docs/sources.md`; verify the answer exists before group 5, and that the keyed route leaves articles out if the answer is unclear
- [ ] 2.3 Write the decision record for taking industry money (public and paid identical, paying changes no record, funded coverage disclosed) once the operator has answered open questions 1 and 2; verify it is in `docs/adr/` and linked from `CLAUDE.md`
- [ ] 2.4 Add "early-stage list" and "translation count" to `GLOSSARY.md`; verify the terms are used exactly in the spec and the tasks below

## 3. Early-stage list

- [ ] 3.1 Add a pure function that derives the list from exported claims (status in the two earliest, first-report date, whole years since at the export's date, overlay, approach, health area, organisations with roles); verify tests for a preclinical claim, a claim with no trial and a lower-band stage reading, a claim that gained a trial, and an archived claim
- [ ] 3.2 Carry the list in the export, regenerate `site/export.schema.json` and `site/data/seed-export.json`; verify the schema and seed tests pass
- [ ] 3.3 Add the list's page and data file to the site, ordered by first report, with the statement of what the tracker does not know; verify a site test finds the statement, that the neutral-wording check covers the page, and that a label containing "abandoned" fails the build
- [ ] 3.4 Look at the page at desktop and phone widths in both themes; record screenshots in the pull request

## 4. Translation counts

- [ ] 4.1 Add a pure function that counts published claims by year of first report and current status, with the minimum group size read from the environment; verify tests for a year under the minimum, a year over it, and an archived claim left out
- [ ] 4.2 Carry the counts in the export and regenerate the schema and seed; verify the schema and seed tests pass
- [ ] 4.3 Add the counts to the site with the statement of how claims were gathered, each figure beside the number counted; verify site tests find the statement, find no percentage for a year under the minimum, and find none of "probability", "likelihood" or "success rate"

## 5. Changes by key (only after the operator's answers allow it)

- [ ] 5.1 Add the keyed route to the site's service, answering status changes since a date for all claims or a named list, from the published export only; verify Worker tests for a watch list with one change, a date with no changes, no key, a revoked key and a preview build
- [ ] 5.2 Hold keys as hashes with the organisation's name and the one contact the operator agreed to hold, and add a command to issue and revoke a key; verify a test that a revoked key is refused and that no key is written to a log
- [ ] 5.3 Leave out of the route every fact the data file leaves out, by reading the same list of sources; verify a test with a claim whose drug card rests on a share-alike fact
- [ ] 5.4 State funded coverage on the method page from a dated list the operator keeps, and what is held about a customer on the privacy page; verify site tests for an area with funded coverage and for none
- [ ] 5.5 Document the route, the key commands and the coverage-on-request steps (`thenwhat prepare`, the audit, the export) in `docs/deploy.md` and the README's operator section; verify the documented commands run as written
