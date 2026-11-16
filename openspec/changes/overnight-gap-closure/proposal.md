# Proposal

## Why

On 2026-11-16 the tracker went from 594 to 708 published claims and stored every interventional trial the registry holds, but several gaps are half closed: the Reddit backfill is mid-run, the address-key migration is merged and not applied, the stored trials cannot say which had activity in 2025 or 2026 or which completed with results, and eight pull requests from parallel sessions are open. The operator wants these closed overnight, quickly and cheaply, without waiting on a person for anything that does not need one.

## What Changes

- The night's work is ordered so that nothing waits on anything it does not depend on, and each step says what it costs and what stops it.
- Work handed to another session or a subagent is given a model by rule: the cheaper model for token-heavy work that clear instructions make deterministic, the stronger one for design and judgement.
- A pull request from a delegated session is reviewed once and merged as soon as it is clean. Only named risks block a merge; anything else is merged and followed up.
- The stored trial record gains the registry's activity and results fields, and all trials are loaded again, so that two sets can be named by rule: trials active in phase 2 or 3 with registry activity since 2025, and trials completed since 2025 with results posted.
- The address-key migration is applied behind a backup and its rekey is surveyed overnight; the rekey itself waits for the operator's reading of the counts.
- The operator cannot be asked anything until the morning. Every session decides for itself by one rule, practical and reversible, and writes each decision down; what cannot be undone waits.
- What is left for the operator in the morning is one short list.

Nothing here changes what the site may say: no verdict wording, no status decided by a model, every drafted claim held until audited.

## Capabilities

### New Capabilities
- `delegated-work`: how work given to other sessions and subagents is assigned a model, reviewed, and merged or sent back.

### Modified Capabilities
- `registry-corpus`: the stored trial record carries the registry's activity and results fields, and two further named sets of trials exist.

## Impact

- `pipeline/src/thenwhat/backfill/registry_load.py`, `pipeline/src/thenwhat/sources/clinicaltrials.py`, `pipeline/src/thenwhat/db/models.py` and one migration: the wider trial record and the two sets.
- The working database on the Mac mini: migrations 0027 and 0028 applied, a full reload of trials, the Reddit claims audited and published.
- `site/data/published-export.json`: one or two data pull requests.
- No change to the site's pages, the extension, or any status rule.
- Spend: within the month's $100 ceiling; the night is budgeted at $10 of model spend.
