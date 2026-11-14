"""What the loaded link leads are, by where they were shared: how many are in scope by
kind of outlet, already tracked, and linked to stored claims and trials.
Behavior: openspec lead-screening, "Screening report"."""

from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_, distinct, exists, func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.link_screen import CLAIM, REGISTRY_TRIAL
from thenwhat.db.models import LinkLead, LinkLeadLink, LinkShare
from thenwhat.domain import OutletKind, ScreenOutcome

IN_SCOPE_KINDS = (OutletKind.GENERAL_NEWS, OutletKind.TRADE_PRESS, OutletKind.PRESS_RELEASE)
UNLISTED_SHOWN = 20


@dataclass(frozen=True, slots=True)
class PlaceCounts:
    """The link leads shared in one community of one platform. A lead shared in two
    places is counted in both."""

    platform: str
    community: str
    loaded: int
    screened: int
    in_scope: dict[OutletKind, int]
    already_tracked: int
    unlisted: int
    linked_to_claim: int
    linked_to_trial: int

    @property
    def in_scope_total(self) -> int:
        return sum(self.in_scope.values())

    def share(self, number: int) -> int:
        """A count as a whole percentage of the leads screened."""
        return round(100 * number / self.screened) if self.screened else 0


@dataclass(frozen=True, slots=True)
class ScreeningReport:
    places: list[PlaceCounts]
    # The unlisted domains with the most leads, and how many each has.
    unlisted_domains: list[tuple[str, int]]

    @property
    def screened(self) -> int:
        return sum(place.screened for place in self.places)


def _linked_to(kind: str) -> ColumnElement[bool]:
    return exists().where(
        LinkLeadLink.link_lead_id == LinkLead.id, LinkLeadLink.record_kind == kind
    )


def screening_report(session: Session) -> ScreeningReport:
    """Count the link leads by platform and community. Reads only; sends nothing."""
    lead = distinct(LinkLead.id)
    in_scope = LinkLead.screen_outcome == ScreenOutcome.IN_SCOPE

    def number(condition: ColumnElement[bool]) -> ColumnElement[int]:
        return func.count(lead).filter(condition)

    rows = session.execute(
        select(
            LinkShare.platform,
            LinkShare.community,
            func.count(lead),
            number(LinkLead.screen_outcome.is_not(None)),
            *(number(and_(in_scope, LinkLead.outlet_kind == kind)) for kind in IN_SCOPE_KINDS),
            number(LinkLead.screen_outcome == ScreenOutcome.ALREADY_TRACKED),
            number(LinkLead.screen_outcome == ScreenOutcome.UNLISTED_OUTLET),
            number(and_(in_scope, _linked_to(CLAIM))),
            number(and_(in_scope, _linked_to(REGISTRY_TRIAL))),
        )
        .join(LinkLead, LinkLead.id == LinkShare.link_lead_id)
        .group_by(LinkShare.platform, LinkShare.community)
        .order_by(LinkShare.platform, func.count(lead).desc(), LinkShare.community)
    ).all()
    places = [
        PlaceCounts(
            platform=row[0],
            community=row[1],
            loaded=row[2],
            screened=row[3],
            in_scope=dict(zip(IN_SCOPE_KINDS, row[4:7], strict=True)),
            already_tracked=row[7],
            unlisted=row[8],
            linked_to_claim=row[9],
            linked_to_trial=row[10],
        )
        for row in rows
    ]
    unlisted = session.execute(
        select(LinkLead.outlet, func.count())
        .where(LinkLead.screen_outcome == ScreenOutcome.UNLISTED_OUTLET)
        .group_by(LinkLead.outlet)
        .order_by(func.count().desc(), LinkLead.outlet)
        .limit(UNLISTED_SHOWN)
    ).all()
    return ScreeningReport(places, [(domain, count) for domain, count in unlisted])
