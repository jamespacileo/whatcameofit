"""Where the link leads stand, from loading to a claim, and what the model calls for
them have cost. Behavior: openspec lead-reading, "Funnel report". Reads only."""

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from thenwhat.backfill import link_reasons as why
from thenwhat.backfill.link_read import LEAD_READING, LinkRead
from thenwhat.backfill.link_triage import Standing, standings
from thenwhat.db.models import Claim, LinkLead, LlmUsage, WorkEntry
from thenwhat.decide.steps import LEAD_TRIAGE, SAME_CLAIM, TREATMENT_KIND, VERTICAL_CHOICE
from thenwhat.domain import Decider, ReadOutcome, ReviewState, ScreenOutcome, WorkOutcome

TRIAGE_PURPOSE = f"decision:{LEAD_TRIAGE}"
READING_PURPOSES = (
    LEAD_READING,
    f"decision:{VERTICAL_CHOICE}",
    f"decision:{SAME_CLAIM}",
    f"decision:{TREATMENT_KIND}",
)


# The read's reasons by code, and what is said of a lead whose entry holds none.
WORDS = {reason.code: reason for reason in why.REASONS}
NO_CODE = "no reason code recorded"


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
    identity_unresolved: int
    enough_articles: int
    # Why leads could not be read, and how many for each reason, in the words made from
    # the reason's code.
    cannot_be_read: dict[str, int]
    # Leads put off, to be asked for again by themselves, and why.
    put_off: dict[str, int]
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
            + self.identity_unresolved
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
    # The entry of each lead's read, which holds why as a code with its values.
    read = and_(
        WorkEntry.record_kind == LinkRead.record_kind,
        WorkEntry.record_id == LinkLead.id,
        WorkEntry.step == LinkRead.name,
        WorkEntry.step_version == LinkRead.version,
    )
    # A reason's values apart from the outlet, so one line counts every outlet.
    carried = WorkEntry.reason_values.op("-")("outlet")
    undated = session.execute(
        select(LinkLead.outlet, func.count())
        .join(WorkEntry, read)
        .where(unreadable, WorkEntry.reason == why.NO_DATE.code)
        .group_by(LinkLead.outlet)
        .order_by(func.count().desc(), LinkLead.outlet)
    ).all()

    def by_reason(*conditions) -> dict[str, int]:
        """How many leads for each reason, in the words made from its code, the reason
        most leads have first."""
        rows = session.execute(
            select(WorkEntry.reason, carried, func.count())
            .select_from(LinkLead)
            .outerjoin(WorkEntry, read)
            .where(*conditions)
            .group_by(WorkEntry.reason, carried)
        ).all()
        counted: dict[str, int] = {}
        for code, values, number in rows:
            words = NO_CODE if code not in WORDS else WORDS[code].say(values or {})
            counted[words] = counted.get(words, 0) + number
        return dict(sorted(counted.items(), key=lambda line: (-line[1], line[0])))

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
        identity_unresolved=number(LinkLead.read_outcome == ReadOutcome.IDENTITY_UNRESOLVED),
        enough_articles=number(LinkLead.read_outcome == ReadOutcome.ENOUGH_ARTICLES),
        cannot_be_read=by_reason(unreadable),
        put_off=by_reason(WorkEntry.outcome == WorkOutcome.LATER, WorkEntry.stale.is_(False)),
        undated_outlets=[(outlet, count) for outlet, count in undated],
        triage_cost_usd=_cost(session, (TRIAGE_PURPOSE,)),
        reading_cost_usd=_cost(session, READING_PURPOSES),
    )
