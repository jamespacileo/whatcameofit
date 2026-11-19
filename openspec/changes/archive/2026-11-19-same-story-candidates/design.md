# Design

## Context

See `proposal.md` for the motivation and the audit figures.

Today a read's candidates come from four places (`LinkRead._claim_it_reports`, `backfill/link_read.py`): claims sharing a name whole (`claims_sharing_a_name`), claims the lead's title names, claims filed under a substance one of the read's names belongs to (`claims_of_a_named_substance`), and the owner of the slug a new claim would get. With no candidate no decision is asked and a claim is drafted. After `thenwhat prepare` has searched the registries, `claim_sharing_its_substance` (`prepare.py`) rejects a draft whose intervention has the substance of another claim and moves its articles with `join_articles`.

Measured on the database as it stood on 16 November 2026 (871 claims not rejected, 95 audited duplicates whose older claim is known):

| What links the pair | Pairs found, of 95 | Claims with at least one such older claim, of 871 |
| --- | --- | --- |
| A shared name word and a shared condition word | 75 | 330 (mean 2.5 candidates, 64 claims over eight) |
| A shared name word and a condition that is the other's, or narrows it | 49 | 197 |
| An approved registry trial in common | 60 | 164 |
| Either of the first and third | 91 | not measured together |

The four pairs neither finds are a description against a product name with no trial yet in common ("Stem-cell-derived insulin-making cells" and zimislecel).

Constraints: only the decision joins an article to a claim; no model decides a status; the pipeline holds no article text; one way of doing each thing, with no looser path standing in when the first finds nothing.

## Goals / Non-Goals

**Goals:**

- The same-claim decision is shown the claim a read duplicates in most cases where a person at audit would name it.
- A pair the read could not see, because the names share nothing, is caught once both have an approved trial in common.
- What is offered stays explainable: each candidate has a stated reason, logged.

**Non-Goals:**

- Changing the decision's question, its thresholds or what it is shown at the read.
- Similarity by embedding or any second model.
- Rejecting or joining by rule alone on a shared word or a shared trial.
- Cleaning up the duplicates already stored.

## Decisions

### 1. A shared telling word plus a shared condition word makes a candidate

A claim is a candidate when one of its intervention names or synonyms and one of the read's names have a word in common that is not on a checked-in list of words many treatments carry, and the two conditions have a word in common. Words are taken as `name_key` gives them, split further on hyphens and punctuation, three letters or more.

Why the looser condition test (a shared word) and not `_conditions_overlap`: the narrow test finds 49 pairs and the loose one 75, because audited pairs differ in the condition's wording as often as in the treatment's ("Kidney failure" and "End-stage kidney failure" pass the narrow test; "Recurrent Clostridium difficile infection" and "Clostridium difficile infection" pass; "Age-related vision decline" and "Age-related decline in eyesight" pass only the loose one). The narrow test is kept for the order in which candidates are offered.

Alternatives considered:

- Offer every claim for the same condition. Finds more, but 507 of 871 claims would get candidates, a mean of seven and 217 over eight. The decision would be asked about mostly unrelated treatments, and its votes would spread.
- Embedding similarity. A second model and an index to keep, for pairs the word rule already finds; and a score in place of a stated reason.
- Widen `claims_sharing_a_name` itself. It is also what orders exact matches first and feeds the overlap refusal; mixing a word match into it would change which claim a read is refused for. A separate lookup keeps each reason apart.

### 2. Word candidates are added after the others, capped at eight

The existing candidates and their limits stand. Word candidates are appended, up to eight, in this order: condition that is the read's or narrows it, then most shared telling words, then oldest. This follows the pattern already used for substance candidates ("none SHALL take the place of a claim that would be offered without them"). 64 of 871 claims have more than eight such older claims; the order keeps the likeliest inside the cut.

### 3. A second decision at prepare, over claims sharing an approved trial

In `decide_prepared_lead_claim`, after the substance twin check finds nothing and before the claim is approved, claims that share an approved `clinicaltrials.gov` match with the draft, for a condition sharing a word, are offered to `choose_same_claim` with the same two tests. A join rejects the draft by rule and calls `join_articles`, exactly as the substance twin does.

Why a decision and not a rule: 164 of 871 claims share an approved trial with an older claim, far more than are duplicates. One trial can be approved for a combination and for its parts, and for two products compared. A shared trial is a reason to ask, not an answer. The substance twin stays a rule, because one substance, form and condition is an identity.

Why only approved matches: a pending or rejected match is a candidate the rules have not accepted for either claim, and 70 pairs share one against 60 sharing an approved one; the extra ten are bought with matches nothing stands behind.

Alternative considered: list such pairs at audit and decide nothing. That leaves every pair to a person, which is the cost this change is meant to cut. The list is kept for the pairs the decision does not join.

### 4. The audit list shows the pairs left

`thenwhat audit list` adds, under a held claim, the claims sharing an approved trial that the decision did not join it to. It is computed when the list is asked for, from stored matches, so no new column and no migration. A claim drafted from a reader's lookup (`docs/adr/0009`) has no audit hold: the decision of 3 still applies to it, and the pair is simply not listed.

### 5. How each candidate was found is recorded with it

`NamedClaim` gains the reason it was offered. The decision's logged options already hold the slugs; the reasons go beside them, and the lead's detail names the reason for the claim joined. This is what lets the next audit say which rule produced a wrong join.

### 6. Turned on only after it is measured on the audited pairs

Before the new candidates are used in a read, the candidates are computed for the 95 audited pairs and for a sample of claims that are not duplicates, and the same-claim decision is asked about them without anything being joined. The change goes on when the figures are recorded in `tasks.md`: how many of the 95 the decision joins, and how many of the sample it would wrongly join. Asking the decision writes to the decision log and costs model calls, so it runs on the machine that is the writer.

## Risks / Trade-offs

- [More candidates spread the decision's votes, so an article that joins today no longer does] → Word candidates are capped and ordered; the measurement in 6 includes pairs that join today and compares.
- [A wrong join puts an article, or a whole draft's articles, on another claim] → The two tests are unchanged, the reason and both probabilities are recorded, and `thenwhat claim` tools already move an article back. The measurement reports wrong joins on the sample before anything is turned on.
- [The word list is a judgement: too short and vaccines for one disease are all candidates of each other, too long and real pairs are lost] → The list is checked in with the pairs that motivated each word, and the candidate count per read is reported by the measurement.
- [A join at prepare rejects a draft that was right, on the strength of a shared trial] → Only the decision joins, at the same thresholds as the read; a combination never shares a substance and its trial is shared with its parts, so the measurement sample includes combinations.
- [About four reads in ten ask one more decision] → Recorded cost is about $0.00006 a decision; the monthly ceiling check already stops a run.

## Migration Plan

No schema change. The candidates take effect for reads and prepares run after deploy; nothing stored is rewritten. To go back, revert the commit: leads already joined stay joined, and each records the reason it was joined by.

## Open Questions

- The exact contents of the word list beyond the words the audited pairs call for. It can grow from the measurement without changing the requirements.
