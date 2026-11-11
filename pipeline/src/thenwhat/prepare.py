"""Working out what each claim needs before it can be reviewed.

Pure planning: which articles are unread, and the commands to run. Running them is the
command's job.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import ClaimNotFound, find_claim
from thenwhat.db.models import Claim, SourceArticle
from thenwhat.domain import ReviewState


@dataclass(frozen=True, slots=True)
class ClaimPlan:
    claim_id: int
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
        claims = []
        for slug in slugs:
            claim = find_claim(session, slug)
            if claim is None:
                raise ClaimNotFound(f"No claim has the slug '{slug}'.")
            claims.append(claim)

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
        plans.append(ClaimPlan(claim.id, claim.slug, unread))
    return plans


def steps_for(plan: ClaimPlan) -> list[list[str]]:
    """The commands that prepare one claim, in order: read its unread articles, search the
    registries, then read the registries for whatever matches are already approved."""
    return [
        *(["extract", "article", plan.slug, "--article-url", url] for url in plan.unread_articles),
        ["resolve", plan.slug],
        ["fetch", plan.slug],
    ]
