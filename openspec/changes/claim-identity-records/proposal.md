# Proposal

## Why

A claim is one intervention for one indication, but neither half of that identity is a record of its own. The indication is free text on the claim. The intervention is an entity that belongs to one claim, so a drug in five claims is five entities with five sets of synonyms. A claim's trials are found through `entity_match`, which names a trial only by its registry number as text, with no key to the stored trial in `registry_trial`.

That shape worked while every claim began from one article and an operator or a model wrote its words. It is now the reason `registry-drafted-claims` cannot reach its goal. That change groups trials into claims on two words worked out for the news search (`search_name`, the first named intervention, and `search_indication`, up to three telling words of the first condition with words such as "positive", "negative" and "carcinoma" removed). On 2026-11-18 a detailed review supported 5 of 50 such groups against a rollout bar of 45 of 50, and 12 of the 16 earlier passes failed on the population a trial enrols. Production cited 831 of 27,731 eligible phase 2 and 3 trials (3.0%). No review of the output fixes a grouping key that loses the facts it is judged on.

The registry already files every trial under coded terms: MeSH descriptors for its conditions and interventions, in `derivedSection` of the raw payload every stored trial keeps. `knowledge-cards` already reads those codes for a claim's subject terms (`claim_term`, with fit exact or broader). This change makes those codes the identity of a claim.

## What Changes

- **A shared Condition record.** One per MeSH descriptor, with its label and tree numbers, read from the vocabulary record the project already stores. Claims and trials point to it. A condition with no descriptor has no record and its claims keep free text.
- **A shared Intervention record.** One per treatment, keyed on the substance registry's identifier when it lists one, else the MeSH descriptor, else the normalised name. It holds the names, synonyms, development codes and search phrases that are on each claim's intervention entity today. **BREAKING** for `entity-resolution`: a synonym added to an intervention is a synonym for every claim of it.
- **A claim is the pair.** A claim points to one intervention and, when one is known, one condition. The store refuses a second live claim for the same pair. The indication text stays as the label a reader sees. **BREAKING** for `claims`: "No duplicate claims" is decided on the records, and on names and synonyms only for a claim with no condition record.
- **A trial's coded terms by rule.** On load, each stored trial gains its condition descriptors and the agent its experimental arm adds over its comparator arm, from the raw payload, with no request and no model. A trial whose experimental arm adds more than one agent, or that has no arms or no descriptor, gets none and is listed with the reason.
- **A claim–trial link to the stored trial.** A match of a registry trial points to the stored trial by key, as well as naming it. The population a trial enrols (for example HER2-positive, second line) is shown on the trial's row of the claim, not in the claim's identity.
- **Coverage is a query.** "Which stored trials no claim cites" is answered by a join on keys, with a reason for each uncited trial: no coded pair, a pair no claim holds, or a pair whose claim has not approved the trial.
- **An article stays optional only where `registry-drafted-claims` says.** That change already specifies a claim drafted from registry records with no source article or first reported date, and records what a claim was drafted from. This change does not restate it; it gives such a claim the keys it is identified by.
- **Existing claims are given records from what they hold.** A claim's approved exact condition term and its intervention entity's substance become its records, in a new migration. A claim with neither keeps working on free text and is listed for the operator.

Not in this change:

- Drafting claims from trials, the sampled audit and the site's wording for a claim with no report. Those stay in `registry-drafted-claims`, which is to group on this change's pair instead of the search words.
- Combinations as one intervention. A trial adding two or more agents is listed, not keyed.
- A change to status rules. Status still comes from approved events.
- Paper, person, institution and company entities. They stay per claim.

## Capabilities

### New Capabilities

- `identity-records`: the shared Condition and Intervention records, where their keys come from, how a trial's coded terms are worked out by rule, and the coverage question they answer.

### Modified Capabilities

- `claims`: claim identity and the duplicate rule are decided on the shared records.
- `entity-resolution`: an intervention's names and synonyms belong to the shared intervention record, not to one claim.
- `registry-corpus`: a stored trial carries its coded condition and added-agent terms, and a claim's match points to the stored trial.

## Impact

- **Database**: new tables `condition` and `intervention`; new columns `claim.condition_id`, `claim.intervention_id`, `entity.intervention_id`, `entity_match.registry_trial_id`; a table of each trial's coded terms. New Alembic migrations, since production holds claims. The same shape in `store/schema.sql` and a D1 migration under `store/ingest/migrations/`, so `cloudflare-source-of-truth` carries it.
- **Pipeline**: `claims/` duplicate check and `claim merge`/`entity rename`; `backfill/registry_load.py` works out a trial's coded terms on load; `resolve/` reads synonyms from the shared record; a `thenwhat coverage` report.
- **Export**: a claim carries its condition and intervention keys. `site/export.schema.json` is regenerated and its version rises. No wording changes.
- **Other changes**: `registry-drafted-claims` (decision 3 and its grouping requirement superseded: it groups on the coded pair, and its duplicate check is this change's; its artifacts are revised by a task here once the work in progress on it is merged); `cloudflare-source-of-truth` (the merge's natural keys gain condition and intervention); `knowledge-cards` (an approved exact condition term now sets the claim's condition record).
- **Documents**: `GLOSSARY.md` (Intervention, Indication, Condition), an ADR that a claim's identity is the pair of shared records.
