# Design

## Context

See proposal.md for the motivation. What the code and the data hold today:

- A claim's condition is a free-text field (`Claim.indication`), not an entity. Its intervention is an entity with a name, other names and search phrases.
- Every approved trial's full registry record is stored with its events. The record's `derivedSection` holds `conditionBrowseModule.meshes` and `interventionBrowseModule.meshes`: MeSH descriptor identifiers and terms the registry assigned. `claims/mesh_areas.py` already reads condition terms to suggest a health area.
- Bounded choices go through `decide_many`, which returns a probability per option and logs each choice. Matches are approved at or above `MATCH_ACCEPT_ABOVE` and rejected below `MATCH_REJECT_BELOW`.
- `docs/sources.md` holds each source's terms, key, limits and the date checked. `CLAUDE.md` requires that entry before a client is written.
- The open data file is offered under CC BY 4.0 (`LICENSE-DATA`).

Measured read-only on the real database, 2026-11-14: 36 of 84 published claims have a stored trial record. For 34 of them at least one condition term is carried by half or more of the claim's trials; for 14, an intervention term. Twenty claims have exactly one such condition term, and three have five or more. There are 83 distinct terms. Examples: "Chronic hepatitis B" gives "Hepatitis B" and "Hepatitis B, Chronic"; "High LDL cholesterol and triglycerides that are hard to treat" gives "Metabolic Diseases", "Dyslipidemias" and "Lipid Metabolism Disorders"; "Endometrial cancer" gives "Endometrial Neoplasms" and also "Parkinson Disease 4, Autosomal Dominant Lewy Body"; the same claim's intervention terms are "Paclitaxel", "pembrolizumab" and "Carboplatin", the drugs in its trials' arms.

Observed on 2026-11-14 with a generic client name and no key, on six varied claims (two named drugs, an antibody, a code-named gene therapy, a procedure, a diet):

| Source | Licence as its own page states it | Limit stated | Interventions found | Conditions found |
| --- | --- | --- | --- | --- |
| NLM MeSH lookup | NLM's terms: acknowledge NLM, state the MeSH version | not found | 0 of 6 | 1 of 6 |
| Wikidata | CC0 | 10 a minute without a contact in the User-Agent, 200 with one | 3 of 6 | 2 of 6 |
| ChEMBL | CC BY-SA 3.0 | not found | 3 of 6 | not searched |
| Open Targets Platform | CC0, with ChEMBL-derived parts CC BY-SA 3.0 | not found | 3 of 6 | 3 of 6 |
| UniProt | CC BY 4.0 | not found | not searched | not searched |

Details that matter below: MeSH's first hit for "Obesity" was "Anti-Obesity Agents"; a MeSH definition is on the term's concept record, a second request; Wikidata's description of a new drug was "chemical compound" and none of the three drug items carried a ChEMBL or MeSH identifier; ChEMBL returned 316 unrelated drugs for a procedure's name and an error after a minute for a diet; ChEMBL's indications for one drug did not include the claim's condition; Open Targets gave one drug two mechanisms with targets and another none, and a field had been renamed since older documentation.

## Goals / Non-Goals

**Goals:**

- A card never rests on a search result alone or on the registry's filing alone.
- Every word of a definition is its source's, attributed in the source's terms.
- The fewest new sources that give a card for a condition, an intervention and a target.

**Non-Goals:**

- Coverage. A procedure, a diet or a code-named candidate with no vocabulary term gets no card, and the page says nothing in its place.
- Plain-language rewriting. A definition written for indexers is less friendly than one a model could write, and it is the only kind the site can stand behind.
- A knowledge graph. Cards are not linked to each other, to other claims or to papers.
- A source's opinion of a drug's progress. ChEMBL's "max phase" and indications disagree with the registry often enough to contradict the status on the same page.

## Decisions

**Two sources, not five.** NLM's MeSH for what a condition or a class of intervention is; Open Targets for what a named drug is, what it acts on and what that target does. MeSH is the vocabulary the registry already files trials under, so the identifier arrives with the stored record and needs no search. Open Targets returns a drug's mechanisms and each target's description in one service, where ChEMBL plus UniProt would be two clients for the same facts. Wikidata is left out: its descriptions are too thin to be a card and its value here would be a link to Wikipedia, which is an open question below.

**Candidates come from the registry's filing and from exact labels only.** The registry's condition and intervention terms for a claim's approved trials, each with the count of trials carrying it; and MeSH terms whose label equals the indication, the intervention's name or another of its names, compared case-insensitively. A lookup's "contains" results are never candidates: the wrong first hit for "Obesity" is the reason. Terms carried by fewer than half the claim's trials are dropped before the check, which removes most of a large claim's long tail.

**Every candidate is checked, including the registry's.** A new step, `term_match`, with three options: the term is the claim's condition or intervention, it is broader, it is something else. The endometrial cancer claim is why the registry's count is a reason and not a rule; the co-administered drugs among intervention terms are why the check sees the claim's intervention names. Alternative considered: approve a registry term by rule when most trials carry it. Rejected on the evidence above.

**"Broader" is an answer, not a failure.** A claim about hard-to-treat high cholesterol has no exact term; "Dyslipidemias" is still useful background. A broader link is approved on its own score and the card says it is broader. An exact link always wins over a broader one.

**Links live in `claim_term`; records in `term_record`.** `claim_term`: claim, role (condition or intervention), source, identifier, whether exact or broader, score, reasons, and the review columns; unique on claim, role, source and identifier. `term_record`: source, identifier, payload, fetched time. A condition is not an entity, so `entity_match` cannot hold these links. Alternative considered: make the condition an entity. Rejected: it changes what a claim's identity is made of, which is a larger change than a card deserves.

**Thresholds are the match thresholds.** `MATCH_ACCEPT_ABOVE` and `MATCH_REJECT_BELOW`. One scale on the site, one pair of settings.

**The drug card is found by exact name and is not scored.** The drug source's own name for the drug must equal the intervention's name or another of its names. An exact name is a rule a reader can check, so the card carries that reason and no percentage. A search hit whose name differs is discarded: the 316 drugs returned for a procedure are the reason.

**The drug card carries two things.** The kind of molecule, as a code the site words, and each mechanism as an action code and a target's name. Not the source's phase, approval year or indications.

**A target card needs exactly one single-protein target.** Two targets would mean two cards and a longer page for a detail few readers want; a protein complex or a family has no one description. The card carries the protein's name, its gene symbol and the function description, with that description's own origin.

**Licences are checked by the export, from a list in the code that mirrors `docs/sources.md`.** Each source has a record: licence, credit line, whether its facts may enter the CC BY data file. The export carries a fact only from a source marked accepted. MeSH is accepted once its entry is written. Open Targets' ChEMBL-derived mechanisms are share-alike, which the data file's licence is not; they are exported for the page only after the operator records a decision in an ADR, and they never enter the data file, which names them as left out. Alternative considered: ship mechanisms now with attribution. Rejected: whether a share-alike fact on a page that also offers a CC BY file is acceptable is the operator's call, not a default.

**The site adds nothing to a card.** The page shows the label, the source's definition inside a disclosure marked as the source's words, the credit the source asks for, the score and reasons for a scored link, and the date read. No summary line, no "in plain words". The section sits after the records and before the share tools, under a note that cards describe terms and are not about the claim's evidence.

**Vocabulary version.** NLM asks that the MeSH version be stated. A term's record carries its own dates; the card states the year of the vocabulary as the record gives it, and task 1.1 confirms which field that is.

## Risks / Trade-offs

- [A definition mentions uses or treatments and reads as advice] → it is shown as the source's words, closed by default, under the section's note and away from the status; the footer notice stands on every page.
- [The check approves a subtly wrong term] → the card shows the score, the reasons and the source's link; the operator rejects it and it stays rejected; task 5.2 reads every approved link once before the page ships.
- [Coverage is low and uneven: drugs get three cards, procedures none] → the section is absent when empty and no card is a placeholder; task 5.1 measures coverage and the change is not worth shipping below one claim in three with a condition card.
- [A source renames a field or goes down] → clients are tolerant and store the record as fetched; cards are derived from stored records, so an outage leaves existing cards in place.
- [MeSH's rate limit is not stated] → the client's default of two requests a second; about 170 requests for today's terms; refreshed no more than every ninety days.
- [Open Targets' drug mechanisms are share-alike] → gated on the operator's decision as above; the condition and intervention cards do not depend on it.
- [Two more sources to credit on every page] → the footer's source list is built from the export, as it is today.

## Migration Plan

1. `docs/sources.md` entries first, then the MeSH client, the candidate rules, the step, the two tables and one migration, then the export.
2. Run for every published claim; measure; read the approved links.
3. Site with condition and intervention cards. An export without cards builds as today.
4. Drug and target cards after the operator's licence decision, as a second deploy.
5. Rollback: revert the site deploy. Stored links and records can stay; nothing else reads them.

## Open Questions

- Whether a card should link to the term's Wikipedia article. Wikidata can map a MeSH identifier to an article title under CC0 and a link copies no text, but it is a third source and a link to a page the site cannot vouch for. Deferrable: it adds one optional field to a card.
- Whether a site-written glossary of a dozen general terms ("monoclonal antibody", "gene therapy") would serve readers better than vocabulary definitions for interventions with no term. It would be site wording, reviewed by the operator, and is a separate change.
