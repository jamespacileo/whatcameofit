"""Shared pieces for the backfill tests: registry trials, a step whose behavior a test
sets, and sessions that stand in for separate processes."""

import threading
from collections.abc import Callable, Generator, Sequence
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Engine, delete
from sqlalchemy.orm import Session

from thenwhat.db.models import (
    ArticleLead,
    LlmUsage,
    RegistryTrial,
    SourceAllowanceUse,
    WorkEntry,
)
from thenwhat.domain import OutletKind, WorkOutcome
from thenwhat.work.steps import MODEL, NO_SOURCE, ModelSpend

NOW = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)


def add_trials(
    session: Session, count: int, *, registry: str = "demo-registry", name: str | None = "drug"
) -> list[RegistryTrial]:
    trials = [
        RegistryTrial(
            registry_name=registry,
            external_id=f"T{number:04d}",
            title=f"Trial {number}",
            conditions=["condition"],
            interventions=[{"type": "DRUG", "name": f"{name} {number}"}] if name else [],
            phases=["PHASE3"],
            search_name=f"{name} {number}" if name else None,
            search_indication="condition" if name else None,
            raw_payload={},
            fetched_at=NOW,
        )
        for number in range(count)
    ]
    session.add_all(trials)
    session.flush()
    return trials


class Client:
    """A source client that only counts."""

    def __init__(self) -> None:
        self.requests_made = 0


class DemoStep:
    """A step over registry trials. A test names the trials that fail or find nothing."""

    record_kind = "registry_trial"
    model = RegistryTrial
    source = "demo-source"
    requests_per_record = 1

    def __init__(self, name: str = "demo", version: int = 1, registry: str = "demo-registry"):
        self.name = name
        self.version = version
        self.registry = registry
        self.fails: set[str] = set()
        self.finds_nothing: set[str] = set()
        self.ran: list[str] = []
        self._lock = threading.Lock()
        # Called for each record before anything else, for example to claim an allowance.
        self.before: Callable[[RegistryTrial], None] | None = None

    def scope(self) -> ColumnElement[bool]:
        return (RegistryTrial.registry_name == self.registry) & RegistryTrial.search_name.is_not(
            None
        )

    def inputs(self, record: RegistryTrial) -> dict[str, Any]:
        return {"name": record.search_name}

    def run(self, session: Session, record: RegistryTrial, client: Client) -> WorkOutcome:
        if self.before is not None:
            self.before(record)
        client.requests_made += 1
        with self._lock:
            self.ran.append(record.external_id)
        if record.external_id in self.finds_nothing:
            return WorkOutcome.NOTHING_FOUND
        # A result, written before the step can fail, so a failure has something to undo.
        session.add(
            ArticleLead(
                registry_trial_id=record.id,
                url=f"https://news.example.org/{self.name}/{record.external_id}",
                outlet="news.example.org",
                title="A synthetic headline",
                outlet_kind=OutletKind.UNKNOWN,
                source_name=self.source,
                search_query="synthetic",
                raw_result={},
                fetched_at=NOW,
            )
        )
        session.flush()
        if record.external_id in self.fails:
            raise RuntimeError(f"could not process {record.external_id}")
        return WorkOutcome.DONE


class QuietStep(DemoStep):
    """A step that asks no source: it only reads the database."""

    source = NO_SOURCE
    requests_per_record = 0

    def run(self, session: Session, record: RegistryTrial, client: Client) -> WorkOutcome:
        with self._lock:
            self.ran.append(record.external_id)
        return WorkOutcome.DONE


class ModelStep(DemoStep):
    """A step that calls a model for several records at once. A test names the trials
    the model gives no answer for, and what each call costs."""

    source = MODEL
    requests_per_record = 0
    model_spend = ModelSpend(input_tokens=40)

    def __init__(
        self,
        name: str = "demo-model",
        version: int = 1,
        registry: str = "demo-registry",
        *,
        batch_size: int = 20,
        call_cost_usd: Decimal = Decimal(0),
    ) -> None:
        super().__init__(name, version, registry)
        self.batch_size = batch_size
        self.call_cost_usd = call_cost_usd
        self.unanswered: set[str] = set()
        # The trials of each call made, in order.
        self.calls: list[list[str]] = []

    def _call(self, session: Session, records: Sequence[RegistryTrial]) -> None:
        asked = [record.external_id for record in records]
        with self._lock:
            self.calls.append(asked)
            self.ran.extend(asked)
        if self.call_cost_usd:
            session.add(
                LlmUsage(
                    purpose=self.name,
                    model="synthetic-model",
                    input_tokens=40 * len(records),
                    output_tokens=0,
                    cost_usd=self.call_cost_usd,
                    created_at=NOW,
                )
            )
            session.flush()
        if self.unanswered.intersection(asked):
            raise RuntimeError("the model left an item out")

    def run(self, session: Session, record: RegistryTrial, client: Client) -> WorkOutcome:
        self._call(session, [record])
        return WorkOutcome.DONE

    def run_many(
        self, session: Session, records: Sequence[RegistryTrial], client: Client
    ) -> list[WorkOutcome]:
        self._call(session, records)
        return [WorkOutcome.DONE for _ in records]


def same_session(session: Session) -> Callable[[], AbstractContextManager[Session]]:
    """Every "transaction" is the test's own session, which is rolled back after the test."""

    @contextmanager
    def open_session() -> Generator[Session]:
        yield session
        session.flush()

    return open_session


def committed_sessions(engine: Engine) -> Callable[[], AbstractContextManager[Session]]:
    """Real transactions on their own connections, as separate processes would have.
    A test that uses this must clean up with `remove_committed`."""

    @contextmanager
    def open_session() -> Generator[Session]:
        with Session(engine) as session, session.begin():
            yield session

    return open_session


def remove_committed(engine: Engine, *, registry: str, step: str, source: str) -> None:
    with Session(engine) as session, session.begin():
        ids = [
            row.id
            for row in session.query(RegistryTrial).filter(RegistryTrial.registry_name == registry)
        ]
        session.execute(delete(ArticleLead).where(ArticleLead.registry_trial_id.in_(ids)))
        session.execute(delete(WorkEntry).where(WorkEntry.step == step))
        session.execute(delete(RegistryTrial).where(RegistryTrial.registry_name == registry))
        session.execute(delete(SourceAllowanceUse).where(SourceAllowanceUse.source_name == source))
