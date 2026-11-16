"""Working out what each claim needs before it can be reviewed, and deciding a claim
that a link lead's read drafted once it has been prepared.

Planning: which articles are unread, and the commands to run. Running them is the
command's job.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import claim_by_slug, find_claim
from thenwhat.db.models import Claim, Entity, LinkLead, SourceArticle
from thenwhat.domain import Decider, EntityType, ReadOutcome, ReviewState
from thenwhat.extract.names import is_a_name
from thenwhat.review.decisions import record_decision


@dataclass(frozen=True, slots=True)
class ClaimPlan:
    slug: str
    # Articles the model has not read yet. Only a claim still awaiting review has any:
    # a decided claim is never redrafted.
    unread_articles: list[str]


def plan_claims(session: Session, slugs: list[str] | None) -> list[ClaimPlan]:
    """A plan for each named claim, or for every claim awaiting review when none is named."""
    if slugs is None:
        claims = list(
            session.scalars(
                select(Claim).where(Claim.review_state == ReviewState.PENDING).order_by(Claim.slug)
            )
        )
    else:
        claims = [claim_by_slug(session, slug) for slug in slugs]

    plans: list[ClaimPlan] = []
    for claim in claims:
        unread: list[str] = []
        if claim.review_state is ReviewState.PENDING:
            unread = list(
                session.scalars(
                    select(SourceArticle.url)
                    .where(SourceArticle.claim_id == claim.id, SourceArticle.content_hash.is_(None))
                    .order_by(SourceArticle.published_date, SourceArticle.id)
                )
            )
        plans.append(ClaimPlan(claim.slug, unread))
    return plans


def steps_for(plan: ClaimPlan) -> list[list[str]]:
    """The commands that prepare one claim, in order: read its unread articles, search the
    registries, read the registries for whatever matches are already approved, then have
    the stored trial records read into record readings."""
    return [
        *(["extract", "article", plan.slug, "--article-url", url] for url in plan.unread_articles),
        ["resolve", plan.slug],
        ["fetch", plan.slug],
        ["readings", plan.slug],
    ]


def decide_prepared_lead_claim(session: Session, slug: str, *, now: datetime) -> ReviewState | None:
    """Decide, by the rule for drafts, a claim that a link lead's read drafted and that has
    now been prepared: approved when its intervention is a name, rejected when it is a
    description. Returns the decision, or None when there is nothing to decide: the claim
    is not awaiting review, or no lead's read drafted it (a claim the operator entered
    keeps waiting for the operator).

    The read leaves such a claim pending so that it is not published before its registries
    have been searched (openspec lead-reading). Call this only after that search succeeded.
    An approved claim is also marked awaiting audit, which keeps it out of every export
    until the audit of its batch clears it.
    """
    claim = find_claim(session, slug)
    if claim is None or claim.review_state is not ReviewState.PENDING:
        return None
    drafted_by_a_read = session.scalar(
        select(LinkLead.id)
        .where(LinkLead.claim_id == claim.id, LinkLead.read_outcome == ReadOutcome.NEW_CLAIM)
        .limit(1)
    )
    if drafted_by_a_read is None:
        return None
    intervention = session.scalar(
        select(Entity.name).where(
            Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION
        )
    )
    state = (
        ReviewState.APPROVED
        if intervention is not None and is_a_name(intervention)
        else ReviewState.REJECTED
    )
    record_decision(claim, state, by=Decider.RULE, now=now)
    if state is ReviewState.APPROVED:
        claim.awaiting_audit_at = now
    return state
