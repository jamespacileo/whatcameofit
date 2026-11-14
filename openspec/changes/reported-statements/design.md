# Design

## Context

See proposal.md for the motivation. What the code holds today:

- An article's text reaches the model once, in `extract_into_claim` (`extract/service.py`), which refuses any claim that is not pending. The text is hashed (`SourceArticle.content_hash`) and dropped. It never goes through `HttpCache`; the pipeline has no logging; `DecisionLog` and `LlmUsage` have no prompt column. A test puts a marker sentence in an article and asserts it is absent from every table.
- The instructions forbid copying sentences for the headline and summary only. Promises have no such rule, and the test draft's promise repeats the article's wording.
- Extraction is one `Llm.run("extraction", …, output_type=Draft)` call. It returns structured output and no probability.
- Bounded choices go through `decide` and `decide_many` (`decide/core.py`), which return a probability for every option and write one `DecisionLog` row per item. Existing steps: `evidence_stage`, `entity_match`.
- `thenwhat entity phrases` already gave decided claims something new without reading their articles, from the claim's own headline, summary and names. Statements cannot be made that way: they are exactly what the summary left out.
- Promises are de-duplicated per article by a normalised key of their text.
- The site's verdict check covers site-owned wording only. It never sees a headline, a summary or a promise.
- Model spend is capped per month in `Llm.run` and in the decisions backend.

## Goals / Non-Goals

**Goals:**

- A statement reaches the page only with a number for how sure the pipeline is that the report says it.
- Nothing more of an article is kept than is kept today.
- A statement cannot be mistaken, on the page or in the data, for a record or a finding.

**Non-Goals:**

- Fact-checking. The pipeline says what a report said, not whether it was right.
- Matching a statement to a trial outcome. That comparison is a verdict however it is worded.
- Statements from papers, press releases the article links to, or the registry.
- Calibrated probabilities. As with matches, the score is the backend's own.

## Decisions

**Two steps: the extraction proposes, a bounded decision checks.** The extraction call returns statements with no score. Each is then put to a new decision step, `statement_check`, with the article text as the state and three options: the article says this, the article says something weaker, the article does not say this. The probability of the first is the statement's confidence. Alternative considered: ask the extraction model for its own confidence per statement. Rejected: a self-reported number in structured output is not a probability, and the decision interface already logs every choice against a later human label. Alternative considered: no score, operator review only. Rejected by `docs/adr/0001-publish-by-rule-archive-to-remove.md`: nothing waits for a person.

**The middle option exists to catch inflation.** The commonest failure is a statement worded more firmly than its article ("cures" for "may help"). With only yes and no, the backend splits that case. With "says something weaker" it has somewhere to put it, and the probability of the first option falls.

**Refusal rules run before the check, in a pure function.** Given the article text, the statement and the claim's person entities: refuse a statement that shares eight or more consecutive words with the article (compared on lower-cased word runs), that contains a quotation mark, or that contains a recorded person's name. Refused statements are counted and dropped; they cost no decision call. Eight words is long enough to let a drug's name and a condition through and short enough to stop a copied sentence; task 2.2 tries it on synthetic articles and the number is a setting.

**Statements have their own table, with the review columns.** `reported_statement`: claim, source article, text, kind, firmness, speaker, basis, confidence, a normalised text key, and the `Reviewed` columns. Unique on article and key. Alternative considered: widen `promise`. Rejected: a promise has a date and sits in the timetable; a statement has neither, and promises are not reviewed item by item.

**The decision log refers to the article and a place, not to a statement row.** A statement is stored only after its check succeeds, so it has no id when the check is logged. The reference is `source_article:<id>:statement:<n>`, and the statement row keeps the same string so a later human label can be joined to its log record.

**Approval uses its own threshold.** `STATEMENT_ACCEPT_ABOVE`, 0.8 by default, the same number as `MATCH_ACCEPT_ABOVE` and the start of the site's top band. Below it a statement is pending and unpublished; there is no reject-by-rule band, because an unsure statement costs nothing to keep unseen. The review queue lists pending statements with their article's outlet and date.

**New claims get statements in the extraction they already make.** `Draft` gains a `statements` list and the instructions gain the rules. The check runs straight after, in the same command, while the text is in memory.

**Decided claims get a separate command that reads the article again.** `thenwhat statements <slug…>` or `--missing`. It uses the same retriever (robots, archived copy, pasted text), runs a narrower extraction that returns statements only, checks them, stores them, and drops the text. It does not call `extract_into_claim` and cannot change a claim's other fields. It compares the new text's hash with the stored one and says when they differ; it does not overwrite the stored hash, which records the first read.

**A re-read replaces pending statements only.** Approved and rejected statements stay. A proposal whose normalised key equals an existing statement of that article is skipped. This keeps an operator's rejection from being undone by the same wording; it does not stop the model proposing the same thing in other words, which is a known limit (see Risks).

**The speaker is a role and the text names no one.** Reports attribute hopes to named professors and patients. The page needs to know that a researcher said it, not who. The instructions forbid names, the refusal rule checks the claim's recorded person entities, and the schema's speaker field is a fixed list.

**The basis is the article's, kept apart from the claim's evidence stage.** `evidence_stage` is a reviewed fact about the claim. A statement's basis is what one article said about one statement, and the two can differ: a report about a mouse study can state a hope for people with no basis given.

**The site words every code and frames every statement.** Kinds, firmness, speaker and basis are codes. The page composes "The report said…" or "The report had a researcher saying it could…" from them, so the framing cannot be dropped by a statement's own text. The section sits between the summary and the records, under a note that a report's statement is not a record.

**No comparison is built, in the pipeline or on the page.** The proposal's "side by side" means two sections on one page. Nothing links a statement to a trial.

## Risks / Trade-offs

- [A statement misstates the report] → the check gives it a low probability and it stays unpublished; a published one shows its confidence and its report's link; the operator archives or rejects; the page's error link is beside it.
- [The same rejected statement returns in new words] → rejected statements are shown to the model's instructions as "do not propose" only if measurement in task 6.2 shows it happens; until then the operator rejects again.
- [A statement reads as the site's own claim] → every statement is composed inside the site's attribution wording, and the open data file carries the statement as a field named for what it is.
- [A defamatory or promotional report is repeated in the site's words] → statements are about the intervention only; the instructions exclude statements about people, companies' conduct and prices; the section links the report and says whose statement it is.
- [Model cost for the backfill] → one extraction and one decision call per article, 104 articles; task 6.1 runs ten first and records the cost against the monthly budget, and the budget check already stops a run that would exceed it.
- [Articles that cannot be read again] → `docs/outlets.md` already lists outlets that refuse; those claims have no statements until an operator pastes the text. The page shows no section, and says nothing is missing.
- [The article has changed since it was first read] → the command says so; the statements are of the article as read on that date, and each statement stores the date its article was read.

## Migration Plan

1. One migration adds `reported_statement`. Reversible by dropping the table.
2. Pipeline: refusal rules, schema and instructions, the step, storage, the command, the review queue, the export.
3. Backfill: ten articles, measure, then the rest.
4. Site in the deploy that follows the first backfill, so the section does not ship empty. An export without statements builds as today.
5. Rollback: revert the site deploy. Stored statements are unpublished by archiving or by leaving the export field empty.

## Decisions made while building

For the proposer to confirm.

- **The check is shown how the statement is put.** Each item gives the statement's text and its firmness, speaker and basis codes, so that "says something weaker" also covers a statement attributed to the wrong kind of speaker or given a firmer basis than the article gives.
- **Places count on across reads.** A statement's place is its position among every statement proposed for the article so far, so a read with `--again` counts on from the highest place already checked. Each log reference then names one check only, and a statement row joins to exactly one log record.
- **The length limit is a refusal, not a validation.** The schema does not cap a statement at 200 characters or the list at six: a long statement would fail the whole draft, claim included. The service refuses the long one and keeps the first six of the rest.
- **What counts as a quotation mark.** Double quotation marks of every kind, guillemets, the opening single quote, and a straight or closing single quote that opens a word. A closing single quote inside or after a word is an apostrophe and is allowed.
- **What counts as a name.** Any part of a recorded person's name of two letters or more, as a whole word starting with a capital letter, titles such as "Professor" left out. A family name alone is refused; a word that only looks like one in lower case ("a small sample") is not.
- **`--missing` covers published claims.** Approved and unarchived claims with an article that has no statement. Named claims may be in any review state. `--again` needs named claims.
- **An article that gave no statement is read again by a later `--missing` run.** Nothing records that an article was read for statements apart from the statements themselves. The spec only asks that an article with statements is skipped.
- **A statement that cannot be checked fails the command after the claim is saved.** `extract new`, `extract article` and `statements` commit the claim, its other fields and the decision records, say how many statements were not stored, and exit 1.
- **The changed-text message speaks of the page.** On the first ten articles, nine pages no longer matched their stored hash, mostly because of what the page shows around the article. The output says the text has changed since it was first read, if only around the article.
- **An operator's rejection labels nothing.** Approving a statement labels its check `says_this`. A rejection does not say whether the report said something weaker or nothing, and may be for another reason, so it leaves the label empty, as a rejected related paper does.
- **An assistant's decision on a statement makes `checked_by_person` false**, as one on a match or an event does.
- **The export's statement codes are fixed lists in its schema.** An unknown code stops the site build at the schema, which now names the value it refused. The site's own check names a code the schema gains before the site words it.
- **How sure the check is, in words.** "Very likely in the report" from 0.8, "Likely in the report" from 0.5, "Unsure it is in the report" below, then the percentage. The disclosure says the number is about the reading of the report, not about the treatment.
- **The kind "how it works" is worded "How it acts"**, since "works" is among the outcome words the site's check refuses.

## Open Questions

- Whether pending statements should be shown apart with their lower confidence, as candidate matches are. Left out here because an unsure statement is a likelier misstatement than an unsure match; it can be added without a schema change.
