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
