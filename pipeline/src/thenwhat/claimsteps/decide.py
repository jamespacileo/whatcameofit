"""Deciding a claim that a link lead's read drafted, by the rule for drafts, once what the
decision rests on has finished. Behavior: openspec claim-extraction, "What a decision
waits for".

The decision waits for the claim's articles to be read, its substance to be looked up,
the trial registry to be searched and its approved records fetched. It does not wait for
its papers, its trial readings or its terms: those stay due until they finish.
"""

from sqlalchemy import ColumnElement, and_, select
from sqlalchemy.orm import Session

from thenwhat.claimsteps.reasons import NOTHING_TO_DECIDE
from thenwhat.claimsteps.step import Answer, ClaimSources, ClaimStep
from thenwhat.db.models import Claim, LinkLead
from thenwhat.domain import ReadOutcome, ReviewState, WorkOutcome
from thenwhat.prepare import decide_prepared_lead_claim
from thenwhat.work.outcome import NothingFound
from thenwhat.work.steps import NO_SOURCE


class ClaimDecide(ClaimStep):
    """Decide a read's draft by the rule for drafts: approved, and held off the site until
    audited, when its intervention is a name and no other claim stands for its substance
    and condition; rejected otherwise. Asks no source."""

    name = "claim_decide"
    source = NO_SOURCE
    reasons = (NOTHING_TO_DECIDE,)

    def condition(self) -> ColumnElement[bool]:
        return and_(
            Claim.review_state == ReviewState.PENDING,
            select(LinkLead.id)
            .where(LinkLead.claim_id == Claim.id, LinkLead.read_outcome == ReadOutcome.NEW_CLAIM)
            .exists(),
        )

    def work(self, session: Session, claim: Claim, sources: ClaimSources) -> Answer:
        decided = decide_prepared_lead_claim(session, claim.slug, now=self.now())
        if decided is None:
            return NothingFound(NOTHING_TO_DECIDE)
        self.results[claim.id] = decided
        return WorkOutcome.DONE
