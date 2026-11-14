# Tasks

## 1. Prerequisites and vocabulary

- [x] 1.1 Confirm `related-research` tasks 6.1 and 6.2 are ticked (the registry's entry in `docs/sources.md`, its client, candidate matches for institution and company entities). If they are not, do them in that change first; verify `thenwhat resolve` stores a candidate match for a known institution on a recorded fixture
- [x] 1.2 Add "Organisation" and "Sponsor" to `GLOSSARY.md`, and note in `docs/sources.md` which five registry fields are republished and which are never exported; verify the entry carries the date read

## 2. Sponsors as entities

- [x] 2.1 Add `entity.named_by` with its migration, defaulting to article for existing rows; verify it applies and reverses against the test database
- [x] 2.2 At fetch, record each approved trial's organisation sponsor as a company or institution entity marked as named by a registry record, adding the mark to an entity the claim already has under that name; verify an industry sponsor no report named, a sponsor a report also named, and that a second fetch records nothing new
- [x] 2.3 Record no entity for a sponsor that is a person, by the two signs trial facts use; verify on `study_NCT04951479_comparison.json` (a sponsor-investigator classed "other")

## 3. Approval rule

- [x] 3.1 Approve by rule a new organisation match the registry marks as chosen, and leave any other pending; verify one chosen record, three records with none chosen, and that a match an operator rejected stays rejected on a later run
- [x] 3.2 Show organisation matches in the review queue with the registry's name, country and website; verify the queue test
- [x] 3.3 Raise the bar, by the operator's decision after 6.2 found 5.6% wrong: approve only when ROR chose the record and the name given is exactly one of its names, a one-word name letter for letter, never a record typed "other" or a journal title, and a government body only with its country; ask extraction not to record journals, news outlets, banks or analysts; verify each wrong match from the run stays pending on its recorded answer, and re-run 6.1 and 6.2

## 4. Export

- [x] 4.1 Export `organisations` on each claim: one per approved registry record or, with no approved match, per entity; roles "named in a report" with article addresses and "sponsor" with trial identifiers; the five registry fields, score and date read when identified; verify export tests for two spellings matched to one record, a sponsor of three trials, an unidentified start-up, and a person sponsor
- [x] 4.2 Refuse to export an organisation whose name equals a person entity of the claim; verify by test
- [x] 4.3 Add a pure function that says whether an article's host is an organisation's website host or a subdomain of it, and mark each article published by an identified organisation of its claim; verify a press office on a subdomain, a newspaper, a host that merely ends with the same letters, and an organisation that is not identified
- [x] 4.4 Verify by test that status and explaining events are the same with and without organisations
- [x] 4.5 Regenerate `site/export.schema.json` and `site/data/seed-export.json`, and verify the checked-in `site/data/published-export.json` still validates

## 5. Site

- [x] 5.1 Add the organisation types to `site/src/lib/export.ts` and a wording module for kinds and roles with a function naming any unworded code; verify a site test fails the build on an unknown kind and on wording containing "endorses"
- [x] 5.2 Add "Organisations named" to the claim page to `DESIGN.md`: each organisation once, ordered by role then name, sponsors linked to their trials, an unidentified organisation saying so, and the note that the registry does not verify an organisation's part; verify in the browser at phone and desktop widths on a claim with one organisation and the claim with the most
- [x] 5.3 Say beside a marked report that it is on that organisation's website; verify a marked and an unmarked report by site test, and that the wording passes the verdict check
- [x] 5.4 Verify by site test that no person entity's name from the fixture appears anywhere in the organisations section
- [x] 5.5 Carry organisations and the publisher mark into the open data file; verify the open data test
- [x] 5.6 Explain on the method page what an organisation's entry says, where it comes from and what the publisher mark means; verify the site build

## 6. Measurement and release check

- [x] 6.1 Run fetch and resolve against the real database and record in `docs/lookup.md`: organisation names looked up, identified, left unidentified, requests made, and how many source articles gained the publisher mark
- [x] 6.2 Read every organisation name in that run's export once, and record how many are a person, a department too vague to be an organisation, or matched to the wrong record. Reject wrong matches before release; if more than one in twenty is wrong, stop and report before the site task ships
- [x] 6.3 Run `make check`

## Workflow follow-up

- Archive the change after the operator has reviewed the first deployed pages.
