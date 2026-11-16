# Proposal

Status: built in this change's pull request. Not applied to the working database: the commands for the cases below are listed in the pull request for the operator's assistant to run after review.

## Why

The audit of 2026-11-16 found two faults in the 708 published claims that no command can correct.

1. **Duplicate published claims for one treatment and indication.** `ervebo-prevention-of-ebola-virus-disease` and the claim whose intervention is `VSV-EBOV`; exa-cel under two descriptive names, with a better-named third claim archived; two Alzheimer's nanoparticle claims. Each pair splits one treatment's articles and evidence over two pages. The only tool today is `archive`, which loses the duplicate's articles and leaves its address answering 410.
2. **29 claims archived because the intervention is a description, a dose, or carries brackets** ("targeted thermal therapy (TTT)", "100 mg daily enteric-coated aspirin", "treatment for Guillain-Barre syndrome"). They cannot be put back without a correct name. `claim edit --intervention` changes the name but checks no entry rule, keeps no synonym, cannot change a published slug, and leaves the registries searched under the old name.

## What Changes

- **`thenwhat claim merge <from-slug> <into-slug> --reason …`** folds a duplicate into the claim that is kept. What articles reported moves: source articles, promises, reported statements, link-lead pointers, the intervention's names (as synonyms), and the papers, organisations and people an article named, de-duplicated. What registries were found to say does not move: the intervention's matches and every evidence event stay with the merged claim, and the kept claim's registry search is marked due so `prepare` finds them again for the kept claim (design.md). The merged claim is archived with the reason and a pointer, never deleted. Refused across different indications, into an archived claim, or for a claim awaiting audit, unless the operator says so explicitly. Who decided is recorded (`--as-assistant`).
- **`thenwhat entity rename <claim-slug> <old-name> <new-name>`** corrects an intervention's name. The old name stays as a synonym unless `--old-is-description`. A new name that breaks an entry rule (brackets, dose, maker, description) is refused with the rule named; one that is another claim's intervention for the same indication is refused with the `claim merge` command to run. `--reslug` makes the slug again by rule.
- **Moved addresses.** The export gains `moved`: each address that was a claim's page and now leads to another's, because the claim was merged or given a new slug. The Worker answers such an address with a permanent redirect, where it answered 410 or 404. A former slug stays taken.
- **A registry search that is due.** Both commands mark the claim's registry search as due. `thenwhat prepare --due` prepares every such claim, and a registry search that succeeds clears the mark.
- **Modified:** a published claim's slug may now change, but only through `entity rename --reslug`, and its old address keeps leading to the page.

## Capabilities

### Modified Capabilities

- `claims`: merging duplicates, renaming an intervention, the registry search due after either, and when a published slug may change.
- `site-publishing`: moved addresses lead to the claim.

## Impact

- Migration `0029`: `claim.merged_into_id`, `claim.registry_search_due_at`, table `claim_change`.
- `pipeline/src/thenwhat/claims/corrections.py` (new), `claims/entry.py` (a merged claim never answers a duplicate check; a former slug is taken), `cli/entry.py`, `cli/resolve.py`, `cli/prepare.py`, `prepare.py`, `export/build.py`.
- `site/export.schema.json` regenerated; `site/scripts/redirects.mjs`, `site/worker/gone.mjs`, `site/worker/index.mjs` carry moved addresses to the Worker.
- Not in this change: the browser extension still says a followed claim that was merged or re-slugged "is no longer published"; `lookup.json` does not carry moved addresses. Comparing a merged claim's articles with the kept claim's by the address key, not the address as written, waits for task 5.1 of `idempotent-runs-and-one-address`.
