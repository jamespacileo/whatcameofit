# Tasks

## 1. Candidates by a shared word

- [ ] 1.1 Add the checked-in list of words many treatments carry, and a pure function that gives a name's telling words (split on spaces, hyphens and punctuation, three letters or more); verify with a test on "RTS,S/AS01", "Genetically modified pig kidney transplant" and "Janssen COVID-19 vaccine"
- [ ] 1.2 Add a lookup in `claims/entry.py` that returns the claims sharing a telling word and a condition word with a read's names and condition, leaving out rejected, archived and merged claims, ordered as the spec says and cut at eight; verify with tests against the test database for the five scenarios of "A claim named in other words for the same condition is a candidate"
- [ ] 1.3 Give `NamedClaim` the reason it was offered and set it in every existing lookup (name, substance, title, slug); verify the existing candidate tests pass unchanged apart from the new field
- [ ] 1.4 Add `GLOSSARY.md` entries for "telling word" and "candidate" as used here; verify the terms in code and spec match them

## 2. The read offers them

- [ ] 2.1 In `LinkRead._claim_it_reports`, append the word candidates after the existing ones without displacing any; verify with tests for the three scenarios of "Candidates by shared words never displace another candidate"
- [ ] 2.2 Record how the joined claim was found in the lead's detail, and the reason of every candidate in the logged decision; verify with a test for "A join through a shared word" and one where the decision joins nothing
- [ ] 2.3 Update `docs/url-to-claim.md` (the allocate step and its table row); verify the Mermaid block still renders

## 3. Measure before turning on

- [ ] 3.1 Add a read-only report that, for a list of claim pairs, says whether each lookup offers the older claim, and for all claims how many candidates each lookup gives; verify it reproduces the figures in `design.md` on a copy of the 16 November database
- [ ] 3.2 On the writer, ask the same-claim decision about the candidates of the 95 audited pairs and of 100 claims that are not duplicates, joining nothing; record under this task how many of the 95 it joins, how many of the 100 it would wrongly join, how many pairs that join today no longer do, and the cost
- [ ] 3.3 Stop and report to the operator if wrong joins on the sample are not zero or any pair that joins today no longer does; otherwise record the go-ahead here

## 4. A drafted claim that shares an approved trial

- [ ] 4.1 Add a lookup of the claims that share an approved `clinicaltrials.gov` match with a claim for a condition sharing a word, leaving out rejected, archived and merged claims; verify with tests for the four scenarios of "A drafted claim that shares an approved trial is asked about again"
- [ ] 4.2 In `decide_prepared_lead_claim`, after the substance twin check, ask the same-claim decision about those claims and on a join reject the draft by rule and call `join_articles`; verify with tests for the three scenarios of "A draft the decision joins is rejected and its articles kept"
- [ ] 4.3 Make the lead's detail for such a join say it joined after the registry search by a shared trial, with both probabilities; verify in the test of 4.2
- [ ] 4.4 Confirm a claim drafted from a reader's lookup lead takes the same path with no audit hold; verify with one test, or record here that leads from lookups are not yet turned on and the path is shared

## 5. The audit list

- [ ] 5.1 Show under each held claim in `thenwhat audit list` the claims sharing an approved trial with it and the registry numbers, worded as a pair to look at; verify with one success test and the two scenarios of "The audit list shows claims that share an approved trial"
- [ ] 5.2 Add the pair listing to the audit section of `docs/daily-run.md` or `docs/backfill-loop.md`, whichever describes `audit list`; verify the documented command prints the lines described

## 6. Integration

- [ ] 6.1 Run `make check`; verify ruff, ty, pytest and the site build pass
- [ ] 6.2 On the writer, run one read batch and `thenwhat prepare --pending`, then `thenwhat audit list`; record here the number of duplicates the audit finds against the batch's size, to compare with 103 of 871

## Workflow follow-up

- Archive this change after `openspec/changes/social-link-backfill` is archived, so `lead-reading` exists in `openspec/specs/` for the delta to join.
