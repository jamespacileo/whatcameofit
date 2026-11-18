# Tasks

Write steps run on the one writer only. Every count below is taken read-only first and recorded here before anything is written.

## 1. Decisions and records

- [x] 1.1 Record the operator's answer to design decision 1 (a trial's narrower population groups under the registry's descriptor); stop and revise the `claims` delta if the answer is no; verify the answer and its date are written in `design.md`
- [ ] 1.2 Write the ADR that a claim's identity is a shared intervention record and a shared condition record, naming the lines of `GLOSSARY.md`, `CLAUDE.md` and `registry-drafted-claims` it changes; verify the ADR number follows the last in `docs/adr/`
- [ ] 1.3 Revise Intervention and Indication in `GLOSSARY.md` and add Condition and Tested intervention; verify each term is used exactly in the specs of this change

## 2. A trial's coded terms

- [ ] 2.1 Add a pure function that reads a trial's condition descriptors and tested intervention from its raw payload, with the reason when there is none; verify tests on synthetic payloads for a drug added to a backbone, a single-arm trial, two agents added, no arms, two condition descriptors and no descriptor
- [ ] 2.2 Add the table of a trial's coded terms to Postgres (new Alembic migration) and D1 (`store/ingest/migrations/`, `store/schema.sql`); verify `make check-store` and a migration test against the test database
- [ ] 2.3 Work out coded terms on load in `backfill/registry_load.py`, and for every stored trial once from payloads already held, with no request; verify a test that a reload with an unchanged payload changes nothing
- [ ] 2.4 Count, read-only on production, the eligible phase 2 and 3 trials by reason (one tested intervention and a descriptor, two or more agents, no arms, no descriptor); record the table here and show the operator before section 4

## 3. Shared intervention and condition records

- [ ] 3.1 Add `condition` and `intervention` tables and nullable `claim.condition_id`, `claim.intervention_id`, `entity.intervention_id` in both stores; verify migration tests and that `make check-fast` passes with no behaviour change
- [ ] 3.2 Add `thenwhat identity backfill --dry-run` that proposes records for existing claims from approved exact condition terms and from entities and their substances, and lists claims with no condition record and pairs two claims share; verify one success and one refusal of the command, and a test that two entities with one substance give one record
- [ ] 3.3 Run the dry run read-only on production and record here the claims with both keys, with one, with none, and the shared pairs; show the operator
- [ ] 3.4 Merge each shared pair the dry run lists with `thenwhat claim merge`, then run the backfill for real; verify the dry run afterwards lists no shared pair
- [ ] 3.5 Add the partial unique index on the pair (both set, not merged) in both stores; verify a test that a second claim for the pair is refused and names the first, and that a merged claim does not block

## 4. Claims use the records

- [ ] 4.1 Decide "No duplicate claims" on the records, keeping the name and synonym rule for a claim with no condition record; verify tests of the four scenarios of the `claims` delta
- [ ] 4.2 Read an intervention's synonyms, codes and search phrases from its record in `resolve/`, and mark every claim of the record due when one is added; verify a test of the shared-synonym scenario
- [ ] 4.3 Extend `thenwhat entity rename` and `thenwhat claim merge` to intervention records; verify tests that a rename keyed on a name gains a substance key without a second record, and that merging two records moves their claims
- [ ] 4.4 Point `entity_match` to the stored trial by key on preparation and backfill existing matches; verify tests of a match to a stored trial and to a trial stored later

## 5. Coverage

- [ ] 5.1 Add `thenwhat coverage --set <name>` that counts cited trials and gives each uncited trial one reason from the fixed list, read-only; verify one success and one refusal, and a test of each reason
- [ ] 5.2 Run the coverage report read-only on production for the active phase 2 and 3 set; record the figures here beside the 3.0% of `proposal.md`

## 6. Intervention and condition pages

- [ ] 6.1 Export intervention records with their slug, names, codes and card, and each claim's condition and intervention keys; regenerate `site/export.schema.json` and the seed export; verify the schema and seed tests pass
- [ ] 6.2 Add `/intervention/[slug]` showing names, card, claims by condition and their trials once each, with the claim page's wording guardrails; verify site tests of a drug with two claims sharing a trial, a drug with no card, no page for an intervention with no published claim, and that the build's wording check covers the page
- [ ] 6.3 Add the condition's card and the list of interventions with a claim for exactly that condition to `/clinical/[descriptor]`, link the claim page's intervention and indication, list intervention pages in the sitemap and send a merged record's slug to the kept page; verify site tests of each scenario in the `site-publishing` delta
- [ ] 6.4 Build the site from the production export and record here the number of intervention pages, the build time and the output's size; verify the figures are recorded and shown to the operator

## 7. The change it unblocks

- [ ] 7.1 Revise `registry-drafted-claims` so its groups are the coded pair and its duplicate check is this change's, superseding its design decision 3 and its grouping requirement; verify `openspec validate registry-drafted-claims --strict` passes
- [ ] 7.2 Update `CLAUDE.md` working rules for the duplicate check and the coverage command, and run `make check` and `openspec validate claim-identity-records --strict`; verify all pass
