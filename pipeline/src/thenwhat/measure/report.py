"""What the measurements of a range of days say. Behavior: openspec processing-metrics.

`report_of` is pure: it takes totals and what claims took and gives the figures.
`gather` reads them: kept totals for days already added, and the span files for days
that are not, today among them.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, MeasureClaim, MeasureDaily, MeasureRolledDay
from thenwhat.measure.files import days_held, read_day
from thenwhat.measure.totals import Key, Total, stored_totals, totals_of


@dataclass(frozen=True, slots=True)
class ClaimTook:
    """What one published claim took."""

    # From its first measured step to its publication.
    elapsed_seconds: float
    ran_seconds: float
    waited_seconds: float
    cost_usd: Decimal


@dataclass(frozen=True, slots=True)
class StepLine:
    step: str
    writer: str
    spans: int
    records: int
    ran_seconds: float
    waited_seconds: float
    cost_usd: Decimal
    # Records by how the step ended for them.
    outcomes: dict[str, int]
    # Share of this step's measurements answered from a stored result.
    reused_share: float
    share_of_time: float
    share_of_cost: float


@dataclass(frozen=True, slots=True)
class ClaimLine:
    claims: int
    median_cost_usd: Decimal
    worst_cost_usd: Decimal
    median_elapsed_seconds: float
    worst_elapsed_seconds: float
    median_ran_seconds: float
    median_waited_seconds: float


@dataclass(frozen=True, slots=True)
class Report:
    first: date
    last: date
    steps: list[StepLine] = field(default_factory=list)
    # Seconds waited by what was waited on, longest first.
    waited_on: list[tuple[str, float]] = field(default_factory=list)
    requests: list[tuple[str, int]] = field(default_factory=list)
    claims: ClaimLine | None = None
    total_cost_usd: Decimal = Decimal(0)
    total_ran_seconds: float = 0.0
    total_waited_seconds: float = 0.0

    @property
    def empty(self) -> bool:
        return not self.steps


def report_of(first: date, last: date, totals: dict[Key, Total], claims: list[ClaimTook]) -> Report:
    by_step: dict[tuple[str, str], Total] = {}
    outcomes: dict[tuple[str, str], dict[str, int]] = {}
    waited: dict[str, float] = {}
    requests: dict[str, int] = {}
    for (step, _version, writer, outcome), total in totals.items():
        by_step.setdefault((step, writer), Total()).merge(total)
        ended = outcomes.setdefault((step, writer), {})
        ended[outcome] = ended.get(outcome, 0) + total.records
        for cause, seconds in total.waited_by_cause.items():
            waited[cause] = waited.get(cause, 0.0) + float(seconds)
        for source, count in total.requests_by_source.items():
            requests[source] = requests.get(source, 0) + int(count)
    all_time = sum(t.ran_seconds + t.waited_seconds for t in by_step.values())
    all_cost = sum((t.cost_usd for t in by_step.values()), Decimal(0))
    steps = [
        StepLine(
            step=step,
            writer=writer,
            spans=total.spans,
            records=total.records,
            ran_seconds=total.ran_seconds,
            waited_seconds=total.waited_seconds,
            cost_usd=total.cost_usd,
            outcomes=outcomes[(step, writer)],
            reused_share=total.reused / total.spans if total.spans else 0.0,
            share_of_time=(total.ran_seconds + total.waited_seconds) / all_time
            if all_time
            else 0.0,
            share_of_cost=float(total.cost_usd / all_cost) if all_cost else 0.0,
        )
        for (step, writer), total in by_step.items()
    ]
    steps.sort(key=lambda line: line.ran_seconds + line.waited_seconds, reverse=True)
    claim_line = None
    if claims:
        claim_line = ClaimLine(
            claims=len(claims),
            median_cost_usd=Decimal(str(median(took.cost_usd for took in claims))),
            worst_cost_usd=max(took.cost_usd for took in claims),
            median_elapsed_seconds=median(took.elapsed_seconds for took in claims),
            worst_elapsed_seconds=max(took.elapsed_seconds for took in claims),
            median_ran_seconds=median(took.ran_seconds for took in claims),
            median_waited_seconds=median(took.waited_seconds for took in claims),
        )
    return Report(
        first=first,
        last=last,
        steps=steps,
        waited_on=sorted(waited.items(), key=lambda item: item[1], reverse=True),
        requests=sorted(requests.items(), key=lambda item: item[1], reverse=True),
        claims=claim_line,
        total_cost_usd=all_cost,
        total_ran_seconds=sum(t.ran_seconds for t in by_step.values()),
        total_waited_seconds=sum(t.waited_seconds for t in by_step.values()),
    )


def claims_published(session: Session, first: date, last: date) -> list[ClaimTook]:
    """What each claim published in the range took, for claims with measurements."""
    rows = session.execute(
        select(Claim.published_at, MeasureClaim)
        .join(MeasureClaim, MeasureClaim.claim_id == Claim.id)
        .where(Claim.published_at.is_not(None))
    )
    took: list[ClaimTook] = []
    for published_at, measured in rows:
        assert isinstance(published_at, datetime)
        if not first <= published_at.date() <= last:
            continue
        took.append(
            ClaimTook(
                elapsed_seconds=max((published_at - measured.first_seen_at).total_seconds(), 0.0),
                ran_seconds=measured.ran_seconds,
                waited_seconds=measured.waited_seconds,
                cost_usd=measured.cost_usd,
            )
        )
    return took


def gather(session: Session, folder: Path | None, first: date, last: date) -> Report:
    """The report for a range of days: kept totals, plus the span files of days in the
    range that have not been added to the totals yet."""
    totals = stored_totals(session, first, last)
    if folder is not None:
        rolled = set(session.scalars(select(MeasureRolledDay.day)))
        for day in days_held(folder):
            if first <= day <= last and day not in rolled:
                for key, total in totals_of(read_day(folder, day)).items():
                    totals.setdefault(key, Total()).merge(total)
    return report_of(first, last, totals, claims_published(session, first, last))


# How many days of measurements a step needs before its measured cost is used in a
# plan in place of its own estimate, and how far back they are looked for.
DAYS_NEEDED = 7
DAYS_BACK = 30


@dataclass(frozen=True, slots=True)
class MeasuredCost:
    per_record: Decimal
    days: int


def measured_cost_of_a_record(session: Session, step: str, *, today: date) -> MeasuredCost | None:
    """What one record of a step cost, from the kept totals of the last days: the
    step's own cost and the cost of what was measured inside it. None when the step has
    fewer than a week of days with measurements, so that a plan falls back on the
    step's estimate."""
    rows = list(
        session.scalars(
            select(MeasureDaily).where(
                MeasureDaily.step == step,
                MeasureDaily.day >= today - timedelta(days=DAYS_BACK),
                MeasureDaily.day < today,
            )
        )
    )
    days = len({row.day for row in rows})
    records = sum(row.records for row in rows)
    if days < DAYS_NEEDED or records == 0:
        return None
    cost = sum((row.cost_usd + row.inner_cost_usd for row in rows), Decimal(0))
    return MeasuredCost(per_record=cost / records, days=days)
