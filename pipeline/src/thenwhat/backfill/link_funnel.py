"""Where the link leads stand, from loading to a claim, and what the model calls for
them have cost. Behavior: openspec lead-reading, "Funnel report". Reads only."""

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.link_read import LEAD_READING, NO_DATE
from thenwhat.backfill.link_triage import Standing, standings
from thenwhat.db.models import Claim, LinkLead, LlmUsage
from thenwhat.decide.steps import LEAD_TRIAGE, VERTICAL_CHOICE
from thenwhat.domain import Decider, ReadOutcome, ReviewState, ScreenOutcome

TRIAGE_PURPOSE = f"decision:{LEAD_TRIAGE}"
READING_PURPOSES = (LEAD_READING, f"decision:{VERTICAL_CHOICE}")


@dataclass(frozen=True, slots=True)
class Funnel:
    loaded: int
    in_scope: int
    scored: int
    standing: Counter[Standing]
    added_to_claim: int
    new_approved_by_rule: int
    new_rejected_by_rule: int
    # Drafted by a read and not yet decided: `thenwhat prepare --pending` searches the
    # registries for it and then decides it by rule.
    new_awaiting_preparation: int
    new_otherwise: int
    needs_vertical: int
    # Read, and not about one treatment for one condition: no claim was made.
    not_one_treatment: int
    # Read, on a topic, and about a treatment's business: no claim was made.
    business_news: int
    enough_articles: int
    # Why leads could not be read, and how many for each reason.
    cannot_be_read: dict[str, int]
    # The outlets whose pages gave no publication date, and how many leads each lost.
    undated_outlets: list[tuple[str, int]]
    triage_cost_usd: Decimal
    reading_cost_usd: Decimal

    @property
    def read(self) -> int:
        """Leads whose article the model read: it made or joined a claim, or lacked only
        a vertical."""
        return (
            self.added_to_claim
            + self.new_approved_by_rule
            + self.new_rejected_by_rule
            + self.new_awaiting_preparation
            + self.new_otherwise
            + self.needs_vertical
            + self.not_one_treatment
            + self.business_news
        )


def _cost(session: Session, purposes: tuple[str, ...]) -> Decimal:
    total = session.scalar(
        select(func.coalesce(func.sum(LlmUsage.cost_usd), 0)).where(LlmUsage.purpose.in_(purposes))
    )
    return Decimal(total or 0)


def funnel(session: Session, *, pass_above: float | None, reject_below: float | None) -> Funnel:
    def number(*conditions) -> int:
        return session.scalar(select(func.count()).select_from(LinkLead).where(*conditions)) or 0

    def new_claims(*conditions) -> int:
        return (
            session.scalar(
                select(func.count())
                .select_from(LinkLead)
                .join(Claim, Claim.id == LinkLead.claim_id)
                .where(LinkLead.read_outcome == ReadOutcome.NEW_CLAIM, *conditions)
            )
            or 0
        )

    by_rule = Claim.reviewed_by == Decider.RULE
    approved = new_claims(Claim.review_state == ReviewState.APPROVED, by_rule)
    rejected = new_claims(Claim.review_state == ReviewState.REJECTED, by_rule)
    awaiting = new_claims(Claim.review_state == ReviewState.PENDING)
    unreadable = LinkLead.read_outcome == ReadOutcome.CANNOT_BE_READ
    reasons = session.execute(
        select(LinkLead.read_detail, func.count())
        .where(unreadable)
        .group_by(LinkLead.read_detail)
        .order_by(func.count().desc(), LinkLead.read_detail)
    ).all()
    undated = session.execute(
        select(LinkLead.outlet, func.count())
        .where(unreadable, LinkLead.read_detail == NO_DATE)
        .group_by(LinkLead.outlet)
        .order_by(func.count().desc(), LinkLead.outlet)
    ).all()
    in_scope = LinkLead.screen_outcome == ScreenOutcome.IN_SCOPE
    return Funnel(
        loaded=number(),
        in_scope=number(in_scope),
        scored=number(in_scope, LinkLead.triage_score.is_not(None)),
        standing=standings(session, pass_above, reject_below),
        added_to_claim=number(LinkLead.read_outcome == ReadOutcome.ADDED_TO_CLAIM),
        new_approved_by_rule=approved,
        new_rejected_by_rule=rejected,
        new_awaiting_preparation=awaiting,
        new_otherwise=new_claims() - approved - rejected - awaiting,
        needs_vertical=number(LinkLead.read_outcome == ReadOutcome.NEEDS_VERTICAL),
        not_one_treatment=number(LinkLead.read_outcome == ReadOutcome.NOT_ONE_TREATMENT),
        business_news=number(LinkLead.read_outcome == ReadOutcome.BUSINESS_NEWS),
        enough_articles=number(LinkLead.read_outcome == ReadOutcome.ENOUGH_ARTICLES),
        cannot_be_read={reason or "no reason recorded": count for reason, count in reasons},
        undated_outlets=[(outlet, count) for outlet, count in undated],
        triage_cost_usd=_cost(session, (TRIAGE_PURPOSE,)),
        reading_cost_usd=_cost(session, READING_PURPOSES),
    )
