# Design

## Context

- `claims/verticals.py` holds three dictionaries:
  - `VERTICALS`: 14 entries.
  - `GROUPS`: 8 entries.
  - `VERTICAL_GROUPS`: the mapping between them, which is optional.
- `claims/entry.py` validates a claim's vertical against `VERTICALS`, and `export/build.py` exports each vertical with its group.
- The site builds `/topic/{vertical}` for every exported vertical. `topics.astro` sorts topics under their groups, and puts any topic without a group under "Other topics".
- The vertical is stored as free text in `claim.vertical`.
- Seed data:
  - `data/seed/claims.csv` holds 25 claims, all `dental-regeneration`.
  - `data/seed/claims-recent.csv` holds 58 claims in 78 rows. A repeated slug with blank fields is another source article for a claim above it, not a claim without a vertical.
- The site has not been deployed: `site.config.mjs` still defaults to localhost, and the launch checklist is open. Slugs can change now with no redirects.
- For the reasons behind the change, see proposal.md.

## Goals / Non-Goals

**Goals:**
- One rule a reviewer can apply to any new claim: pick the body system, then a specific vertical if one exists, else the group's general vertical.
- A configuration check that proves the tree complete against HRCS, run in `make check`.
- Every seed claim refiled, with each judgement call written down.

**Non-Goals:**
- Showing HRCS codes anywhere public.
- Assigning a vertical automatically.
- Index pages for each approach.
- Splitting cancer by tumour type.
- ISRCTN condition categories.

## Decisions

### 1. The tree

Group titles are our own wording. The HRCS anchors stay in configuration and are never exported.

| Group slug | Title | HRCS anchors | Specific verticals |
|---|---|---|---|
| `ageing` | Ageing | Generic health relevance | none |
| `bones-joints-and-muscles` | Bones, joints and muscles | Musculoskeletal; Injuries and accidents | none |
| `brain-and-nerves` | Brain and nerves | Neurological; Stroke | `dementia` |
| `cancer` | Cancer | Cancer and neoplasms | none |
| `diabetes-and-hormones` | Diabetes, weight and hormones | Metabolic and endocrine | none |
| `eyes-and-ears` | Eyes and ears | Eye; Ear | none |
| `gut-and-liver` | Gut and liver | Oral and gastrointestinal | none |
| `heart-and-circulation` | Heart, blood and circulation | Cardiovascular; Blood | none |
| `immune-system-and-allergies` | Immune system and allergies | Inflammatory and immune system | none |
| `infections` | Infections | Infection | none |
| `kidneys-and-bladder` | Kidneys and bladder | Renal and urogenital | none |
| `lungs-and-breathing` | Lungs and breathing | Respiratory | none |
| `mental-health` | Mental health | Mental health | none |
| `mouth-and-teeth` | Mouth and teeth | Oral and gastrointestinal | `gum-disease` |
| `pregnancy-and-fertility` | Pregnancy and fertility | Reproductive health and childbirth | none |
| `skin-and-hair` | Skin and hair | Skin | none |

Every group's general vertical shares its slug, so the verticals are the 16 group slugs plus `dementia` and `gum-disease`.

- **Categories exempt from the coverage check:** "Generic health relevance", "Disputed aetiology and other" and "Congenital disorders". A congenital condition is filed by the body system it affects.
- **Ageing** is anchored to "Generic health relevance" by choice, not by coverage. Its title drops "longevity", which leans towards a promise.
- **Two groups share "Oral and gastrointestinal".** Readers think of mouth and gut separately, and HRCS joins them only for funding analysis.
- **Stroke sits under Brain and nerves**, because readers place it there. HRCS keeps it apart from Cardiovascular for the same reason.

*Alternatives considered:*
- Adopting HRCS labels outright: rejected. The licence is NC-ND, and labels such as "Renal and urogenital" are not plain.
- MeSH branches as groups: rejected. The labels are clinical ("Stomatognathic Diseases").
- Keeping the bespoke tree as it is: rejected. It has no completeness check.

### 2. General and specific verticals

The general vertical takes the group's slug, so a claim always has somewhere to go, and the site needs no separate group pages. A specific vertical splits out when it would hold about five claims. The operator applies that threshold when proposing a new vertical; no code enforces it.

### 3. Refiling the seed claims

| Old vertical | New vertical |
|---|---|
| `ageing` | `ageing` |
| `allergies` | `immune-system-and-allergies` |
| `brain-and-nerves` | `brain-and-nerves` |
| `cancer` | `cancer`, including pre-leukaemia blood disorders (CCUS and low-risk MDS), which HRCS files as neoplasms |
| `dementia` | `dementia` |
| `dental-regeneration` | `gum-disease` for periodontal indications (periodontitis, diabetes-associated periodontitis, periodontal bone and gum loss, a periodontal bone defect, the missing periodontal ligament around implants); `mouth-and-teeth` for the rest |
| `diabetes-and-metabolism` | `diabetes-and-hormones`, except MASH, which goes to `gut-and-liver`, and obstructive sleep apnoea, which goes to `lungs-and-breathing` |
| `hair-loss` | `skin-and-hair` |
| `heart-and-circulation` | `heart-and-circulation`, including primary aldosteronism (judgement call: readers know it as a cause of high blood pressure) |
| `infections` | `infections`, including chronic hepatitis B |
| `mental-health` | `mental-health` |
| `pain` | `bones-joints-and-muscles` (low back disc, knee osteoarthritis) |
| `sight-and-hearing` | `eyes-and-ears` |
| `transplants` | `kidneys-and-bladder` (end-stage kidney failure) and `pregnancy-and-fertility` (infertility after childhood chemotherapy), both with the approach `transplant` |

### 4. Approach

The approach is a closed set of codes in pipeline configuration:

`drug`, `vaccine`, `gene-therapy`, `cell-therapy`, `tissue-regeneration`, `transplant`, `device`, `surgery-or-procedure`, `diet-or-lifestyle`

- **Storage:** a nullable `claim.approach` column, added by migration `0006`.
- **Entry:** `claim add`, `claim edit` and `import-csv` accept it, through an optional `approach` CSV column.
- **Export:** carries the code.
- **Site:** the site owns the label wording, and the build fails on a code it has no label for, as it already does for statuses.
- **Biologics** count as `drug`. This includes phage therapy and antibody drugs. A reader does not separate them, and the registry's intervention type stays in the stored payload for anyone who wants it.
- **Seed claims** get their approach in the CSV files, decided by the operator and recorded as seed data.

*Alternatives considered:*
- The ClinicalTrials.gov intervention types (Drug, Biological, Genetic, and so on): rejected. They describe trials, not news claims, and a preclinical claim has no trial.
- Several approaches per claim: rejected for now. One code keeps the chip unambiguous.

### 5. Suggesting a group from MeSH

- **Input:** the stored payload of each claim's approved trial matches. A full study record from `fetch_trial` carries `derivedSection.conditionBrowseModule`, with `meshes` and `ancestors`. The search fields do not, and they need not change.
- **Lookup:** a pure function maps MeSH terms to group slugs through a fixed table, keyed by the MeSH tree's top disease headings. Examples:
  - Neoplasms → `cancer`
  - Nervous System Diseases → `brain-and-nerves`
  - Mental Disorders → `mental-health`
  - Stomatognathic Diseases → `mouth-and-teeth`
  - Digestive System Diseases → `gut-and-liver`
  - Skin and Connective Tissue Diseases → `skin-and-hair`
- **Ignored terms:** broad headings such as "Pathologic Processes" and "Signs and Symptoms" are ignored, which is why ageing is never suggested.
- **Where it is shown:** in `thenwhat prepare` output and in the review queue's claim line. It is advisory only and never written to the claim.
- **Why a table, not a model:** a model is not needed, and the table is deterministic, testable from recorded fixtures, and easy to explain. The repo has one fixture with the module (an autism trial, giving Mental Disorders), and others can be recorded.
- **Why no ISRCTN:** there is no ISRCTN client yet.

### 6. Redirects after launch

- **Retired slugs:** `RETIRED_VERTICALS` in pipeline configuration maps an old slug to its successor, and the export carries the map.
- **Redirect file:** the site build writes a Cloudflare `_redirects` file with a 301 for each entry.
- **Launch record:** `make deploy` records the set of topic slugs it published in `site/data/published-topics.json`. The build fails when a slug in that file is neither current nor retired.
- **Before launch:** the file does not exist, so this change's renames need no redirects, and `RETIRED_VERTICALS` starts empty.

## Risks / Trade-offs

- **Migrating an existing database.** A local database may hold claims under old slugs. Migration `0006` maps every one-to-one rename. For claims under `dental-regeneration`, `diabetes-and-metabolism` and `transplants`, it uses the per-indication rules above. It aborts and lists any claim it cannot place, so the operator can fix it with `claim edit --vertical` and rerun. Checked 2026-11-12: the operator's database holds 84 claims, all of them in `data/seed/`, so the rules above place every one.
- **HRCS licence.** Writing HRCS category names into private configuration is internal use, and nothing derived from them is published. The conditions of use are checked once before the anchors are committed.
- **Too many thin groups.** Several groups start with one claim. The topics page lists only groups with published claims, so readers never see empty headings.
- **The MeSH table is too coarse.** A trial for diabetic periodontitis maps to both `mouth-and-teeth` and `diabetes-and-hormones`. The spec shows both, and the operator chooses.
- **Conflict with in-flight work.** `backfill-dental-regeneration` adds claims under the old slug. Whichever change lands second refiles them, and the migration rules cover them.
