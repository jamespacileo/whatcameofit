"""Adding a day's spans into totals that are kept. Behavior: openspec processing-metrics.

`totals_of` is pure. `roll` stores the totals of every finished day that has span files
and has not been added before, and adds each claim's share to what the claim took.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key
from thenwhat.db.models import Claim, MeasureClaim, MeasureDaily, MeasureRolledDay, SourceArticle
from thenwhat.measure.files import days_held, read_day
from thenwhat.measure.spans import Span

CLAIM_PREFIX = "claim:"

Key = tuple[str, int, str, str]


@dataclass(slots=True)
class Total:
    """What the spans of one step, version, writer and outcome add up to."""

    spans: int = 0
    records: int = 0
    reused: int = 0
    ran_seconds: float = 0.0
    waited_seconds: float = 0.0
    waited_by_cause: dict[str, float] = field(default_factory=dict)
    requests_by_source: dict[str, int] = field(default_factory=dict)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal(0)
    inner_cost_usd: Decimal = Decimal(0)
    rows_written: int = 0

    def add(self, span: Span) -> None:
        self.spans += 1
        self.records += sum(span.records_by_outcome().values())
        self.reused += int(span.reused)
        self.ran_seconds += span.ran_seconds
        self.waited_seconds += span.waited_seconds
        for cause, seconds in span.waited.items():
            self.waited_by_cause[cause] = self.waited_by_cause.get(cause, 0.0) + seconds
        for source, count in span.requests.items():
            self.requests_by_source[source] = self.requests_by_source.get(source, 0) + count
        self.tokens_in += span.tokens_in
        self.tokens_out += span.tokens_out
        self.cost_usd += span.cost_usd
        self.inner_cost_usd += span.inner_cost_usd
        self.rows_written += span.rows_written

    def merge(self, other: "Total") -> None:
        self.spans += other.spans
        self.records += other.records
        self.reused += other.reused
        self.ran_seconds += other.ran_seconds
        self.waited_seconds += other.waited_seconds
        for cause, seconds in other.waited_by_cause.items():
            self.waited_by_cause[cause] = self.waited_by_cause.get(cause, 0.0) + float(seconds)
        for source, count in other.requests_by_source.items():
            self.requests_by_source[source] = self.requests_by_source.get(source, 0) + int(count)
        self.tokens_in += other.tokens_in
        self.tokens_out += other.tokens_out
        self.cost_usd += other.cost_usd
        self.inner_cost_usd += other.inner_cost_usd
        self.rows_written += other.rows_written


def totals_of(spans: Iterable[Span]) -> dict[Key, Total]:
    """Spans added up by step, version, writer and outcome."""
    totals: dict[Key, Total] = {}
    for span in spans:
        key = (span.step, span.step_version, span.writer, span.outcome)
        totals.setdefault(key, Total()).add(span)
    return totals


@dataclass(slots=True)
class Rolled:
    days: list[date] = field(default_factory=list)
    spans: int = 0
    claims: int = 0


def _claims_by_trace(session: Session) -> dict[str, int]:
    """Which claim a trace belongs to: by the claim's slug, or by the address key of
    one of its source articles."""
    by_trace: dict[str, int] = {}
    for claim_id, slug in session.execute(select(Claim.id, Claim.slug)):
        by_trace[f"{CLAIM_PREFIX}{slug}"] = claim_id
    for claim_id, url in session.execute(select(SourceArticle.claim_id, SourceArticle.url)):
        key = article_key(url)
        if key is not None:
            by_trace.setdefault(key, claim_id)
    return by_trace


def _add_to_claims(session: Session, spans: list[Span]) -> int:
    by_trace = _claims_by_trace(session)
    # Each claim's spans with the share of each that is the claim's: a call that
    # covered twenty leads gives a twentieth of its time and cost to each.
    touched: dict[int, list[tuple[Span, float]]] = {}
    for span in spans:
        named = [span.trace] if span.trace else span.traces
        share = 1.0 / max(span.batch, 1) if span.traces and not span.trace else 1.0
        for trace in named:
            claim_id = by_trace.get(trace)
            if claim_id is not None:
                touched.setdefault(claim_id, []).append((span, share))
    for claim_id, shares in touched.items():
        theirs = [span for span, _ in shares]
        took = session.scalars(
            select(MeasureClaim).where(MeasureClaim.claim_id == claim_id)
        ).one_or_none()
        first = min(span.started_at for span in theirs)
        last = max(span.started_at for span in theirs)
        if took is None:
            took = MeasureClaim(
                claim_id=claim_id,
                first_seen_at=first,
                last_step_at=last,
                spans=0,
                ran_seconds=0.0,
                waited_seconds=0.0,
                cost_usd=Decimal(0),
            )
            session.add(took)
        took.first_seen_at = min(took.first_seen_at, first)
        took.last_step_at = max(took.last_step_at, last)
        took.spans += len(theirs)
        took.ran_seconds += sum(span.ran_seconds * share for span, share in shares)
        took.waited_seconds += sum(span.waited_seconds * share for span, share in shares)
        took.cost_usd += sum(
            (span.cost_usd * Decimal(str(share)) for span, share in shares), Decimal(0)
        )
    return len(touched)


def roll(session: Session, folder: Path, *, today: date, now: datetime) -> Rolled:
    """Store the totals of each finished day not yet added, and add to what each claim
    took. A day is added once: running this again changes nothing. Today is left alone,
    because it is not over."""
    rolled = Rolled()
    done = set(session.scalars(select(MeasureRolledDay.day)))
    for day in days_held(folder):
        if day >= today or day in done:
            continue
        spans = list(read_day(folder, day))
        session.execute(delete(MeasureDaily).where(MeasureDaily.day == day))
        for (step, version, writer, outcome), total in totals_of(spans).items():
            session.add(
                MeasureDaily(
                    day=day,
                    step=step,
                    step_version=version,
                    writer=writer,
                    outcome=outcome,
                    spans=total.spans,
                    records=total.records,
                    reused=total.reused,
                    ran_seconds=total.ran_seconds,
                    waited_seconds=total.waited_seconds,
                    waited_by_cause=total.waited_by_cause,
                    requests_by_source=total.requests_by_source,
                    tokens_in=total.tokens_in,
                    tokens_out=total.tokens_out,
                    cost_usd=total.cost_usd,
                    inner_cost_usd=total.inner_cost_usd,
                    rows_written=total.rows_written,
                )
            )
        rolled.claims += _add_to_claims(session, spans)
        session.add(MeasureRolledDay(day=day, rolled_at=now))
        rolled.days.append(day)
        rolled.spans += len(spans)
    session.flush()
    return rolled


def stored_totals(session: Session, first: date, last: date) -> dict[Key, Total]:
    """The kept totals for a range of days, added up across the days."""
    totals: dict[Key, Total] = {}
    rows = session.scalars(
        select(MeasureDaily).where(MeasureDaily.day >= first, MeasureDaily.day <= last)
    )
    for row in rows:
        key = (row.step, row.step_version, row.writer, row.outcome)
        totals.setdefault(key, Total()).merge(
            Total(
                spans=row.spans,
                records=row.records,
                reused=row.reused,
                ran_seconds=row.ran_seconds,
                waited_seconds=row.waited_seconds,
                waited_by_cause=dict(row.waited_by_cause),
                requests_by_source=dict(row.requests_by_source),
                tokens_in=row.tokens_in,
                tokens_out=row.tokens_out,
                cost_usd=row.cost_usd,
                inner_cost_usd=row.inner_cost_usd,
                rows_written=row.rows_written,
            )
        )
    return totals
