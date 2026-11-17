"""How many processed trials have an article lead, in all and by kind of outlet.
Behavior: openspec article-leads, "Hit rate report"."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.db.models import ArticleLead, WorkEntry
from thenwhat.domain import OutletKind
from thenwhat.work.ledger import FINISHED
from thenwhat.work.steps import Step


@dataclass(frozen=True, slots=True)
class HitRates:
    # Trials the step has finished, whether or not anything was found.
    processed: int
    with_a_lead: int
    # Trials with at least one lead from an outlet of each kind. A trial can be in several.
    by_kind: dict[OutletKind, int]

    def share(self, count: int) -> int:
        return round(100 * count / self.processed) if self.processed else 0


def hit_rates(session: Session, step: Step) -> HitRates:
    finished = (
        select(WorkEntry.record_id)
        .where(
            WorkEntry.record_kind == step.record_kind,
            WorkEntry.step == step.name,
            WorkEntry.step_version == step.version,
            WorkEntry.outcome.in_(FINISHED),
            WorkEntry.stale.is_(False),
        )
        .subquery()
    )
    processed = session.scalar(select(func.count()).select_from(finished)) or 0
    leads = select(ArticleLead.registry_trial_id, ArticleLead.outlet_kind).where(
        ArticleLead.registry_trial_id.in_(select(finished.c.record_id)),
        ArticleLead.source_name == step.source,
    )
    found = leads.subquery()
    with_a_lead = session.scalar(select(func.count(func.distinct(found.c.registry_trial_id)))) or 0
    rows = session.execute(
        select(found.c.outlet_kind, func.count(func.distinct(found.c.registry_trial_id))).group_by(
            found.c.outlet_kind
        )
    ).all()
    by_kind = {kind: 0 for kind in OutletKind}
    by_kind.update({OutletKind(kind): number for kind, number in rows})
    return HitRates(processed, with_a_lead, by_kind)
