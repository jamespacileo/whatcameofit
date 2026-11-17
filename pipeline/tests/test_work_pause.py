"""A source's pause and its allowance, kept in the database for every command and every
process (work/pause.py). Requests go to `respx`, time is the fake clock, and the
database is the real test database. Scenario names are from openspec source-clients."""

from datetime import timedelta

import httpx
import pytest
import respx
from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from backfill_support import same_session
from test_registry_corpus import CONDITION, Registry
from thenwhat.backfill.registry_load import load_trials
from thenwhat.config import DEFAULT_ALLOWANCES
from thenwhat.db.models import SourceAllowanceUse
from thenwhat.sources.base import SourceCannotBeAsked, SourceUnavailable
from thenwhat.sources.clinicaltrials import API, ClinicalTrials
from thenwhat.work.allowance import Allowances

CONTACT = "ops@thenwhat.test"
NOTHING_FOUND = {"studies": []}
SLOW_DOWN = httpx.Response(429, headers={"Retry-After": "3600"})


def registry(session: Session, fake_time, **options) -> ClinicalTrials:
    return ClinicalTrials(session, contact_email=CONTACT, time=fake_time, **options)


def test_a_second_command_sends_a_paused_registry_nothing(engine: Engine, fake_time):
    """Scenario: Two commands and one throttled source"""
    try:
        # Two sessions on their own connections, as two processes have.
        with Session(engine) as one, Session(engine) as other, respx.mock:
            route = respx.get(f"{API}/studies").mock(return_value=SLOW_DOWN)
            with pytest.raises(SourceUnavailable):
                registry(one, fake_time).search_trials("tideglusib")
            one.rollback()

            fake_time.advance(timedelta(minutes=1))
            with pytest.raises(SourceCannotBeAsked) as paused:
                registry(other, fake_time).search_trials("tideglusib")
            other.rollback()

        assert route.call_count == 1
        assert "paused until 2026-01-01 13:00 UTC" in str(paused.value)
        assert paused.value.until == fake_time.now() + timedelta(minutes=59)
    finally:
        with Session(engine) as session, session.begin():
            session.execute(
                delete(SourceAllowanceUse).where(
                    SourceAllowanceUse.source_name == ClinicalTrials.name
                )
            )


def test_a_registry_is_asked_as_usual_once_its_pause_has_passed(session: Session, fake_time):
    """Scenario: The pause has passed"""
    with respx.mock:
        route = respx.get(f"{API}/studies").mock(
            side_effect=[SLOW_DOWN, httpx.Response(200, json=NOTHING_FOUND)]
        )
        with pytest.raises(SourceUnavailable):
            registry(session, fake_time).search_trials("tideglusib")

        fake_time.advance(timedelta(hours=1, seconds=1))

        assert registry(session, fake_time).search_trials("tideglusib") == []
    assert route.call_count == 2


def test_preparing_claims_and_a_backfill_count_against_one_allowance(
    session: Session, fake_time, fixture_json
):
    """Scenario: Preparing claims and a backfill share a registry"""
    with respx.mock:
        # The backfill's bulk load of trials: two pages.
        respx.get(f"{API}/studies", params={"filter.advanced": CONDITION}).mock(
            side_effect=Registry(fixture_json)
        )
        load_trials(
            same_session(session),
            registry(session, fake_time),
            [],
            condition=CONDITION,
            changes_only=False,
            now=fake_time.now,
        )
        # A claim's registry search, as `thenwhat prepare` makes it: one page.
        respx.get(f"{API}/studies").mock(return_value=httpx.Response(200, json=NOTHING_FOUND))
        registry(session, fake_time).search_trials("tideglusib")

    allowances = Allowances(same_session(session), DEFAULT_ALLOWANCES, fake_time)
    assert allowances.status(session, ClinicalTrials.name).used == 3


def test_a_pause_recorded_during_pacing_prevents_the_reserved_request(
    session, fake_time, monkeypatch
):
    from thenwhat.work.pause import pause

    monkeypatch.setenv(
        "SOURCE_ALLOWANCES",
        '{"clinicaltrials.gov":{"requests":2,"period_hours":24,"interval_seconds":10}}',
    )
    source = registry(session, fake_time, rate_per_second=0.1)
    until = fake_time.now() + timedelta(hours=1)
    slept = fake_time.sleep

    def record_pause(seconds):
        pause(session, source.name, until, fake_time.now())
        slept(seconds)

    with respx.mock:
        calls = respx.get(f"{API}/studies").mock(
            return_value=httpx.Response(200, json=NOTHING_FOUND)
        )
        source.search_trials("first")
        monkeypatch.setattr(fake_time, "sleep", record_pause)
        with pytest.raises(SourceCannotBeAsked) as refused:
            source.search_trials("next")
        assert fake_time.slept == [10.0]
        assert refused.value.until == until and calls.call_count == 1
        fake_time.advance(until - fake_time.now())
        assert source.search_trials("next") == []
        assert calls.call_count == 2


def test_cancelled_allowance_turn_is_available_after_the_pause(session, fake_time, monkeypatch):
    from thenwhat.config import SourceAllowance
    from thenwhat.work.errors import SourcePaused

    source = "test-provider"
    allowance = SourceAllowance(requests=2, period_hours=24, interval_seconds=10)
    gate = Allowances(same_session(session), {source: allowance}, fake_time)
    gate.claim(source)
    until = fake_time.now() + timedelta(hours=1)
    slept = fake_time.sleep

    def hold(seconds):
        gate.hold(source, until)
        slept(seconds)

    monkeypatch.setattr(fake_time, "sleep", hold)
    with pytest.raises(SourcePaused) as refused:
        gate.claim(source)
    assert refused.value.until == until
    assert gate.status(session, source).used == 1
    fake_time.advance(until - fake_time.now())
    gate.claim(source)
    assert gate.status(session, source).used == 2


def test_cancelled_turn_from_an_earlier_period_keeps_the_new_periods_usage(session, fake_time):
    from thenwhat.config import SourceAllowance
    from thenwhat.work.errors import SourcePaused
    from thenwhat.work.pause import finish_wait

    allowance = SourceAllowance(requests=2, period_hours=1, interval_seconds=0)
    gate = Allowances(same_session(session), {"period-test": allowance}, fake_time)
    reserved_at = fake_time.now()
    gate.claim("period-test")
    fake_time.advance(timedelta(hours=1))
    gate.claim("period-test")
    gate.hold("period-test", fake_time.now() + timedelta(hours=1))
    with pytest.raises(SourcePaused):
        finish_wait(
            same_session(session),
            "period-test",
            reserved_at=reserved_at,
            now=fake_time.now(),
            counted=True,
        )
    assert gate.status(session, "period-test").used == 1
