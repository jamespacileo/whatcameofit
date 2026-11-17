"""The named sets of stored trials, selected from rows built in the test database.
Scenario names are from openspec registry-corpus."""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backfill_support import NOW
from thenwhat.backfill.trial_sets import (
    active_since_2025,
    completed_with_results_since_2025,
    count_sets,
)
from thenwhat.db.models import RegistryTrial


def trial(session: Session, external_id: str, **fields: Any) -> RegistryTrial:
    defaults: dict[str, Any] = {
        "registry_name": "demo-registry",
        "external_id": external_id,
        "title": f"Trial {external_id}",
        "conditions": ["condition"],
        "interventions": [],
        "phases": ["PHASE3"],
        "overall_status": "RECRUITING",
        "last_update_posted": date(2025, 6, 1),
        "has_results": False,
        "raw_payload": {},
        "fetched_at": NOW,
    }
    row = RegistryTrial(**(defaults | fields))
    session.add(row)
    session.flush()
    return row


def in_set(session: Session, rule) -> list[str]:
    return list(
        session.scalars(
            select(RegistryTrial.external_id).where(rule()).order_by(RegistryTrial.external_id)
        )
    )


def test_active_since_2025_is_phase_2_or_3_under_way_and_updated_since(session: Session):
    trial(session, "A1", phases=["PHASE2"], overall_status="RECRUITING")
    trial(session, "A2", phases=["PHASE2", "PHASE3"], overall_status="ACTIVE_NOT_RECRUITING")
    trial(session, "A3", overall_status="NOT_YET_RECRUITING", last_update_posted=date(2025, 1, 1))
    trial(session, "A4", overall_status="ENROLLING_BY_INVITATION")
    trial(session, "X1", phases=["PHASE1"])
    trial(session, "X2", last_update_posted=date(2024, 12, 31))
    trial(session, "X3", overall_status="COMPLETED")
    # Loaded before the wider record: no update date, so in no set.
    trial(session, "X4", last_update_posted=None)

    assert in_set(session, active_since_2025) == ["A1", "A2", "A3", "A4"]


def test_completed_with_results_since_2025_needs_an_actual_date_and_posted_results(
    session: Session,
):
    """Scenario: A completed trial without results"""
    completed = {"overall_status": "COMPLETED", "completion_date_type": "ACTUAL"}
    trial(session, "C1", **completed, completion_date="2025-06", has_results=True)
    trial(session, "C2", **completed, completion_date="2026-02-14", has_results=True)
    trial(session, "C3", **completed, completion_date="2025", has_results=True)
    # Completed in 2026, but no results posted.
    trial(session, "X1", **completed, completion_date="2026-01-10", has_results=False)
    # Completion date anticipated, not actual.
    trial(
        session,
        "X2",
        overall_status="COMPLETED",
        completion_date="2025-08",
        completion_date_type="ESTIMATED",
        has_results=True,
    )
    trial(session, "X3", **completed, completion_date="2024-12", has_results=True)
    trial(session, "X4", **completed, completion_date="2024-12-31", has_results=True)
    trial(
        session,
        "X5",
        overall_status="TERMINATED",
        completion_date="2025-03",
        completion_date_type="ACTUAL",
        has_results=True,
    )
    trial(session, "X6", **completed, completion_date=None, has_results=True)

    assert in_set(session, completed_with_results_since_2025) == ["C1", "C2", "C3"]
    assert "X1" not in in_set(session, active_since_2025)


def test_counting_the_sets_by_phase_with_the_day_they_were_loaded(session: Session):
    """Scenario: Counting the sets"""
    trial(session, "A1", phases=["PHASE2"])
    trial(session, "A2", phases=["PHASE2", "PHASE3"])
    trial(session, "A3", phases=["PHASE3"])
    trial(session, "A4", phases=["PHASE3"])
    trial(
        session,
        "C1",
        phases=[],
        overall_status="COMPLETED",
        completion_date="2025-06",
        completion_date_type="ACTUAL",
        has_results=True,
    )
    trial(session, "OLD", last_update_posted=None)

    report = count_sets(session)

    active, completed = report.sets
    assert (active.name, active.total) == ("active-since-2025", 4)
    assert active.by_phase == {("PHASE2",): 1, ("PHASE2", "PHASE3"): 1, ("PHASE3",): 2}
    assert active.loaded_first == active.loaded_last == NOW.date()
    assert (completed.name, completed.total, completed.by_phase) == (
        "completed-with-results-since-2025",
        1,
        {(): 1},
    )
    assert (report.stored, report.without_wider_record) == (6, 1)
