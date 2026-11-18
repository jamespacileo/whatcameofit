"""Deciding an article or registry draft by rule once what the
decision rests on has finished. Behavior: openspec claim-extraction, "What a decision
waits for".

The decision waits for the claim's articles to be read, its substance to be looked up,
the trial registry to be searched and its approved records fetched. It does not wait for
its papers, its trial readings or its terms: those stay due until they finish.
"""

from typing import Any

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.orm import Session

from thenwhat.claimsteps.inputs import Inputs
from thenwhat.claimsteps.reasons import NO_DRAFT_TRIAL_APPROVED, NOTHING_TO_DECIDE
from thenwhat.claimsteps.step import Answer, ClaimSources, ClaimStep
from thenwhat.db.models import Claim, LinkLead
from thenwhat.domain import DraftedFrom, ReadOutcome, ReviewState, WorkOutcome
from thenwhat.prepare import (
    decide_prepared_lead_claim,
    decide_prepared_registry_claim,
    registry_draft_matches,
)
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.work.outcome import NothingFound
from thenwhat.work.steps import NO_SOURCE


class ClaimDecide(ClaimStep):
    """Decide a prepared draft. An article draft needs a name and no duplicate.
    A registry draft needs an approved drafting match. Approved drafts wait for audit.
    Asks no source."""

    name = "claim_decide"
    source = NO_SOURCE
    reasons = (NOTHING_TO_DECIDE, NO_DRAFT_TRIAL_APPROVED)

    def condition(self) -> ColumnElement[bool]:
        return and_(
            Claim.review_state == ReviewState.PENDING,
            or_(
                Claim.drafted_from == DraftedFrom.REGISTRY,
                select(LinkLead.id)
                .where(
                    LinkLead.claim_id == Claim.id, LinkLead.read_outcome == ReadOutcome.NEW_CLAIM
                )
                .exists(),
            ),
        )

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]:
        drafting = inputs.drafting_trial_ids.get(claim_id)
        if not drafting:
            return {}
        approved = set(inputs.approved.get(claim_id, ()))
        return {
            "approved_drafting_trials": [
                identifier
                for identifier in drafting
                if f"{ClinicalTrials.name} {identifier}" in approved
            ]
        }

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        if claim.drafted_from is DraftedFrom.REGISTRY:
            matches = registry_draft_matches(session, claim)
            decided = decide_prepared_registry_claim(claim, matches, now=self.now())
            if decided is None:
                return NothingFound(NO_DRAFT_TRIAL_APPROVED)
        else:
            decided = decide_prepared_lead_claim(session, claim.slug, now=self.now())
        if decided is None:
            return NothingFound(NOTHING_TO_DECIDE)
        self.results[claim.id] = decided
        return WorkOutcome.DONE
