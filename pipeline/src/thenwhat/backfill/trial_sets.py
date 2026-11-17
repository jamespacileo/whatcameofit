"""Sets of stored trials named by their activity and results, selected by rule from the
stored trials alone, asking no source. A set says only which trials are in it, never how
any of them turned out. Behavior: openspec registry-corpus."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.orm import Session

from thenwhat.db.models import RegistryTrial
from thenwhat.work.errors import BackfillError

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

# The trial target set, decided by the operator on 2026-11-17: every trial under way
# now, whatever its phase, and every trial that ended in the current calendar year. It
# rolls with the year, so its rule takes the year and no clock is read here: a command
# gives the year it runs in. The two sets above keep their names and their rules. Every
# trial of `active-since-2025` is in this set; `completed-with-results-since-2025` is
# in it only for the trials completed in the year given.
ROLLING = "active-or-ended-this-year"
ENDED = ("COMPLETED", "TERMINATED", "WITHDRAWN", "SUSPENDED")
NOT_COMPLETED = ("TERMINATED", "WITHDRAWN", "SUSPENDED")
NAMES = (*SETS, ROLLING)


def under_way() -> ColumnElement[bool]:
    """Under way now, in any phase, whenever the registry last updated the record."""
    return RegistryTrial.overall_status.in_(UNDER_WAY)


def ended_in(year: int, statuses: tuple[str, ...] = ENDED) -> ColumnElement[bool]:
    """Listed as completed, terminated, withdrawn or suspended, with a completion date
    in the year. The date is text, a year and month with or without a day, so it is in
    the year when it begins with it. Says nothing of how the trial turned out."""
    return and_(
        RegistryTrial.overall_status.in_(statuses),
        RegistryTrial.completion_date.startswith(f"{year:04d}", autoescape=True),
    )


def active_or_ended_in(year: int) -> ColumnElement[bool]:
    return or_(under_way(), ended_in(year))


def groups_of(year: int) -> dict[str, ColumnElement[bool]]:
    """The rolling set in three groups that share no trial, named in the registry's own
    words for a trial's state."""
    return {
        "under way": under_way(),
        f"completed in {year}": ended_in(year, ("COMPLETED",)),
        f"terminated, withdrawn or suspended in {year}": ended_in(year, NOT_COMPLETED),
    }


NO_WIDER_RECORD = (
    "No stored trial has the activity and results fields yet. Load the trials "
    "again in full: `thenwhat backfill load-trials --trials interventional`."
)


class UnknownSet(BackfillError):
    """No set of stored trials has the name given."""


class NoWiderRecord(BackfillError):
    """No stored trial holds the fields the sets are chosen by."""


class YearNotGiven(BackfillError):
    """The rolling set was asked for without the year it is chosen in."""


def rule_of(name: str, year: int | None = None) -> Callable[[], ColumnElement[bool]]:
    """The rule of a named set of stored trials. Refuses a name it does not know with
    the list of sets. The rolling set needs the year it is chosen in, which the command
    reads from the clock; the two dated sets ignore it."""
    if name == ROLLING:
        if year is None:
            raise YearNotGiven(f"The set '{ROLLING}' is chosen by the year, and none was given.")
        return lambda: active_or_ended_in(year)
    if name not in SETS:
        raise UnknownSet(f"No set of stored trials is named '{name}'. Sets: {', '.join(NAMES)}.")
    return SETS[name]


def require_wider_record(session: Session) -> None:
    """Refuse when no stored trial was loaded with the fields the sets are chosen by:
    every set would be empty, which says nothing of the trials."""
    loaded = session.scalar(
        select(RegistryTrial.id).where(RegistryTrial.last_update_posted.is_not(None)).limit(1)
    )
    if loaded is None:
        raise NoWiderRecord(NO_WIDER_RECORD)


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


def count_sets(session: Session, year: int | None = None) -> SetsReport:
    """Count the dated sets, and the rolling set too when its year is given."""
    counts: list[SetCount] = []
    rules = dict(SETS) | ({ROLLING: rule_of(ROLLING, year)} if year is not None else {})
    for name, rule in rules.items():
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
