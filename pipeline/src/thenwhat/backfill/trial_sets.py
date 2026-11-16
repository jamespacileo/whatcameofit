"""Sets of stored trials named by their activity and results, selected by rule from the
stored trials alone, asking no source. A set says only which trials are in it, never how
any of them turned out. Behavior: openspec registry-corpus."""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.orm import Session

from thenwhat.db.models import RegistryTrial

# Both sets start on 1 January 2025. A completion date can be a year and month without
# a day, so it is compared by its year: any date the registry writes for 2025 or later,
# in either form, sorts at or after "2025".
SINCE = date(2025, 1, 1)
_SINCE_YEAR = str(SINCE.year)

UNDER_WAY = (
    "RECRUITING",
    "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "ACTIVE_NOT_RECRUITING",
)


def active_since_2025() -> ColumnElement[bool]:
    """Phase 2 or 3, under way now, and with a record the registry updated on or after
    1 January 2025."""
    return and_(
        RegistryTrial.phases.overlap(["PHASE2", "PHASE3"]),
        RegistryTrial.overall_status.in_(UNDER_WAY),
        RegistryTrial.last_update_posted >= SINCE,
    )


def completed_with_results_since_2025() -> ColumnElement[bool]:
    """Completed, with an actual completion date on or after 1 January 2025, and with
    results posted. Says nothing of what the results were."""
    return and_(
        RegistryTrial.overall_status == "COMPLETED",
        RegistryTrial.completion_date_type == "ACTUAL",
        RegistryTrial.completion_date >= _SINCE_YEAR,
        RegistryTrial.has_results.is_(True),
    )


SETS = {
    "active-since-2025": active_since_2025,
    "completed-with-results-since-2025": completed_with_results_since_2025,
}


@dataclass(slots=True)
class SetCount:
    name: str
    total: int = 0
    # Keyed by the trial's phases as the registry lists them, joined: "PHASE2, PHASE3"
    # is one key, so the counts add up to the total.
    by_phase: dict[tuple[str, ...], int] = field(default_factory=dict)
    loaded_first: date | None = None
    loaded_last: date | None = None


@dataclass(slots=True)
class SetsReport:
    sets: list[SetCount]
    # Stored trials with none of the wider record: loaded before it was asked for, so
    # in neither set until loaded again.
    without_wider_record: int
    stored: int


def count_sets(session: Session) -> SetsReport:
    counts: list[SetCount] = []
    for name, rule in SETS.items():
        counted = SetCount(name)
        rows = session.execute(
            select(
                RegistryTrial.phases,
                func.count(),
                func.min(RegistryTrial.fetched_at),
                func.max(RegistryTrial.fetched_at),
            )
            .where(rule())
            .group_by(RegistryTrial.phases)
        )
        for phases, number, first, last in rows:
            counted.by_phase[tuple(phases or ())] = number
            counted.total += number
            first_day, last_day = first.date(), last.date()
            if counted.loaded_first is None or first_day < counted.loaded_first:
                counted.loaded_first = first_day
            if counted.loaded_last is None or last_day > counted.loaded_last:
                counted.loaded_last = last_day
        counts.append(counted)
    stored, without = session.execute(
        select(
            func.count(),
            func.count().filter(RegistryTrial.last_update_posted.is_(None)),
        ).select_from(RegistryTrial)
    ).one()
    return SetsReport(counts, without, stored)
