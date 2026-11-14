# Proposal

## Why

A claim page names a condition and an intervention and assumes the reader knows what both are. Many do not: most visits are one claim page reached from outside, by someone who remembers a headline. A short, sourced note on what the condition is, what kind of thing the intervention is and, for a drug, what it acts on would make the page readable on its own, and useful to a reader who does know and wants the identifier.

Two things measured on 14 November 2026 shape how this can be done honestly:

- **Looking names up does not work well.** Six varied claims were tried against five open sources. The three named drugs were found; a code-named gene therapy, a procedure and a diet were found nowhere. Free-text conditions ("Knee osteoarthritis pain", "Type 2 diabetes in adults under 45") matched in at most three of six. A first search hit was often the wrong thing ("Anti-Obesity Agents" ahead of "Obesity").
- **The registry has already filed many claims under a subject term, and it is sometimes wrong.** Of the 36 claims with a stored trial record, 34 have a condition term carried by at least half their trials. But one claim about endometrial cancer has a Parkinson's disease term on most of its trials, and terms for the intervention usually name the other drugs in a trial's arms.

So a card cannot come from a lookup alone, or from the registry alone. Every link between a claim and a term is a candidate, checked and scored like every other match on the site.

A third measurement, on the same day after the first terms had been run for all 84 published claims, showed who the first design leaves out:

- **Most interventions are not in any vocabulary under their own name.** Six claims had an approved term for their intervention. A device ("Wrist-worn median nerve stimulation device"), a procedure ("Genicular artery embolisation"), a diet, a cell therapy and a code-named candidate ("CTX310") are described in the report's words, and no label equals them. Comparing names with the vocabulary's own listed synonyms as well as its main labels raises the claims with a candidate from 1 to 17, and for conditions from 11 to 20. For the other 67 interventions the most a vocabulary can say is what kind of thing it is.
- **The thing a claim turns on is often a gene or protein named inside the intervention.** "Anti-CXCR3 antibody", "CPNE7-derived peptide" and "APOE4-to-APOE3 base editing" name one. Thirteen claims have a word in their intervention's names that equals a human gene's symbol or a listed synonym of one; about half are the gene meant and the rest are coincidences ("TMS" is also a symbol for a gene, "TOFA" another).

So the same rule holds for the wider net: a kind and a named gene are candidates, each checked and scored, never shown on a name's resemblance alone.

## What Changes

- For each claim, candidate subject terms for its condition and its intervention are gathered by rule: terms the registry files the claim's approved trials under, and terms whose label, or one of whose entry terms (the synonyms the vocabulary itself lists), equals one of the claim's own names. This reaches devices, procedures, diets and newly named compounds the vocabulary holds under another wording.
- An intervention with no approved exact term is put to a second bounded decision: which kind of intervention it is, from a fixed list (a device, a surgical procedure, a gene therapy, a cell therapy, an antibody, a diet and so on), or none of them. Each kind is tied in the code to one vocabulary term, and the chosen kind's term becomes the intervention's card, marked as the kind of thing and not the thing itself. When the registry lists the intervention by name with a type of its own, that is carried as a reason.
- A gene or protein named in the intervention's own names becomes a candidate for a target card when the name's word equals a human gene's symbol or a listed synonym of one. The candidate is checked and scored like a term. This card uses no share-alike material and does not wait for the drug card.
- Each candidate is put to a bounded decision: is this term the claim's condition (or intervention), a broader term, or something else. The probability is the link's score. A link at or above the threshold is approved by rule; an operator can reject it.
- An approved term's own record (its label and its definition as the vocabulary's publisher wrote it) is stored with its fetch time and exported as a background card, with the score, the reasons and whether the term is exact or broader.
- For an intervention that is a named drug, a second card states what kind of molecule it is and what it acts on, and a third states what that target is, each from an open source and each attributed. This part ships only once the operator has accepted the licences involved, because one source is share-alike and the site's data file is not.
- The claim page gains a "Background" section of at most four cards (the condition, the intervention or its kind, what a drug is and acts on, a target), definitions closed until asked for. The site writes no explanation of its own.
- The open data file carries the cards whose licence allows it and names the ones it leaves out.

Not in this change: any text written by a model or by the site to explain a condition or a treatment, including a site-written glossary of kinds (a kind's card is the vocabulary's own definition of the kind's term); Wikipedia text; images or chemical structures; doses, side effects, approvals, or a source's own view of how far a drug has got, which would compete with the status; a card for a gene variant (a claim that names "APOE4" gets the gene's card or none); cards for the genes of a condition; a second source for devices, such as a regulator's device classification; any change to status.

Covered elsewhere and not here: the universities, companies and sponsors a claim names are the `organisations` change. People are not shown in any form, because the site treats them as personal data.

## Capabilities

### New Capabilities

- `knowledge-cards`: how a claim's condition, intervention and target are tied to entries in open vocabularies, how each tie is scored and decided, and what is published as a background card.

### Modified Capabilities

- `source-clients`: a vocabulary term is looked up by identifier, by label and by entry term; a drug and its target are looked up by name; a gene is looked up by symbol; a source is used only once its terms are recorded.
- `decision-steps`: checking a term against a claim, choosing an intervention's kind and checking a named gene are decision steps.
- `site-publishing`: the claim page shows background cards, attributed, with their score.
- `open-data`: the data file holds the cards its licence allows.

## Impact

- New sources, each needing its entry in `docs/sources.md` before its client is written: NLM's Medical Subject Headings (no key; NLM asks to be acknowledged and for the vocabulary's version to be stated; rate limit not found on the pages read) and, for the drug and target cards, Open Targets Platform (no key; the platform is marked CC0, with the parts drawn from ChEMBL under CC BY-SA 3.0 and target descriptions drawn from UniProt under CC BY 4.0).
- Pipeline: two source clients, a pure module that gathers candidates, one decision step, a `claim_term` table with the review columns and a `term_record` table, one migration, `review/queue.py`, `export/build.py`.
- Model cost: one bounded decision per candidate term, about ten candidates a claim; on the decisions backend that is three requests for today's 84 claims. One more decision for each intervention with no exact term (79 of 84 today, fewer once entry terms are compared) and one for each named-gene candidate (13 today). Measured in task 5.1.
- Requests: two per approved vocabulary term (the term and its definition); 83 distinct terms today. One lookup per name, synonym and search phrase for entry terms (552 on the day measured, cached). One search and one record per named drug, and one search per candidate word for a gene (55 on the day measured).
- Pipeline, for the wider net: a list of kinds with their terms in the code, a `kind` value for how a link fits and a `target` role in `claim_term`, with one further migration.
- Site: `site/src/pages/[slug].astro`, a card component, a wording module, `site/src/lib/open-data.ts`, the method page, the footer's source list, `site/export.schema.json`, `site/data/seed-export.json`.
- Docs: `GLOSSARY.md` gains "Background card" and "Subject term", and for the wider net "Entry term" and "Intervention kind"; one ADR records the operator's decision on share-alike material.
