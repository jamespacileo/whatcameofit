# Proposal

## Why

A link lead's read drafts a new claim for a story the tracker already holds whenever the two are named in different words. Of 277 claims archived at the audits of 15 and 16 November 2026, 103 were duplicates of an existing claim, the largest single cause. For the 99 that name the claim they duplicate, that claim was the older one in 90, and the same-claim decision was never shown it in 70: for 48 no candidate was found and no decision was asked, and for 22 the decision was asked about other claims only.

Candidates are found by a shared name or a shared substance record. A procedure, a device, a transplant or a vaccine has no substance record (74 of the 99 duplicates have none), and two outlets rarely name one in the same words: "gene-edited pig kidney transplant" and "genetically modified pig kidney transplant". The rule that rejects a draft as a twin after its registries are searched needs the same substance record, so it does not catch them either. Each duplicate costs an audit decision and, until archived, would publish one story as two claims.

## What Changes

- The read offers the same-claim decision more candidates: claims whose intervention shares a word that says which treatment, for a condition that shares a word with the read's. They are added after the candidates offered today and never take the place of one. The decision and its two tests are unchanged, and only the decision joins.
- After a drafted claim's registries are searched and before the rule for drafts decides it, the claims that share an approved registry trial with it are offered to the same-claim decision. When the decision says the draft is one of them, the draft is rejected by rule and its articles join that claim, as for a twin by substance today.
- A claim that shares an approved registry trial with another claim and was not joined to it is listed with that claim by `thenwhat audit list`, so an audit sees the pair without searching for it.
- The lead's detail and the decision log say which candidates were offered and how each was found.

Not in this change: how the decision scores a candidate it is shown (29 of the 99 were shown the right claim and declined), merging the duplicates that exist (`thenwhat claim merge` does that), the entry rules for classes and several products, and registry match scoring.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lead-reading`: which claims are offered to the same-claim decision at the read, a second same-claim decision once a drafted claim's registries are searched, and what the audit list says about claims that share an approved trial. The capability is defined by `openspec/changes/social-link-backfill`, which is not archived, so `openspec/specs/` has no `lead-reading` yet and this delta adds requirements beside that change's.

## Impact

- `pipeline/src/thenwhat/claims/entry.py`: a new candidate lookup beside `claims_sharing_a_name` and `claims_of_a_named_substance`.
- `pipeline/src/thenwhat/backfill/link_read.py` (`_claim_it_reports`): the new candidates and the record of how each was found.
- `pipeline/src/thenwhat/prepare.py` (`decide_prepared_lead_claim`): the decision over claims sharing an approved trial, beside `claim_sharing_its_substance`.
- `pipeline/src/thenwhat/cli/audit.py`: the pairs listed.
- A checked-in list of words that name no treatment on their own.
- Model spend: one more same-claim decision for about four reads in ten and for about one drafted claim in five, at about $0.00006 each as recorded in `llm_usage`. No new source, no schema change expected, nothing on the site.
- `docs/url-to-claim.md` and `GLOSSARY.md` where the candidates are described.
