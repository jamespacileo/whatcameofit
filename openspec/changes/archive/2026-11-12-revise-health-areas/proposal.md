# Proposal

## Why

The groups and verticals in `pipeline/src/thenwhat/claims/verticals.py` grew claim by claim, and they no longer match the claims filed under them:

- The two "pain" claims (back disc, knee osteoarthritis) are filed under "Brain and mind".
- The two "transplants" claims (kidney failure, infertility after chemotherapy) are filed under the immune system.
- Liver disease (MASH) and sleep apnoea sit in "Diabetes and metabolism".
- Lungs, kidneys, bones and joints, digestion, pregnancy and blood have no home at all.

The tree has no principle a reviewer can apply to a new claim. The site is not deployed yet, so slugs can still change without breaking public addresses.

## What Changes

- **A rule for the tree.** A group is a body system or disease area that a reader would recognise. Each group is anchored in pipeline configuration to one or more UKCRC HRCS health categories, which makes the tree complete: every condition has a group. The HRCS codes stay internal. Their licence (CC BY-NC-ND) rules out republishing an adapted copy, so neither the export nor the site carries them. Labels stay our own plain wording.
- **General and specific verticals.** Each group has one general vertical with the group's own slug. A specific vertical splits out of it once it would hold about five published claims, for example dementia within "Brain and nerves".
- **A revised set of groups and verticals**, moving every seed claim:
  - **BREAKING** for slugs: `pain`, `transplants`, `hair-loss`, `allergies` and `sight-and-hearing` are retired, and `dental-regeneration` is split into `teeth` and `gum-disease`.
  - Groups are added for lungs, kidneys and bladder, bones, joints and muscles, gut and liver, and pregnancy and fertility.
- **An approach facet.** A claim may carry one approach code, such as drug, gene therapy, cell therapy, tissue regeneration, transplant, device or surgery. This stops intervention-shaped topics ("transplants", "regeneration") from bending the disease tree. The export carries the code, and the claim page shows its label.
- **Suggested health area.** After a claim's trials are matched, the pipeline suggests a group from the trials' MeSH ancestor terms, using a fixed lookup table. The suggestion is advisory and is shown with the MeSH term it came from. The operator always chooses the vertical.
- **Renamed or retired slugs after launch.** Once the site is public, a renamed or retired vertical slug keeps a redirect to its successor.

## Capabilities

### New Capabilities

- `health-areas`: the group and vertical tree, its HRCS anchoring, the general and specific vertical rule, the approach facet, the MeSH-based suggestion, and slug retirement.

### Modified Capabilities

- `claims`: the Vertical requirement points at `health-areas`, and a claim may carry an approach.
- `site-publishing`: the topic index covers a vertical's claims, a claim page shows its approach, and retired topic addresses redirect after launch.

## Impact

- **Pipeline:**
  - `claims/verticals.py` gains the new tree and HRCS anchors.
  - A new approach module.
  - A MeSH ancestor table.
  - A new `approach` column on the claim, added by a new migration.
  - Claim entry, CSV import, seed load and the export model change.
  - The ClinicalTrials.gov search fields gain the condition MeSH terms.
- **Data:**
  - `data/seed/claims.csv`, `claims-recent.csv` and `tooth-regrowth-usag1.json` are re-filed.
  - `site/export.schema.json` and `site/data/seed-export.json` are regenerated.
- **Site:**
  - The topic chip's special case for `dental-regeneration`.
  - An approach label on the claim page.
  - The topics page picks up new groups unchanged.
  - Redirects for retired slugs (only needed after launch).
- **Not in scope:**
  - ISRCTN condition categories.
  - Index pages for each approach.
  - Splitting cancer by tumour type.
  - A "rare and genetic conditions" facet.
