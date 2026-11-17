# Design

## Context

See `proposal.md` for the motivation and the operator's decisions of 2026-11-17. What shapes the approach:

- **Trials carry MeSH condition terms already.** A stored ClinicalTrials.gov record has `derivedSection.conditionBrowseModule` with `meshes` (the terms for the trial's conditions) and `ancestors`, each an identifier and a label. `claims/mesh_areas.py` reads them for an advisory line and a table of 21 heading names (`MESH_GROUPS`). Nothing stores them per claim.
- **Papers carry MeSH headings too.** A stored Europe PMC `core` record keeps `meshHeadingList`. `events/paper_facts.py` reads it only for "Humans" and "Animals", and `docs/sources.md` says no other heading is read or shown and that the terms must be read again before republishing any further field.
- **The MeSH client exists.** `sources/mesh.py` reads a descriptor's record from NLM's MeSH RDF service and stores it in `term_record`. Observed on 2026-11-17 with a generic client name: `GET /mesh/2026/D009765.json` carries `treeNumber` (two for Obesity: `C18.654.726.750.500` and `C23.888.144.699.500`) and `broaderDescriptor`. The client does not read either yet.
- **The approach** is a nullable text column with no record of who set it. `terms/kinds.py` already has the pure `registry_types(trial_payloads, names)`, which counts registry intervention types for interventions named as the claim's.
- **A claim has exactly one vertical** (`claims` spec), and the site's topic pages, feeds and redirects are built on that.
- The writer is the Mac mini. The MacBook database is frozen. The fault tab is in a Google Sheet the pipeline has no client for.

## Goals / Non-Goals

**Goals:**

- Clinical categories per claim, set by rule, each traceable to the records that gave it.
- A clinical browse a clinician recognises: MeSH names, MeSH structure, nothing renamed.
- The mapping and the numbers needed to decide, later and on evidence, whether friendly topics are derived from the clinical ones.
- One deterministic way to set an approach, with its basis stored and shown.

**Non-Goals:**

- Changing how a claim is filed for general readers. That is the switch-over, a later decision.
- A category or an approach for every claim. What the records do not state stays empty.
- Writing to the Google Sheet from the pipeline.

## Decisions

### 1. Categories are derived from stored records, never stored themselves

A claim's clinical categories are a pure function of records both stores already hold: the registry records of its approved trials and the index records of its approved papers. They are computed when the export and the reports are built. There is no `claim_category` table.

*Why (decided by the operator on 2026-11-17, during apply):* the first design stored a row per claim and descriptor. It missed the truth store: the export is assembled once from either Postgres or the D1 store, and tests hold the two equal, so every stored field needs a D1 migration, merge statements, proof scenarios and push and pull code. A derived value needs none of that, cannot go stale when a match is rejected or a claim merged, and needs no recompute hooks.

Only the direct terms count: a trial's `meshes`, never its `ancestors`. The registry's ancestor list is flat, with no parent links, so it cannot draw a tree; everything broader comes from NLM's tree numbers (Decision 3).

The derivation reads through the export's `Records` interface, so it gives the same answer from either store.

### 2. From papers: major topics in the disease trees only

A paper's headings include check tags, ages, methods and drugs. The rule takes a heading only when it is marked as a major topic and one of its tree numbers begins with `C` (Diseases) or `F03` (Mental Disorders).

Trials are not filtered this way: the registry has already said the term is the trial's condition, whatever tree it is in. That is what lets a trial on ageing give "Aging", which is not in the disease trees.

*Alternative considered:* asking NLM's lookup for the claim's indication text. Rejected: an exact-label match on free text is a guess at identity, and the operator chose papers.

*Before any paper heading is published:* Europe PMC's and NLM's terms are read again and `docs/sources.md` is updated, as that file already requires. If the reading does not allow it, paper headings are not used and claims with no trial have no category. There is no third source.

### 3. The tree is read once per descriptor, through the existing client

`sources/mesh.py` gains the reading of `treeNumber` and `broaderDescriptor` from the record it already fetches. For every descriptor some claim has as a category, and each broader descriptor up to a tree's top, the record is stored in `term_record` as now. A descriptor's ancestors are found by tree-number prefix (`C18.654.726` is above `C18.654.726.750`), and the descriptor holding each prefix is known from the stored records.

Expected volume: a few thousand records for 970 claims, read once and refreshed with the MeSH year. At the client's 2 a second that is under an hour, well inside NLM's stated limit.

The export is refused while any needed record is missing. An incomplete tree would silently drop claims from category pages.

### 4. The topic mapping replaces `MESH_GROUPS`

`clinical/topics.py` holds, for each group and vertical slug, a tuple of descriptor identifiers with the label beside each as a comment. A topic covers a claim when one of the claim's categories has a tree number at or below a tree number of one of the topic's descriptors.

The 21 heading names in `MESH_GROUPS` become the first entries, by identifier. `claims/mesh_areas.py` keeps its advisory line and reads this mapping instead; the label table is deleted. There is then one mapping, not two.

Topics the disease tree does not hold are mapped like any other: `ageing` to "Aging" and "Longevity"; a weight-loss topic, if the operator adds one, to "Obesity", "Overweight" and "Weight Loss". Adding a topic is a config edit plus the existing configuration checks. Whether a new friendly topic is *shown* waits for the switch-over.

### 5. Derived topics are computed, not stored, and not shown

`derived_topics(categories, tree, mapping)` is pure. Nothing writes its answer to the claim, the export or a topic page in this change. The comparison and the advisory line are its only readers.

*Why not show them now:* the operator asked for a measured test first. Showing a claim under a second friendly topic *is* the switch-over, in part.

### 6. The comparison is the test

`thenwhat clinical compare` prints the counts in the `clinical-classification` spec; `--disagreeing` lists the claims; `--tsv` prints fault-tab rows; `--uncovered` lists categories no topic covers, most claims first, which is the worklist for the mapping.

A disagreement is one of three things, each with one response:

- **The model filed it wrongly.** `claim edit --vertical`, and a row in the fault tab.
- **The mapping is wrong or thin.** The mapping is corrected, with a case in its pure test.
- **Both are defensible.** Nothing changes. These are the cases that being under several topics would resolve, and their number is one of the inputs to the switch-over decision.

The numbers to record here before the switch-over is proposed: agreement rate, share of claims with more than one derived topic, share with none, and the uncovered categories.

### 7. Category pages are addressed by descriptor identifier

`/clinical/D009765`, not a tree number and not a slug of the label. A descriptor with two tree numbers is one page with two broader links. Identifiers do not change when NLM rewords a label or moves a term; tree numbers and labels do, every year.

*Trade-off:* the address says nothing to a reader. The page title and links carry the name. Clinicians arriving from a search for a MeSH term see the name in the title.

The export carries, once, the nodes the site needs: identifier, label, tree numbers, for every category in use and above. The site builds parent and child links from tree numbers. Counts are of published claims, each counted once per page.

### 8. The approach rule

Unchanged from the first version of this change:

| Registry type | Approach |
| --- | --- |
| `DRUG` | `drug` |
| `DEVICE` | `device` |
| `PROCEDURE` | `surgery-or-procedure` |
| `GENETIC` | `gene-therapy` |
| `DIETARY_SUPPLEMENT` | `diet-or-lifestyle` |

`BIOLOGICAL`, `BEHAVIORAL`, `RADIATION`, `COMBINATION_PRODUCT`, `DIAGNOSTIC_TEST` and `OTHER` map to nothing: each covers more than one approach or none. The rule answers only when `registry_types` returns exactly one type and the table maps it. Two columns on the claim, `approach_decided_by` and `approach_basis`; existing rows keep the first empty, which the rule reads as "not mine". `claims/approach_rule.py` holds the table and one pure function; a session function enforces "never overwrite" and is called from `prepare`, the daily refresh and `thenwhat claim approaches` (`--dry-run`, `--unset`).

**The basis shown on the site is derived too.** The export states the registry's type and trial count whenever the registry's one type maps to the claim's approach, whoever set the approach: it is a fact about the registry, true of a person's approach as much as of a rule's. So the export needs neither column, and neither goes to the D1 store. The columns stay in Postgres only, where they decide what the rule may overwrite. Decided by the operator on 2026-11-17, during apply.

*Alternative considered:* the majority type. Rejected: a majority of mis-typed records would set a wrong approach with a confident-looking basis.

### 9. Measure before each first write

On the writer, before anything is published:

- `thenwhat claim approaches --dry-run`: how many claims the rule would fill, and its agreement with the 90 approaches set by hand or seed. A type that agrees poorly leaves the table.
- `thenwhat clinical categories`: how many claims have a category from trials, how many only from papers, how many none. It only reads.
- `thenwhat clinical compare`: the numbers in Decision 6.

Each is recorded in this file under "Measured".

## Risks / Trade-offs

- **The D1 store never updates a claim's approach after its first push.** `store/merge.sql` inserts a claim's own fields once and afterwards updates only its review, status, dates and audit marks; the same holds today for an edited vertical or headline. The site's export is still built from Postgres, so nothing is lost now. Before the cut-over to the store, a rule-set approach on an existing claim must be carried, or it will not be published. That belongs to `cloudflare-source-of-truth`; it is recorded here so it is not found late.
- **A database restored from the store loses who set each approach**, since the column is Postgres only → Every approach then reads as "not the rule's" and is kept. The rule stops updating them; it does not overwrite anything.
- **Deriving categories costs export time** → Measured in the export task and reported; the tree lookup is in memory.
- **The change is large**: a new source field, derivations, new site pages → Tasks are grouped so the approach rule (groups 1 and 2) and the clinical data (3 to 5) each land and pass `make check` alone, and the site (6) reads only the export.
- **A paper is about more than the claim's indication** (a results paper indexed under a comorbidity as a major topic) → Each category names its records on the claim page, so a wrong one is traceable. The dry run reports how many claims are filed by papers alone; the operator can look at those first.
- **Europe PMC's terms may not allow republishing headings** → Decision 2: then papers are not used. Coverage falls to claims with an approved trial.
- **MeSH changes every year**: labels reworded, terms moved or retired → Identifiers are the key; the year is stored and shown; a retired descriptor is kept and listed, not dropped silently.
- **Registry condition terms are derived by NLM's algorithm from free text** and are sometimes too broad or wrong → They are shown as the registry's, with the trial named. The comparison's disagreements surface the worst.
- **A wrong registry type sets a wrong approach** → The basis is shown; the operator corrects it and the rule then leaves it alone; Decision 9 measures how often first.
- **Clinical pages roughly add a few hundred pages to the build** → Static, from the export; build time is measured in the site task and reported.
- **The disagreement list keeps showing defensible cases** → Their count is recorded as an input to the switch-over rather than hidden.

## Migration Plan

1. Land groups 1 and 2 (approach). On the writer: migrate, dry run, record, run, export.
2. Land groups 3 to 5 (clinical data, mapping, comparison). On the writer: read the MeSH records, run the reports, record. Nothing public changes yet except the export's new fields.
3. Land group 6 (site). Deploy through the usual pull request and its preview.
4. Paste the disagreement rows into the fault tab. Record the comparison's numbers under "Measured". The switch-over is proposed, or not, from them.

Rollback: the site pages are removed by reverting the site commit. Clinical categories hold no state of their own. Rule-set approaches are cleared where `approach_decided_by` is `rule`.

## Measured

To be filled on the writer (Decision 9). Empty until then.

## Open Questions

- Should `BEHAVIORAL` map to `diet-or-lifestyle`? Left unmapped; the `--unset` list will show what it would add.
- Should the clinical index open at MeSH's top categories or one level down? Decided when the pages can be looked at with real counts; it changes one template.
- Should a disagreement the operator has looked at and kept be recorded, so the list shows only new ones? Deferred until the first list shows how many there are.
