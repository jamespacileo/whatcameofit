# Proposal

## Why

A claim page names a condition and an intervention and assumes the reader knows what both are. Many do not: most visits are one claim page reached from outside, by someone who remembers a headline. A short, sourced note on what the condition is, what kind of thing the intervention is and, for a drug, what it acts on would make the page readable on its own, and useful to a reader who does know and wants the identifier.

Two things measured on 14 November 2026 shape how this can be done honestly:

- **Looking names up does not work well.** Six varied claims were tried against five open sources. The three named drugs were found; a code-named gene therapy, a procedure and a diet were found nowhere. Free-text conditions ("Knee osteoarthritis pain", "Type 2 diabetes in adults under 45") matched in at most three of six. A first search hit was often the wrong thing ("Anti-Obesity Agents" ahead of "Obesity").
- **The registry has already filed many claims under a subject term, and it is sometimes wrong.** Of the 36 claims with a stored trial record, 34 have a condition term carried by at least half their trials. But one claim about endometrial cancer has a Parkinson's disease term on most of its trials, and terms for the intervention usually name the other drugs in a trial's arms.

So a card cannot come from a lookup alone, or from the registry alone. Every link between a claim and a term is a candidate, checked and scored like every other match on the site.

## What Changes

- For each claim, candidate subject terms for its condition and its intervention are gathered by rule: terms the registry files the claim's approved trials under, and terms whose label equals one of the claim's own names.
- Each candidate is put to a bounded decision: is this term the claim's condition (or intervention), a broader term, or something else. The probability is the link's score. A link at or above the threshold is approved by rule; an operator can reject it.
- An approved term's own record (its label and its definition as the vocabulary's publisher wrote it) is stored with its fetch time and exported as a background card, with the score, the reasons and whether the term is exact or broader.
- For an intervention that is a named drug, a second card states what kind of molecule it is and what it acts on, and a third states what that target is, each from an open source and each attributed. This part ships only once the operator has accepted the licences involved, because one source is share-alike and the site's data file is not.
- The claim page gains a "Background" section of at most three cards, definitions closed until asked for. The site writes no explanation of its own.
- The open data file carries the cards whose licence allows it and names the ones it leaves out.

Not in this change: any text written by a model or by the site to explain a condition or a treatment; Wikipedia text; images or chemical structures; doses, side effects, approvals, or a source's own view of how far a drug has got, which would compete with the status; cards for conditions' genes or variants; any change to status.

## Capabilities

### New Capabilities

- `knowledge-cards`: how a claim's condition, intervention and target are tied to entries in open vocabularies, how each tie is scored and decided, and what is published as a background card.

### Modified Capabilities

- `source-clients`: a vocabulary term is looked up by identifier and by label; a drug and its target are looked up by name; a source is used only once its terms are recorded.
- `decision-steps`: checking a term against a claim is a decision step.
- `site-publishing`: the claim page shows background cards, attributed, with their score.
- `open-data`: the data file holds the cards its licence allows.

## Impact

- New sources, each needing its entry in `docs/sources.md` before its client is written: NLM's Medical Subject Headings (no key; NLM asks to be acknowledged and for the vocabulary's version to be stated; rate limit not found on the pages read) and, for the drug and target cards, Open Targets Platform (no key; the platform is marked CC0, with the parts drawn from ChEMBL under CC BY-SA 3.0 and target descriptions drawn from UniProt under CC BY 4.0).
- Pipeline: two source clients, a pure module that gathers candidates, one decision step, a `claim_term` table with the review columns and a `term_record` table, one migration, `review/queue.py`, `export/build.py`.
- Model cost: one bounded decision per candidate term, about ten candidates a claim; on the decisions backend that is three requests for today's 84 claims. Measured in task 5.1.
- Requests: two per approved vocabulary term (the term and its definition); 83 distinct terms today. One search and one record per named drug.
- Site: `site/src/pages/[slug].astro`, a card component, a wording module, `site/src/lib/open-data.ts`, the method page, the footer's source list, `site/export.schema.json`, `site/data/seed-export.json`.
- Docs: `GLOSSARY.md` gains "Background card" and "Subject term"; one ADR records the operator's decision on share-alike material.
