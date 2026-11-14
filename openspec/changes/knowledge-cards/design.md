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

Measured read-only on the real database after tasks 2.1 to 2.7 had run for every published claim, 2026-11-14, with a generic client name and no key:

- Links stored: 28 claims with an approved exact condition term and 7 more with only a broader one; 5 claims with an approved exact intervention term and 1 with only a broader one. So 35 of 84 claims would carry a condition card and 6 an intervention card.
- The 84 interventions have 108 other names and 130 search phrases. One intervention's name equals a MeSH descriptor's label. Ten equal an entry term (`lookup/term`, `match=exact`), and 17 claims have a name or other name that does; search phrases add no claim. "Ketogenic Diet" is an entry term of a descriptor labelled otherwise and `lookup/descriptor` answers `[]` for it; "orforglipron" is found as a term and not as a descriptor; "Baxdrostat" is found as neither. For conditions, 11 indications equal a descriptor's label and 20 equal an entry term.
- 67 interventions have no entry under any of their names. They are phrases in the report's words: "Comb-shaped electrical stimulation device", "Deep cervical lymphatic-venous anastomosis surgery", "Dental pulp stem cells in GelMA hydrogel", "CTX310".
- The registry gives each intervention of a trial a type. Across the 36 claims with a stored trial, the types carried are DRUG (27 claims), OTHER (11), PROCEDURE (9), BIOLOGICAL (8), DEVICE (7), BEHAVIORAL (4), DIETARY_SUPPLEMENT (3), DIAGNOSTIC_TEST (3), COMBINATION_PRODUCT (2), RADIATION (1). For 25 claims a trial lists an intervention whose name equals the claim's intervention name or another of its names: DRUG 21, BIOLOGICAL 3, PROCEDURE 2, DIETARY_SUPPLEMENT 2, DEVICE 1, COMBINATION_PRODUCT 1. The other types on a claim's trials belong to comparators and co-administered treatments.
- 28 general MeSH descriptors were checked by exact label and all exist, among them "Equipment and Supplies" (D004864), "Prostheses and Implants" (D019736), "Electric Stimulation Therapy" (D004599), "Surgical Procedures, Operative" (D013514), "Genetic Therapy" (D015316), "Gene Editing" (D000072669), "Cell- and Tissue-Based Therapy" (D064987), "Antibodies, Monoclonal" (D000911), "Diet Therapy" (D004035), "Tissue Engineering" (D023822) and "Biocompatible Materials" (D001672).
- 55 words in the interventions' names look like a gene symbol (a letter, then two to nine letters, digits or hyphens with a capital or a digit among them, after "anti-" and endings such as "-derived" are removed). Open Targets' target search returned, for words on 13 claims, a target whose approved symbol or listed symbol synonym equals the word. Seven are the gene meant or its receptor (GFAP, CXCR3, CPNE7, DLK1, APOE for "APOE4", SOSTDC1 for "USAG-1", GLP1R for "GLP-1" on two claims). Five are coincidences: "TMS" (magnetic stimulation) is a synonym of TYMS, "TOFA" of BTG3, "CSR" of SCARA3, "ASI" of ARSI, "Mar1" of RTL1.

Read in the code and observed at the sources on 2026-11-14, for group 2a (generic client name, no key):

- **MeSH entry terms.** `lookup/term?label=…&match=exact&year=<year>` compares the name with each term's own preferred wording and answers `[{"resource": "http://id.nlm.nih.gov/mesh/T713007", "label": "Ketogenic Diet"}]`: a term's identifier (`T…`), not the record it belongs to. It does not compare a term's plural or inverted variants ("Diets, Ketogenic" answers `[]`), and a word contained in a term answers `[]` ("Ketogenic"). A term's own record (`/mesh/2026/T713007.json`) names no owner. The owner is found by one query at `/mesh/sparql` (`format=JSON`, `year=<year>`, `inference=false`) from the term to the concept that lists it (`meshv:term` or `meshv:preferredTerm`) to the record that lists that concept (`meshv:concept` or `meshv:preferredConcept`); one query can ask for several terms. It answered `D055423`, a `TopicalDescriptor` labelled "Diet, Ketogenic", for the first and `C000729680`, an `SCR_Chemical`, for "orforglipron". There is no lookup for supplementary records by label (`lookup/supplemental…` answers 404).
- **A supplementary record** (`/mesh/2026/C000729680.json`) holds `label`, `note` ("An oral, non-peptide glucagon-like peptide-1 receptor agonist"), `source` (the paper NLM took it from), `preferredMappedTo` (two descriptors, chemical-structure headings) and `preferredConcept`. Its concept record holds no `scopeNote`. So its definition is the record's `note`, not its concept's `scopeNote`.
- **Open Targets** answers a GraphQL query sent by POST with 200 and the same query sent by GET with 500. `sources/base.py` has `_get` only, with a cache keyed by the address. A target found by `search(queryString, entityNames: ["target"])` carries `id` (an Ensembl gene identifier), `approvedSymbol`, `approvedName`, `biotype`, `symbolSynonyms` (each a label and the source that gives it: UniProt, HGNC or, seen when group 2a was built, NCBI Entrez; one label can be listed once per source, so a named-gene reason carries every source that gives the synonym), `functionDescriptions` (a list; for CXCR3 the first starts "[Isoform 1]: Receptor for the C-X-C chemokines…" and cites papers inline as "(PubMed:12782716)") and `proteinIds`. This settles the field `docs/sources.md` left unchecked.
- **The list of sources** (`sources/terms.py`) marks `opentargets`, `chembl` and `uniprot` as not accepted, under a comment that none is accepted before the operator's decision in task 6.1. A client may ask a source that is listed and not accepted; only the export reads `accepted`.
- **`claim_term`** stores `role` and `fit` as text with a check constraint each (`condition`, `intervention`; `exact`, `broader`), and is unique on claim, role, source and identifier. A candidate that already has a score is left as it is by a later run. `thenwhat terms --missing` picks published claims with no candidate at all, which after the first run is none of them.
- **The term's definition** is read by `mesh.describe` wherever a stored record is used, whatever its source.

## Goals / Non-Goals

**Goals:**

- A card never rests on a search result alone or on the registry's filing alone.
- Every word of a definition is its source's, attributed in the source's terms.
- The fewest new sources that give a card for a condition, an intervention and a target.
- Every kind of intervention can get a card: a drug, a device, a procedure, a diet, a cell or gene therapy, a code-named candidate. When the vocabulary does not hold the thing itself, the card is for the kind of thing it is, and says so.

**Non-Goals:**

- A card for every claim. An intervention that fits no kind on the list, or whose kind is not chosen with enough confidence, gets no card, and the page says nothing in its place.
- A second source for devices. A regulator's device classification names product types for one country's market and matches a report's wording no better than MeSH does.
- Gene variants. "APOE4" is an allele; the card is for the gene, and no source here defines the allele in a sentence the site could show.
- Plain-language rewriting. A definition written for indexers is less friendly than one a model could write, and it is the only kind the site can stand behind.
- A knowledge graph. Cards are not linked to each other, to other claims or to papers.
- A source's opinion of a drug's progress. ChEMBL's "max phase" and indications disagree with the registry often enough to contradict the status on the same page.

## Decisions

**Two sources, not five.** NLM's MeSH for what a condition or a class of intervention is; Open Targets for what a named drug is, what it acts on and what that target does. MeSH is the vocabulary the registry already files trials under, so the identifier arrives with the stored record and needs no search. Open Targets returns a drug's mechanisms and each target's description in one service, where ChEMBL plus UniProt would be two clients for the same facts. Wikidata is left out: its descriptions are too thin to be a card and its value here would be a link to Wikipedia, which is an open question below.

**Candidates come from the registry's filing and from exact labels only.** The registry's condition and intervention terms for a claim's approved trials, each with the count of trials carrying it; and MeSH terms whose label equals the indication, the intervention's name or another of its names, compared case-insensitively. A lookup's "contains" results are never candidates: the wrong first hit for "Obesity" is the reason. Terms carried by fewer than half the claim's trials are dropped before the check, which removes most of a large claim's long tail.

**Entry terms count as labels.** A MeSH descriptor lists entry terms, the other wordings NLM files under it. A name equal to an entry term is as checkable as one equal to the main label, and it is the vocabulary's own statement that the two mean the same. The candidate carries which entry term was equal. This is what finds "Ketogenic Diet", "Salpingectomy" and "Deep Brain Stimulation", and it reaches supplementary records, where NLM files compounds that have no descriptor yet. Search phrases are not compared: they were written for searching the registry, are looser than names, and added no claim when measured. Alternative considered: `match=contains`. Rejected for the reason above.

**An entry term is resolved to its record by one further request.** The lookup gives term identifiers; one SPARQL query gives the descriptor or supplementary record each belongs to, and that record's identifier is the candidate's. Both answers are cached like any other. A term whose owner the query does not return makes no candidate and is reported, not guessed from the label.

**A supplementary record gives a card like any term.** Its definition is its own `note`, word for word, where a descriptor's is its preferred concept's `scopeNote`; with no note the card carries the label and link. The headings NLM maps it to are not candidates: for "orforglipron" they are chemical-structure headings, which say less to a reader than the kind does. The paper in `source` is not shown.

**Every candidate is checked, including the registry's.** A new step, `term_match`, with three options: the term is the claim's condition or intervention, it is broader, it is something else. The endometrial cancer claim is why the registry's count is a reason and not a rule; the co-administered drugs among intervention terms are why the check sees the claim's intervention names. Alternative considered: approve a registry term by rule when most trials carry it. Rejected on the evidence above.

**"Broader" is an answer, not a failure.** A claim about hard-to-treat high cholesterol has no exact term; "Dyslipidemias" is still useful background. A broader link is approved on its own score and the card says it is broader. An exact link always wins over a broader one.

**An intervention with no exact term gets its kind, by a decision over a fixed list.** A new step, `intervention_kind`, with one option per kind and "none of these". The state judged is the claim's headline, summary and intervention names. The chosen kind's probability is the score, and the same two thresholds decide it. Each kind is tied in the code to one MeSH descriptor identifier, so the card is that term's record with NLM's definition, and the site writes nothing. The list is checked in and starts as:

| Kind code | MeSH descriptor |
| --- | --- |
| `drug` | Pharmaceutical Preparations |
| `antibody` | Antibodies, Monoclonal |
| `peptide` | Peptides |
| `oligonucleotide` | Oligonucleotides |
| `messenger_rna` | RNA, Messenger |
| `vaccine` | Vaccines |
| `gene_therapy` | Genetic Therapy |
| `gene_editing` | Gene Editing |
| `cell_therapy` | Cell- and Tissue-Based Therapy |
| `stem_cell_transplant` | Stem Cell Transplantation |
| `transplant` | Transplantation |
| `tissue_engineering` | Tissue Engineering |
| `biomaterial` | Biocompatible Materials |
| `device` | Equipment and Supplies |
| `implant` | Prostheses and Implants |
| `electrical_stimulation` | Electric Stimulation Therapy |
| `surgical_procedure` | Surgical Procedures, Operative |
| `radiotherapy` | Radiotherapy |
| `phage_therapy` | Phage Therapy |
| `probiotic` | Probiotics |
| `diet` | Diet Therapy |
| `dietary_supplement` | Dietary Supplements |
| `exercise` | Exercise Therapy |

All were found by exact label on the day measured. A kind is added by adding a row; a test asserts codes and identifiers are unique, and each kind's record is fetched when first used. The step runs only for a claim with no approved exact intervention term, because an exact term always wins and the decision would be paid for and unused. Alternatives considered: (a) a glossary of kinds written by the site. Rejected: it is the site explaining a treatment, which this change rules out, and the vocabulary already defines each kind. (b) Walking up the MeSH tree from a term. Rejected: 67 interventions have no term to start from. (c) The registry's intervention type as the kind. Rejected as the rule: it exists for 25 of 84 claims, its commonest values are DRUG and OTHER, and it has no definition. It is kept as a reason.

**A kind is a third way a link fits, below exact and broader.** `claim_term` gains the value `kind` beside `exact` and `broader`. A broader term the registry filed or a label gave ("Dyslipidemias") is nearer the claim than a kind ("Pharmaceutical Preparations"), so the card is chosen exact, then broader, then kind. The card says "the kind of treatment this is", not "broader".

**The registry's type is a reason on a kind link.** When an approved trial lists an intervention whose name equals one of the claim's intervention names, its type and the number of such trials are carried as a reason code with the registry's own type code (one reason per type, most trials first, when the registry lists it under more than one), worded by the site ("the registry lists it as a device in three of this claim's trials"). Types on the trial's other interventions are not read. It does not change the score.

**A named gene or protein is a candidate target, checked like a term.** Words in the intervention's name and other names are compared with human gene symbols: a target whose approved symbol or listed symbol synonym equals the word, without regard to case, is a candidate. Words are taken after removing a leading "anti-" and a trailing "-derived", "-mediated", "-targeting", "-based" or "-to-…". Each candidate goes to a step, `target_match`, with two options: the intervention acts on this gene's product or is made from it, or the word means something else. The five coincidences measured are why equality alone is not enough, and "GLP-1" matching the receptor's gene is why the reasons state that the word equals a synonym, not the symbol. The link is stored in `claim_term` with the role `target`, source Open Targets, the target's identifier, and the usual score, reasons and review columns.

**One target card, and the drug source's own target wins.** A drug whose record names exactly one single-protein target gets that target's card by rule, unscored, as before. Otherwise the approved named-gene link with the highest score gives the card, scored. The card's content is the same either way: the protein's name, the gene symbol and the function description with its origin.

**The named-gene card needs its own, smaller decision from the operator.** It reads Open Targets' target record only: the platform's own data is CC0 and the function description is UniProt's under CC BY 4.0, which the data file's licence can carry with credit. None of it is share-alike, so it does not wait for task 6.1. But the list marks both sources not accepted and the code says acceptance is the operator's, so task 2a.18 asks for it and records the answer in `docs/sources.md` and the list. Until then the client is written, candidates are checked and links are stored, and the export carries no target card. `chembl` stays not accepted until 6.1.

**A kind's term that is already a link is not linked twice.** The registry can file a claim's trials under the very term a kind is tied to ("Genetic Therapy"), and the table holds one link per claim, role, source and identifier. When the chosen kind's term is already a link for the claim's intervention, no second link is stored: an approved one already gives the card, a pending one waits for review, and a rejected one stays rejected, so the claim gets no kind card from it.

**A kind is asked for once.** The decision is logged against the claim with the options offered. A later run asks again only when the claim has no approved exact intervention term, no kind link, and no logged answer for the same list of kinds. Adding or removing a kind changes the list, so claims answered "none of these" are asked again and the others are not.

**A kind whose term the vocabulary does not hold stops the run.** Each kind's record is fetched and stored when first used. An identifier that answers nothing is an error that names the kind; no other term is tried.

**At most three candidate genes a claim.** The configured cap, three by default, keeps a long name from costing ten searches' worth of decisions. Words whose symbol itself is equal come before words equal to a synonym.

**A target's record is stored like a term's.** `term_record` under the source `opentargets` with the Ensembl gene identifier, the payload as answered and the fetch time; the link's label is the approved symbol. The card's description is the first entry of `functionDescriptions`, word for word, with its isoform prefix and its inline paper citations, credited to UniProt. Reading a record's label and definition goes through one function per source, not through the MeSH one.

**The base client gains a cached POST.** Open Targets refuses the query by GET. The cache key holds the source's name, the address and the request body, so two queries to one address do not share an answer. Rate, retries, the contact User-Agent and the refusal for an unlisted source are the same as for a GET.

**`thenwhat terms` gets a way to run again.** `--missing` keeps its meaning. `--all` takes every published claim: new candidates are gathered and scored, scored ones are left alone, the kind is asked for where the rule above allows, and named genes are checked. This is how the wider net reaches the 84 claims that already have candidates.

**The migration replaces two check constraints.** `role` gains `target` and `fit` gains `kind`; both are text with a named check, so the next migration drops and re-creates each check and its downgrade refuses, with a message, while a row holds a new value. Rows are not rewritten.

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
- [Coverage is uneven: a named drug gets three cards, a procedure one for its kind] → the section is absent when empty and no card is a placeholder; task 5.1 measures coverage and the change is not worth shipping below one claim in three with a condition card.
- [A kind card is too general to help: "Pharmaceutical Preparations" for a code-named compound] → it is the last choice after exact and broader, it is worded as the kind and not the thing, and task 5a.11 reads every kind card beside its claim; a kind whose cards read as empty is removed from the list.
- [The kind decision picks a plausible wrong kind: a hydrogel carrying cells read as a biomaterial or as a cell therapy] → the score and reasons are shown, the operator rejects it, and a claim that fits two kinds equally scores below the threshold for both and gets none.
- [A word in a name equals a gene symbol by coincidence] → never shown on equality alone; the check reads the claim, a coincidence scores zero and is rejected by rule; task 5a.12 reads every approved named-gene link.
- [Open Targets discourages asking its API for one entity after another] → one search per candidate word, about 55 for today's claims, each cached; a word already answered is not asked again, and the run is not repeated on a schedule. If the count grows past a few hundred, the platform's data download is the stated route and a separate change.
- [The SPARQL service is slower or less available than the lookup] → one query per claim's found terms, cached; a failure leaves those names without a candidate for this run and is reported, and the next run asks again.
- [A target card suggests the intervention is known to work through that gene] → the card describes the gene's product and says the report names it; it does not state a mechanism, which only the drug card does and only from its source.
- [A source renames a field or goes down] → clients are tolerant and store the record as fetched; cards are derived from stored records, so an outage leaves existing cards in place.
- [MeSH's rate limit is not stated for records and lookups; for the SPARQL service NLM's Acceptable Use Policy, read when group 2a was built, asks for no more than 500 requests a minute from one address] → the client's default of two requests a second, which is 120 a minute; about 170 requests for the first run's terms; refreshed no more than every ninety days.
- [Open Targets' drug mechanisms are share-alike] → gated on the operator's decision as above; the condition and intervention cards do not depend on it.
- [Two more sources to credit on every page] → the footer's source list is built from the export, as it is today.

## Migration Plan

1. `docs/sources.md` entries first, then the MeSH client, the candidate rules, the step, the two tables and one migration, then the export.
2. Run for every published claim; measure; read the approved links.
3. Entry terms, the kind step and the named-gene check, with one further migration for the `kind` value and the `target` role. `claim_term` holds real links by now, so this is a new migration and not a rewrite of the first. Run again for every published claim; a link an operator rejected stays rejected.
4. Site with condition, intervention, kind and named-gene target cards. An export without cards builds as today.
5. Drug cards, and the target card a drug's record gives, after the operator's licence decision, as a second deploy.
6. Rollback: revert the site deploy. Stored links and records can stay; nothing else reads them.

## Open Questions

- Whether a card should link to the term's Wikipedia article. Wikidata can map a MeSH identifier to an article title under CC0 and a link copies no text, but it is a third source and a link to a page the site cannot vouch for. Deferrable: it adds one optional field to a card.
- Whether a site-written glossary of a dozen general terms ("monoclonal antibody", "gene therapy") would serve readers better than the vocabulary's definitions of the kinds. The kind card answers the need with the source's words; task 5a.11 reads them as a reader would. If they read badly, a glossary is site wording reviewed by the operator, and a separate change.
- Whether a condition with no term should get a kind as an intervention does. Not done: a claim already carries a health area, which is the site's own answer to "what kind of condition", and 35 of 84 claims have a condition card against 6 with an intervention card.
- Whether the registry's type should be shown on the claim page when there is no card at all. It is a code with no definition, so it would be a line and not a card. Deferrable.
