"""Which leads are linked to trials of a named set, and what reading them would take.
Behavior: openspec trial-report-links, "What a strong link changes", "Sets of trials" and
"A plan before a set is worked".

A link changes only which leads are read and in what order. It attaches nothing to a
trial, is shown nowhere and is never exported.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, and_, false, func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.errors import BackfillError
from thenwhat.backfill.link_screen import (
    CANDIDATE,
    EXACT,
    NAMED,
    REGISTRY_TRIAL,
    STRENGTH_TO_READ,
    STRONG,
)
from thenwhat.backfill.trial_sets import rule_of
from thenwhat.db.models import LinkLead, LinkLeadLink, RegistryTrial, WorkEntry
from thenwhat.domain import ScreenOutcome

STRONGEST_FIRST = (EXACT, STRONG, NAMED, CANDIDATE)
PHASE_3 = "PHASE3"
# Of the leads read to date, the share whose read drafted a claim (openspec
# trial-first-route, design.md: 1,616 of 3,786).
CLAIMS_A_READ = Decimal("0.44")


class UnknownStrength(BackfillError):
    """No strength of link has the name given."""


def at_least(strength: str) -> tuple[str, ...]:
    """The strengths that say at least as much as the one named."""
    if strength not in STRONGEST_FIRST:
        raise UnknownStrength(
            f"No strength of link is named '{strength}'. Strengths, strongest first: "
            f"{', '.join(STRONGEST_FIRST)}."
        )
    return STRONGEST_FIRST[: STRONGEST_FIRST.index(strength) + 1]


def linked_to(
    strengths: tuple[str, ...] = STRENGTH_TO_READ,
    trial_set: str | None = None,
    *,
    phase: str | None = None,
    year: int | None = None,
) -> ColumnElement[bool]:
    """The query condition for a lead with a link of one of these strengths to a
    registry trial: any trial, or a trial of the named set, or one of its trials in the
    phase given."""
    link = (
        select(LinkLeadLink.id)
        .where(
            LinkLeadLink.link_lead_id == LinkLead.id,
            LinkLeadLink.record_kind == REGISTRY_TRIAL,
            LinkLeadLink.strength.in_(strengths),
        )
        .correlate(LinkLead)
    )
    if trial_set is not None:
        link = link.join(RegistryTrial, RegistryTrial.id == LinkLeadLink.record_id).where(
            rule_of(trial_set, year)()
        )
        if phase is not None:
            link = link.where(RegistryTrial.phases.contains([phase]))
    return link.exists()


@dataclass(frozen=True, slots=True)
class SetPlan:
    """Where the leads linked to a set stand, before any is read."""

    trial_set: str
    strengths: tuple[str, ...]
    leads: int
    trials: int
    passed: int
    held: int
    rejected: int
    not_scored: int
    already_read: int
    read_this_month: int


def plan_of(
    session: Session,
    trial_set: str,
    strengths: tuple[str, ...],
    *,
    pass_above: float | None,
    reject_below: float | None,
    read_step: str,
    now: datetime,
) -> SetPlan:
    """Count the leads in scope that are linked to the set at these strengths, by where
    triage left them, how many are read, and how many were read this month."""
    linked = and_(
        LinkLead.screen_outcome == ScreenOutcome.IN_SCOPE,
        linked_to(strengths, trial_set, year=now.year),
    )
    score = LinkLead.triage_score

    def number(condition: ColumnElement[bool]) -> Any:
        return func.count().filter(condition)

    if pass_above is None or reject_below is None:
        passed = held = rejected = false()
    else:
        passed = score >= pass_above
        held = and_(score >= reject_below, score < pass_above)
        rejected = score < reject_below
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    read_lately = (
        select(WorkEntry.id)
        .where(
            WorkEntry.record_kind == "link_lead",
            WorkEntry.record_id == LinkLead.id,
            WorkEntry.step == read_step,
            WorkEntry.last_attempt_at >= month_start,
        )
        .correlate(LinkLead)
        .exists()
    )
    row = session.execute(
        select(
            func.count(),
            number(passed),
            number(held),
            number(rejected),
            number(score.is_(None)),
            number(LinkLead.read_outcome.is_not(None)),
            number(read_lately),
        )
        .select_from(LinkLead)
        .where(linked)
    ).one()
    trials = session.scalar(
        select(func.count(func.distinct(LinkLeadLink.record_id)))
        .select_from(LinkLeadLink)
        .join(RegistryTrial, RegistryTrial.id == LinkLeadLink.record_id)
        .where(
            LinkLeadLink.record_kind == REGISTRY_TRIAL,
            LinkLeadLink.strength.in_(strengths),
            rule_of(trial_set, now.year)(),
        )
    )
    return SetPlan(trial_set, strengths, row[0], trials or 0, *row[1:])


def held_and_linked(
    trial_set: str,
    reject_below: float,
    strengths: tuple[str, ...] = STRENGTH_TO_READ,
    *,
    year: int | None = None,
) -> ColumnElement[bool]:
    """A lead triage held, linked to the set strongly enough to be read."""
    return and_(
        linked_to(strengths, trial_set, year=year),
        LinkLead.triage_score.is_not(None),
        LinkLead.triage_score >= reject_below,
    )
