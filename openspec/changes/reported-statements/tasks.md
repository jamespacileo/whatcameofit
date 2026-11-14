# Tasks

## 1. Vocabulary and storage

- [ ] 1.1 Add "Reported statement" to `GLOSSARY.md`, saying how it differs from a claim and from a promise; verify the term is used exactly in every later task's code and output
- [ ] 1.2 Add the `reported_statement` table with the review columns, a normalised text key unique per article, the date the article was read, and its migration; verify it applies and reverses against the test database, and that a statement without an article is refused
- [ ] 1.3 Add `STATEMENT_ACCEPT_ABOVE` (0.8), the number of statements per article (6) and the copied-run length (8) to `config.py` and `.env.example`; verify the defaults in a test

## 2. Refusal rules

- [ ] 2.1 Add a pure function that refuses a statement over 200 characters, with a quotation mark, or containing a given person's name; verify each refusal and one acceptance
- [ ] 2.2 Refuse a statement that shares a run of consecutive words with the article at or above the configured length, compared on lower-cased words; verify on synthetic articles that a copied sentence is refused and that a drug name with a condition is not

## 3. Proposing and checking

- [ ] 3.1 Add `statements` to the extraction schema with kind, firmness, speaker and basis as fixed lists, and the rules to the instructions (own words, no quotation, no names, timelines stay promises, about the intervention only); verify extraction tests with a synthetic article that has an effect, a researcher's hope and a timeline give two statements and one promise
- [ ] 3.2 Add the `statement_check` step with its three options through `decide_many`, referring to the article and the statement's place; verify one log record per statement, that no record holds text from the article, and that a backend failure stores nothing for that statement
- [ ] 3.3 Store each checked statement with its confidence, approved by rule at or above the threshold and pending below; verify 0.9 is approved and 0.6 is pending, and that the marker-sentence test still finds no article text in any table
- [ ] 3.4 Run the proposing and checking in the existing extraction command for a pending claim; verify the CLI test for one success, and that refused statements are counted in the output

## 4. Decided claims

- [ ] 4.1 Add `thenwhat statements <slug…>` and `--missing`, reading each article under the same robots, archived-copy and pasted-text rules, extracting statements only; verify one success and one refusal, and that the claim's headline, summary, intervention, promises and entities are unchanged
- [ ] 4.2 Skip an article that already has statements unless `--again` is given, replacing only pending statements and skipping a proposal whose key matches an existing one; verify a second run makes no model call, and that a rejected statement is not created again under the same wording
- [ ] 4.3 Report an article whose text no longer matches its stored hash without overwriting the hash, and an article that cannot be read with the words that pasted text is needed; verify both outputs

## 5. Review and export

- [ ] 5.1 List pending statements in the review queue with their article's outlet and date, and allow approve and reject; verify the queue test and that a decision sets the log record's human label
- [ ] 5.2 Export approved statements on each claim with text, kind, firmness, speaker, basis, confidence and article address; verify export tests for mixed review states and that status, explaining events and evidence stage are unchanged
- [ ] 5.3 Regenerate `site/export.schema.json` and `site/data/seed-export.json`, and verify the checked-in `site/data/published-export.json` still validates

## 6. Measurement before the page

- [ ] 6.1 Run the command on ten articles of the real database and record in `docs/lookup.md`: statements proposed, refused by each rule, approved, pending, and the model cost against the monthly budget. Stop and report if the cost of all 104 articles would pass a quarter of the budget
- [ ] 6.2 Read the approved statements of those ten beside their articles and record how many misstate the article, are stronger than it, or name someone. If more than one in ten does, raise the threshold or tighten the instructions and run the ten again before the rest
- [ ] 6.3 Run the remaining articles and record the same figures, and which outlets could not be read

## 7. Site

- [ ] 7.1 Add the statement types to `site/src/lib/export.ts` and a wording module for kinds, firmness, speaker and basis that composes the attribution sentence, with a function naming any unworded code; verify a site test fails the build on an unknown kind and that the wording passes the verdict check
- [ ] 7.2 Add "What the report said" to the claim page to `DESIGN.md`, between the summary and the records, grouped by report, each statement with its confidence and its report's link, and the note that a statement is not a record; verify in the browser at phone and desktop widths on a claim with one report and a claim with several
- [ ] 7.3 Verify by site test that a page with a statement of an effect and a trial with posted results shows no word comparing them, and that a claim with no approved statement has no section
- [ ] 7.4 Carry statements into the open data file; verify approved statements are present and a pending one is not
- [ ] 7.5 Explain reported statements on the method page; verify the site build and the verdict-wording test

## 8. Integration

- [ ] 8.1 Run `make check` and confirm no test, fixture, log or cache holds article text

## Workflow follow-up

- Archive the change after the operator has reviewed the first deployed pages and the figures from 6.2.
