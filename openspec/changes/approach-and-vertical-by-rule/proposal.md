# Proposal

## Why

The site can be browsed by health area and by approach, but the published data does not support either well. On 2026-11-17, 880 of 970 published claims have no approach, because nothing sets one for a claim drafted from a link lead. A drafted claim's vertical is chosen by a model from a flat list before any trial is known, and nothing compares that choice with what the registry later says about the claim's trials. Both gaps can be closed from registry records the pipeline already stores: 555 of the 880 claims with no approach have at least one trial.

## What Changes

- A claim with no approach gets one **by rule** when its approved trials list its intervention, by an equal name, under one registry intervention type that maps to a configured approach. The mapping is a checked-in table. No model is asked.
- A claim's approach records **who set it and on what basis**. A rule only fills an empty approach or replaces one a rule set; an approach set by a person, the seed or an assistant is never overwritten.
- When the registry types do not agree, or the one type has no approach in the table, the approach stays **empty** and the claim is listed with the reason. There is no second way to fill it (see "Not in this change").
- The export carries the basis of a rule-set approach, and the claim page says where the approach came from.
- A **vertical check** compares the group a claim is filed under with the groups its approved trials' MeSH terms point to. It reports agreement, disagreement or no suggestion per claim. It never changes a vertical and never holds a claim back.
- `thenwhat prepare` reports how many of the claims it handled disagree, and a command lists every disagreeing claim with the MeSH terms, in rows that can be pasted into the fault tab of the failed-address sheet.

### Not in this change

- **A model reading of the approach when the rule finds none.** This was in the first sketch as a lower-band reading. It is left out: it would be a second, weaker way of setting the same field, used when the first does not answer. An empty approach is the honest state, and the site already shows nothing for it.
- Changing a vertical by rule. "Only an operator changes a vertical" stands.
- Showing a confidence for the vertical on the site.
- A condition level below the vertical, a drug class facet, and topic discovery. Each is its own change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `health-areas`: adds the approach set by rule from registry intervention types, the record of who set an approach and why, and the vertical check against the MeSH suggestion.
- `site-publishing`: the claim page states the basis of an approach that a rule set.

## Impact

- **Pipeline**: `claims/` (the type table and the rule, beside `claims/verticals.py` and `claims/mesh_areas.py`), `terms/kinds.py` (its `registry_types` reader is reused, not copied), `prepare.py`, `cli/entry.py`, `db/models.py` and one new migration (two columns on the claim), `export/build.py`.
- **Export**: one new field per claim. `site/export.schema.json` and `site/data/seed-export.json` are regenerated.
- **Site**: `site/src/lib/approach.ts`, `site/src/pages/[slug].astro`, the export type in `site/src/lib/export.ts`.
- **Operations**: the migration and the first run over existing claims are write steps, so they run on the writer (the Mac mini) only. The first run changes the approach of up to 555 published claims at once; the design sets a measured check before it.
- **No new source, no model cost.** Every input is a stored ClinicalTrials.gov record.
