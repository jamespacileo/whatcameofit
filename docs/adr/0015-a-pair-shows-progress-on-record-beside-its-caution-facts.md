# 15. A pair shows its progress on record, always beside its caution facts

Date: 2026-11-21. Status: accepted. Change: `openspec/changes/pairs-site` (task 3.1g). Sits beside the guardrail "No editorial verdicts" and `0010`.

## Context

Readers ask whether a treatment looks promising. The site may not say: no model decides a status, figures are copied as text and never compared, and nothing says whether a result is good news (the lab's `docs/decisions.md`, 2026-11-18). Every established system that grades "does it work" (GRADE, Examine, Natural Medicines, USPSTF) relies on reviewers judging the direction and size of effects across trials. The research is in the Claude Doc "Evidence-strength ratings for trials: what to reuse" (https://claude.ai/artifact/8heuMmUYYK8dYQXtXsw8ZV), with four real pairs worked through at https://claude.ai/artifact/CKCReatqtUKdNfqUCfZ3j5.

Three options were put to the operator on 2026-11-21: sourced facts only; a level by progress only; a level with a step for a randomised trial with a comparison group. The operator chose the second, "always shown with its caution facts". The third cannot be computed: the bundle carries no arm roles.

## Decision

A pair page has a section "What the record shows". It gives one level, named "Progress on record", as the furthest of five steps for which a record exists:

1. **Registered**: a trial is registered.
2. **Trial started**: the registry records a trial's start (not an expected one).
3. **Trial finished**: the registry records a trial's completion, or gives its state as completed.
4. **Results on record**: a trial's results are posted on the registry.
5. **Regulator has decided**: a regulator's decision is on record. A refusal counts as an approval does.

The rule is one pure function over a pair's page file (`progressOf`, `site/src/lib/progress.ts`). It reads dates, events and states only. It cannot rise because a figure looked favourable, and nothing is read from free text.

The level is never drawn alone. Beside it, from the same records, are its caution facts: a trial the registry gives as stopped early, suspended or withdrawn, with the registry's stated reason quoted as written; a trial with no results on the registry a year after its primary completion, dated and worded "Results may be available elsewhere"; a retraction. Where the records hold none, the page says that in a sentence. A caution fact never changes the step: lowering it for a trial "stopped for negative reasons", as Open Targets does, needs a model to read the reason.

It is named for what it counts. Never "strength", "promise", "certainty" or "grade". The steps are drawn in the site's one blue, filled or empty, so `0010` holds: no colour is given by what a result says.

It sits beside the pair's status and replaces nothing. The status is a place on the path by phase; this is how much of a trial's life is on record.

## Known defects

Kept here and added to as they are found. Each is a way the level can mislead today.

1. **A trial's role on the pair is not modelled.** A long-term follow-up or surveillance study counts as a trial of the pair (NCT04208529, NCT05626855 in the release review of 2026-11-21). It can put a pair on "Trial started" or further.
2. **A small trial that ended early and posted results reaches step 4.** On staging, PF-06649751 for Parkinson disease: 5 people, terminated, results posted. This is why the caution facts are always drawn.
3. **No refusal in the bundle.** The one regulator code is `approved`. A refused treatment stays on step 4 or below until the lab carries refusals. Staging on 2026-11-21 has no approved pair among 3,825, so step 5 has no real example and no test.
4. **Results outside ClinicalTrials.gov do not count.** A results paper, or results on another registry, does not reach step 4. The page file does not say which linked paper reports results.
5. **The results-a-year-on fact is as old as the lab's last reading.** It carries its day. It is not drawn for a trial whose posted results the page itself carries.
6. **The test bundle holds no trial that ended early, none a year past completion without results, and no retraction.** The caution lines are drawn by code no test exercises on real records until such pairs are added to `site/tests/bundle`.
7. **Readers may take a fuller level for a better treatment.** The name, the fixed note under it and the caution facts reduce this and do not remove it.

## Consequences

- Nothing here is read by a model, so there is no accuracy to sample. Anything later that reads meaning (a stop reason's category, whether an arm is a comparison group, a trial's role on a pair, what a paper found) needs a labelled sample with measured accuracy and its own entries in this list before it is shown (the operator, 2026-11-21).
- The rule lives on the site, over the lab's page file. If the lab later derives it, the site keeps only the wording.
