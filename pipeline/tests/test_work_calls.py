"""The one call policy (work/calls.py), as a registry client meets it: a registry that
asks for a wait, asks for too long a wait, or does not answer. Requests go to `respx`,
and time is the fake clock. Scenario names are from openspec source-clients."""

from datetime import timedelta
from email.utils import format_datetime

import httpx
import pytest
import respx
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import HttpCache
from thenwhat.sources.base import SourceThrottled, SourceUnavailable
from thenwhat.sources.clinicaltrials import API, ClinicalTrials
from thenwhat.work.errors import CannotAsk

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
