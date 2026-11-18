# Proposal

## Why

The site files each claim under one reader-friendly vertical and, rarely, an approach. Neither serves a clinician, and neither is well supported by the data:

- On 2026-11-17, 880 of 970 published claims have no approach, because nothing sets one for a claim drafted from a link lead. 555 of those have at least one trial.
- A drafted claim's vertical is chosen by a model from a flat list before any trial is known, and nothing compares it with what the registry later says.
- A clinical or medical professional thinks in a standard hierarchy of conditions, not in "Brain and nerves". The registry and the literature index already give each trial and paper its MeSH subject headings, and the pipeline stores them without using them for filing.

The operator decided on 2026-11-17 (in chat):

- the site should serve **clinicians browsing**, beside general readers;
- the clinical vocabulary for conditions is **MeSH**;
- the clinical classification is the **source of truth**, and the reader-friendly topics are to be derived from it. Topics such as longevity or weight loss do not map one to one, so one friendly topic may cover several MeSH categories, and **one claim may appear under several friendly topics**. "It would need to be tested";
- a claim with no approved trial takes its clinical categories from its **linked papers too**;
- the friendly vertical starts being derived from MeSH only **after a measured test**;
- this change includes a **full clinical browse** on the site.

## What Changes

**Clinical classification (new)**

- Every claim gets its **clinical categories**: the MeSH descriptors its approved trials list as conditions and the disease headings its approved papers are indexed under. Each category records the trials and papers that gave it. They are set by rule; no model is asked.
- The MeSH **hierarchy** for those categories is read from NLM's own records (tree numbers), so a category is known with all its broader categories. A category can sit in several places in the tree.
- A checked-in **topic mapping** says which MeSH categories each reader-friendly group and vertical covers. It is many to many. From it the pipeline derives, for any claim, the friendly topics its clinical categories fall under.
- A **measured comparison** reports, across all claims, how the derived topics compare with the vertical each claim is filed under today: agrees, disagrees, nothing to compare, and how many claims fall under more than one topic. Disagreements are listed in rows for the fault tab of the failed-address sheet. This is the test the switch-over waits for.
- The site gains a **clinical browse**: an index of the top MeSH categories, a page per category showing where it sits in the tree, its narrower categories and the published claims at or below it, and the clinical categories on each claim page with the records behind them. NLM is credited as its terms require.

**Approach by rule**

- A claim with no approach gets one by rule when its approved trials list its intervention, by an equal name, under one registry intervention type that a checked-in table maps to an approach.
- A claim's approach records who set it and on what basis. A rule never overwrites an approach set by a person, the seed or an assistant. The claim page states what the registry lists whenever that supports the claim's approach, whoever set it.
- When the registry types do not agree, or the one type has no approach in the table, the approach stays empty and the claim is listed with the reason.

### Not in this change

- **Deriving the vertical from MeSH, and showing a claim under several friendly topics.** Both are the operator's stated direction and both wait for the measured comparison. Until then every claim keeps exactly one vertical, filed as today, and friendly topic pages are unchanged. The mapping and the derivation are built here so that the numbers exist.
- **A model reading of the approach, or of a clinical category, when the rule finds none.** It would be a second, weaker way of setting the same field. An empty value is the honest state.
- **A clinical hierarchy of interventions** (drug classes). The registry lists MeSH terms for interventions as well; that is its own change.
- **ICD-11 or SNOMED CT.** Each needs its terms checked first. MeSH identifiers are kept, so a later mapping is possible.
- Clinical categories in the open data files. The export carries them; the per-claim open data files are left as they are until a data user asks.

## Capabilities

### New Capabilities

- `clinical-classification`: a claim's clinical categories and where they came from, the MeSH hierarchy they sit in, the mapping from clinical categories to reader-friendly topics, and the measured comparison of derived topics with filed verticals.

### Modified Capabilities

- `health-areas`: adds the approach set by rule and its record of who set it and why. The suggested group for a claim now comes from its clinical categories and the topic mapping, not from a separate table of MeSH heading names.
- `site-publishing`: adds the clinical browse pages, the clinical categories on the claim page, the NLM credit, and the basis of a rule-set approach.

## Impact

- **Pipeline**: a new `clinical/` package (categories, tree, topic mapping, comparison); `claims/mesh_areas.py` (its label table is replaced by the mapping); `claims/` for the approach rule; `terms/kinds.py` (`registry_types` reused); `sources/mesh.py` (one more read: a descriptor's tree numbers); `prepare.py`, the daily trial refresh, `cli/`, `export/build.py`; `db/models.py` with one new migration (two columns on the claim). Clinical categories are derived from stored records and add no table.
- **Sources**: no new source. NLM's MeSH service is asked for one record per distinct category and broader category, within the limit in `docs/sources.md`. Republishing a paper's subject headings is a field beyond what `docs/sources.md` now allows for Europe PMC records; the terms are read again and the note updated before any paper heading is published.
- **Truth store (D1)**: no schema change. Categories and the approach basis are derived when the export is built, from records both stores hold.
- **Export**: per claim, its clinical categories with sources and its approach basis; once per export, the part of the MeSH tree the claims use, with the MeSH year. `site/export.schema.json` and `site/data/seed-export.json` are regenerated.
- **Site**: new pages under `/clinical`, a section on the claim page, links from `/for/clinicians` and the topics page, sitemap entries, the NLM credit.
- **Operations**: the migration and the first runs are write steps, so they run on the writer (the Mac mini) only, each after a dry run whose numbers are recorded in `design.md`.
- **No model cost.** Every input is a stored registry or index record, or NLM's own record of a term.
