# Design

## Context

See `proposal.md` for the motivation. What shapes the approach:

- `Claim.approach` is a nullable text column with no record of who set it (`db/models.py`). It is set only through `claim add`, `claim edit`, CSV import and the seed. A claim drafted from a link lead (`backfill/link_read.py`) never gets one.
- `terms/kinds.py` already has `registry_types(trial_payloads, names)`: for a claim's approved trials it counts, per registry intervention type, the trials that list an intervention whose name equals one of the claim's names. It is pure and already ignores comparators. The knowledge-cards step uses it as a reason for a model decision; nothing uses it for the approach.
- `claims/mesh_areas.py` already has `approved_trial_payloads` and `suggest_groups`, and prints one advisory line. Nothing compares the suggestion with the filed vertical or reports across claims.
- A drafted claim's vertical is chosen in `link_read.py` before `thenwhat prepare` has searched any registry, so the check cannot run at the read. The first moment trials exist is after `prepare` approves matches.
- The writer is the Mac mini. The MacBook database is frozen, so the migration and any run that changes claims happen there.
- The fault tab lives in a Google Sheet the pipeline has no client for. The pipeline's part ends at producing rows.

## Goals / Non-Goals

**Goals:**

- One deterministic way to set an approach, with its basis stored and shown.
- A vertical check that costs nothing to run and makes disagreement visible where the operator already looks.
- No new source, no model call, no stored article text.

**Non-Goals:**

- Raising approach coverage beyond what the registry states plainly. Claims the rule cannot answer stay empty.
- Writing to the Google Sheet from the pipeline.
- Storing the vertical check's answer. It is recomputed from stored records each time.

## Decisions

### 1. The type table maps only types that name one approach

ClinicalTrials.gov's intervention types are: `DRUG`, `DEVICE`, `BIOLOGICAL`, `PROCEDURE`, `RADIATION`, `BEHAVIORAL`, `GENETIC`, `DIETARY_SUPPLEMENT`, `COMBINATION_PRODUCT`, `DIAGNOSTIC_TEST`, `OTHER`. The table:

| Registry type | Approach |
| --- | --- |
| `DRUG` | `drug` |
| `DEVICE` | `device` |
| `PROCEDURE` | `surgery-or-procedure` |
| `GENETIC` | `gene-therapy` |
| `DIETARY_SUPPLEMENT` | `diet-or-lifestyle` |

The rest map to nothing. `BIOLOGICAL` covers vaccines, cell therapies and antibodies, which are three different approaches here. `BEHAVIORAL` covers talking therapies as well as habits. `RADIATION`, `COMBINATION_PRODUCT`, `DIAGNOSTIC_TEST` and `OTHER` have no approach of their own.

*Alternative considered:* splitting `BIOLOGICAL` with the kinds list in `terms/kinds.py` (vaccine, cell therapy, antibody). Rejected for this change: a kind is chosen by a model decision, so the approach would no longer be set by the registry alone. It can be proposed later as its own rule with its own basis code.

### 2. The types must be unanimous

The rule answers only when `registry_types` returns exactly one type and the table maps it. Two drug trials and one biological trial give no approach. This trades coverage for precision: sponsors register gene and cell therapies under `DRUG`, `BIOLOGICAL` or `GENETIC` inconsistently, and a mixed record is the sign of it.

*Alternative considered:* the majority type. Rejected: a majority of mis-typed records would set a wrong approach with a confident-looking basis.

### 3. Two columns on the claim, not a table

`approach_decided_by` (the existing `Decider` values, nullable) and `approach_basis` (JSON, nullable: `{"code": "registry_lists_type", "type": "DRUG", "trials": 3}`, the reason shape `registry_types` already returns). One new migration. Existing rows keep `approach_decided_by` empty, which the rule reads as "not mine".

`claim add`, `claim edit` and CSV import set `human` (or `assistant` with `--as-assistant`); the seed sets `seed`. Clearing an approach by hand clears both columns, after which the rule may fill it again. That is intended: an operator who wants "no approach" to hold against the registry has no way to say so in this change (see Risks).

*Alternative considered:* recording the approach as a decision in the decisions ledger. Rejected: that ledger holds model decisions with probabilities; this is a rule with a count.

### 4. One pure function, called from two places

`claims/approach_rule.py` holds the table and `approach_from_registry(types) -> (approach | None, basis | None, reason)`. It takes the output of `registry_types` and nothing else: no session, no clock. A session-taking function applies it to one claim and enforces "never overwrite".

It is called:

- in `thenwhat prepare`, for each claim it handles, after trial matches are decided;
- by `thenwhat claim approaches`, which applies it to every unarchived claim, with `--dry-run` to report without writing and `--unset` to list the claims left empty with their reasons.

The daily trial refresh approves new matches too. It calls the same session function for each claim it changes, so a rule-set approach follows the trials without a separate run.

### 5. The vertical check is a pure comparison, computed on demand

`claims/mesh_areas.py` gains `check_vertical(vertical, suggestions) -> VerticalCheck` (agrees, disagrees, no suggestion with its cause). The comparison is by group: `VERTICAL_GROUPS[vertical]` against the suggested group slugs, so `dementia` agrees with `brain-and-nerves`. Any one matching group is agreement, because a claim about diabetic eye disease is rightly filed under either.

`thenwhat claim vertical-check` lists the disagreeing claims and the three counts; `--tsv` prints the fault-tab rows. `prepare` adds one summary line for the claims it handled.

Nothing is stored, so there is no state to go stale when the MeSH table or a vertical changes.

*Alternative considered:* raising or lowering `vertical_accept_above` from the check. Not possible: the vertical is chosen before trials exist.

### 6. What happens to a disagreement

A disagreement is one of three things, and each has one response:

- **The model filed it wrongly.** The operator runs `claim edit --vertical`. The row goes in the fault tab.
- **The MeSH table is wrong or coarse.** The table is corrected and a case for the heading is added to the table's pure test.
- **Both are defensible** (a cancer drug tested for a skin condition, a claim under `ageing`, which no MeSH heading maps to). Nothing changes. The claim keeps appearing in the list; see Open Questions.

### 7. Measure before the first write

Before `thenwhat claim approaches` writes anything, `--dry-run` is run on the writer and two numbers are recorded in this file: how many of the 880 claims the rule would fill, and, over the 90 claims whose approach was set by hand or seed, how often the rule's answer equals the stored one. The second number is the only measure of the table's accuracy available without new labelling. If agreement is poor for one type, that row leaves the table before the first write.

## Risks / Trade-offs

- **A wrong registry type sets a wrong approach** (a gene therapy registered as `DRUG` in every trial) → The basis is shown on the page, so the reader sees it is the registry's word. The operator corrects it with `claim edit`, after which the rule leaves it alone. Decision 7 measures how often before anything is published.
- **Coverage will be well under 555.** Unanimity, the equal-name requirement and the unmapped types each remove claims → Accepted. `--unset` shows what was left and why, which is the input for any later rule.
- **Up to 555 published pages change in one run** → `--dry-run` first; the run happens on the writer, followed by one export. Roll back by clearing every approach whose `approach_decided_by` is `rule`.
- **An operator cannot pin "no approach".** Clearing one lets the rule refill it → Accepted for now; no case of it exists. If one appears, the fix is a third state, not a workaround.
- **The disagreement list keeps showing defensible cases**, which trains the operator to skim it → See Open Questions.
- **`registry_types` now serves two callers** (`terms` and `claims`) → It stays where it is and stays pure; the new rule imports it. Moving it is not part of this change.

## Migration Plan

1. Land the code with the migration. `make check` passes on any machine: tests use the test database and recorded payloads.
2. On the writer: run the migration, then `thenwhat claim approaches --dry-run`. Record the two numbers from Decision 7 here.
3. If the numbers hold, run `thenwhat claim approaches`, then `thenwhat claim vertical-check --tsv` and paste the rows into the fault tab.
4. Regenerate the export and deploy through the usual pull request.

Rollback: set `approach`, `approach_decided_by` and `approach_basis` to empty where `approach_decided_by` is `rule`, and export again. The columns can stay.

## Open Questions

- Should a disagreement the operator has looked at and kept be recorded, so that the list shows only new ones? It needs a stored "kept" mark per claim. Deferred until the first list shows how many defensible cases there are.
- Should `BEHAVIORAL` map to `diet-or-lifestyle`? Left unmapped. The `--unset` list will show how many claims it would add and what they are.
