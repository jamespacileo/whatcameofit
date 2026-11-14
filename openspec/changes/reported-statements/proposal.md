# Proposal

## Why

A claim page gives a neutral headline and a two-sentence summary of a report, and then the registry's records. What the report itself said, the part a reader remembers ("pain relief for 80% of patients", "could replace knee surgery"), is nowhere on the page, so there is nothing to hold the records against. The only thing the pipeline keeps from an article beyond the summary is its timelines: 53 promises on 35 of 84 claims. News reports say much more than timelines, and they are held to a looser standard than a registry record, which is exactly why a reader needs to see the two side by side and told apart.

The name avoids "claim", which already means one intervention for one indication. A thing a report says is a **reported statement**.

## What Changes

- Extraction also returns up to six statements a report makes about the intervention, each in the site's own words, with its kind (effect, safety, how it works, who it could help, comparison with existing treatment, what it could lead to), how firmly the report puts it (as fact or as a possibility), who the report has saying it (by role, never by name), and what the report says it rests on (people, animals, laboratory work, or not said).
- Each statement is then checked against the article while the text is still in memory, as a bounded decision with a probability. That probability is the statement's confidence. A statement at or above the threshold is approved by rule; one below it waits and is not published.
- A statement that repeats a run of the article's words, carries a quotation, or names a person the article named is refused by rule before it is stored.
- A new command reads the article of an already-decided claim again, for statements only. It changes nothing else about the claim and stores nothing of the text.
- The claim page gains a "What the report said" section, above the records, with each statement attributed to its report and worded as a report's statement, never as a finding.
- The open data file carries the statements.

Not in this change: comparing a statement with a trial result or a paper and saying whether it held; quoting a report; statements from papers or registry records; timelines, which stay promises; any change to status.

## Capabilities

### New Capabilities

- `reported-statements`: what a source article says about a claim's intervention beyond its timeline, how each statement is worded, checked, scored, decided and published.

### Modified Capabilities

- `claim-extraction`: statements are part of a draft, and a decided claim's article can be read again for statements only.
- `decision-steps`: checking a statement against its article is a decision step.
- `site-publishing`: the claim page shows reported statements, attributed and apart from the records.
- `open-data`: the data file holds the statements the claim pages show.

## Impact

- Pipeline: `extract/schema.py` and the extraction instructions; a pure module for the refusal rules; `decide/steps.py` gains one step; a `reported_statement` table with the review columns and one migration; a `thenwhat statements` command; `review/queue.py`; `export/build.py`. New settings for the accept threshold and the number of statements per article.
- Model cost: for a new claim, the one extraction call it already makes, with a longer answer, plus one decision call per article. For the 104 articles of today's 84 claims, one extraction call and one decision call each, once. Measured in task 6.1 against the monthly budget before the backfill is run in full.
- Article text: read as today, under the same robots, archive and paste rules, hashed and dropped. Nothing new is stored of it.
- Site: `site/src/pages/[slug].astro`, a wording module for the statement codes, `site/src/lib/open-data.ts`, the method page, `site/export.schema.json`, `site/data/seed-export.json`.
- Docs: `GLOSSARY.md` gains "Reported statement".
