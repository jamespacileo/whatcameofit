"""The one call policy (work/calls.py), as a registry client meets it: a registry that
asks for a wait, asks for too long a wait, or does not answer; and as a run meets it,
when the model cannot be asked part way. Requests go to `respx` or a scripted model, and
time is the fake clock. Scenario names are from openspec source-clients and, for the
runs, work-ledger."""

from datetime import timedelta
from decimal import Decimal
from email.utils import format_datetime

import httpx
import pytest
import respx
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backfill_support import Client, DemoStep, add_trials, same_session
from thenwhat.db.models import HttpCache, WorkEntry
from thenwhat.decide.core import decide
from thenwhat.decide.llm_backend import LlmBackend
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.sources.base import SourceThrottled, SourceUnavailable
from thenwhat.sources.clinicaltrials import API, ClinicalTrials
from thenwhat.work.errors import CannotAsk
from thenwhat.work.runner import run_step

CONTACT = "ops@thenwhat.test"
NOTHING_FOUND = {"studies": []}


def registry(session: Session, fake_time) -> ClinicalTrials:
    return ClinicalTrials(session, contact_email=CONTACT, time=fake_time)


def test_a_wait_given_as_a_time_is_honoured(session: Session, fake_time):
    """Scenario: A wait given as a time"""
    asked_at = []

    def answer(request: httpx.Request) -> httpx.Response:
        asked_at.append(fake_time.now())
        if len(asked_at) == 1:
            again = format_datetime(fake_time.now() + timedelta(seconds=20), usegmt=True)
            return httpx.Response(429, headers={"Retry-After": again})
        return httpx.Response(200, json=NOTHING_FOUND)

    with respx.mock:
        respx.get(f"{API}/studies").mock(side_effect=answer)

        assert registry(session, fake_time).search_trials("tideglusib") == []

    assert len(asked_at) == 2
    assert asked_at[1] - asked_at[0] >= timedelta(seconds=20)


def test_a_wait_longer_than_the_ceiling_ends_the_fetch_at_once(session: Session, fake_time):
    """Scenario: A wait longer than the ceiling"""
    with respx.mock:
        route = respx.get(f"{API}/studies").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "3600"})
        )

        with pytest.raises(SourceThrottled) as stopped:
            registry(session, fake_time).search_trials("tideglusib")

    assert route.call_count == 1
    assert fake_time.slept == []
    # The caller is told the registry cannot be asked, and for how long.
    assert isinstance(stopped.value, CannotAsk)
    assert stopped.value.until == fake_time.now() + timedelta(hours=1)
    assert "not asked again before 2026-01-01 13:00 UTC" in str(stopped.value)


def test_a_search_while_the_registry_is_down_did_not_run(session: Session, fake_time):
    """Scenario: A search while the registry is down"""
    with respx.mock:
        route = respx.get(f"{API}/studies").mock(return_value=httpx.Response(503))

        # Not an empty list: the caller is told the search did not run.
        with pytest.raises(SourceUnavailable) as stopped:
            registry(session, fake_time).search_trials("tideglusib")

    assert route.call_count > 1
    assert isinstance(stopped.value, CannotAsk)
    assert "did not answer" in str(stopped.value)
    # Nothing records that the search found no trial.
    assert session.scalars(select(HttpCache)).all() == []


# --- a run that meets a model that cannot be asked (openspec work-ledger) ---------------


class Said(BaseModel):
    word: str


def model_answering(calls: int) -> FunctionModel:
    """A model that answers the first `calls` calls, then cannot be reached."""
    made: list[int] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        made.append(1)
        if len(made) > calls:
            raise httpx.ConnectError("synthetic outage")
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"word": "ok"})])

    return FunctionModel(respond, model_name="scripted")


def llm(session: Session, model: FunctionModel, fake_time, budget: str = "10") -> Llm:
    settings = LlmSettings("test:scripted", Decimal(budget), Decimal("3"), Decimal("15"))
    return Llm(session, settings, model=model, now=fake_time.now, time=fake_time)


def entries(session: Session, step: DemoStep) -> list[WorkEntry]:
    return list(session.scalars(select(WorkEntry).where(WorkEntry.step == step.name)))


def test_the_model_going_away_part_way_stops_the_run(session: Session, fake_time):
    """Scenario: The model goes away during a read"""
    add_trials(session, 50)
    model = model_answering(4)
    step = DemoStep()

    def read(record) -> None:
        llm(session, model, fake_time).run(
            "read", instructions="Read.", prompt=record.title, output_type=Said
        )

    step.before = read

    report = run_step(same_session(session), step, Client(), now=fake_time.now, attempt_limit=3)

    assert (report.done, report.failed, report.remaining_due) == (4, 0, 46)
    assert (report.stopped or "").startswith("The language model cannot be asked")
    # Only the four finished records have entries: no attempt counted for the others.
    assert len(entries(session, step)) == 4


def test_the_ceiling_reached_inside_a_decision_stops_the_run(session: Session, fake_time):
    """Scenario: The ceiling is reached inside a decision"""
    add_trials(session, 1)
    step = DemoStep()
    read: list[str] = []

    def read_then_decide(record) -> None:
        # The first call is allowed, and its cost reaches the month's ceiling.
        asked = llm(session, model_answering(1), fake_time, budget="0.000001")
        read.append(
            asked.run("read", instructions="Read.", prompt=record.title, output_type=Said).word
        )
        decide(
            session,
            LlmBackend(asked),
            step="kind",
            state=record.title,
            options=["drug", "device"],
            input_ref=f"trial:{record.id}",
            now=fake_time.now(),
        )

    step.before = read_then_decide

    report = run_step(same_session(session), step, Client(), now=fake_time.now, attempt_limit=3)

    assert read == ["ok"]
    assert (report.processed, report.failed, report.remaining_due) == (0, 0, 1)
    assert "monthly ceiling" in (report.stopped or "")
    assert entries(session, step) == []
