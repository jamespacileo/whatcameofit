# Approvals fixture

The site's first pair page with a regulator's approval, until a bundle cut by the lab after its
pull request 189 (change `regulator-approvals`) replaces `tests/bundle`.

- `staging-tirzepatide--obesity.json`: the `pair` of staging's
  `/data/pairs/tirzepatide--obesity.json`, read 2026-11-21, kept as served except that its
  trials, `nct_ids` and names are cut to two trials (NCT04184622, Phase 3; NCT06864026,
  Phase 4) and the registry's arm names, and `approach.trials` counts the two.
- `lab-approval.json`: the `PairApproval` the lab's approvals pipeline (PR 189, s83 v2) wrote
  for this pair on a copy of the full store, 2026-11-21: EMA's Mounjaro, EMEA/H/C/005620,
  exact fit, no day (EMA's table dates the first authorisation, for type 2 diabetes, not the
  weight-management use added later). Credit as `lab.sources.ema.TERMS`.
- `PairPage.schema.json`: the lab's `PairPage` schema at PR 189 (756ef4a), as
  `lab.page_files` writes it.

`tests/pair-approvals.test.mjs` makes the page the lab now writes from the two, as
`tests/lab-shape.mjs` does for earlier shapes: status `approved`, explained by the approval's
key (lab u15 v4), and the approval in `approvals` (p12 v7).
