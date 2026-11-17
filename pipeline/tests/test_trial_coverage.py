"""The coverage report for the trial target set, counted from synthetic rows in the
test database. Scenario names are from openspec trial-coverage (change
trial-first-route)."""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from backfill_support import NOW
from thenwhat.backfill.trial_coverage import coverage_of
from thenwhat.claims.entry import add_claim
from thenwhat.db.models import RegistryTrial, TrialPaper
from thenwhat.domain import EventType, ReviewState, TrialPhase
from thenwhat.events.manual import add_manual_event
from thenwhat.review.queue import decide_item

LISTS_A_RESULT = {
    "protocolSection": {"referencesModule": {"references": [{"pmid": "111", "type": "RESULT"}]}}
}
LISTS_BACKGROUND = {
    "protocolSection": {"referencesModule": {"references": [{"pmid": "222", "type": "BACKGROUND"}]}}
}


def trial(session: Session, external_id: str, **fields: Any) -> RegistryTrial:
    defaults: dict[str, Any] = {
        "registry_name": "clinicaltrials.gov",
        "external_id": external_id,
        "title": f"Synthetic study {external_id}",
        "conditions": ["Synthetic condition"],
        "interventions": [],
        "phases": ["PHASE1"],
        "overall_status": "RECRUITING",
        "last_update_posted": date(2026, 3, 1),
        "has_results": False,
        "raw_payload": {},
        "fetched_at": NOW,
    }
    row = RegistryTrial(**(defaults | fields))
    session.add(row)
    session.flush()
    return row


def paper_for(session: Session, row: RegistryTrial, pubmed_id: str) -> None:
    session.add(
        TrialPaper(
            registry_trial_id=row.id,
            source_name="pubmed",
            pubmed_id=pubmed_id,
            raw_payload={"pmid": pubmed_id},
            fetched_at=NOW,
        )
    )
    session.flush()


def claim_citing(session: Session, slug: str, external_id: str, approve: bool = True) -> None:
    claim = add_claim(
        session,
        slug=slug,
        headline="A synthetic treatment was reported",
        vertical="mouth-and-teeth",
        intervention=f"EX-1 {slug}",
        indication="synthetic condition",
        summary="A synthetic summary.",
    )
    decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=NOW)
    event = add_manual_event(
        session,
        slug,
        now=NOW,
        type=EventType.TRIAL_REGISTERED,
        event_date=date(2025, 9, 1),
        source_url=f"https://clinicaltrials.gov/study/{external_id}",
        summary="Phase 3 trial registered.",
        external_id=external_id,
        trial_phases=[TrialPhase.PHASE_3],
    )
    if approve:
        decide_item(session, "event", event.id, ReviewState.APPROVED, now=NOW)


def test_the_report_counts_what_is_held_for_each_group_of_the_set(session: Session):
    """Scenario: A coverage report for the set"""
    # Under way: four, one of each thing counted, and one stale record.
    first = trial(session, "NCT00000001", raw_payload=LISTS_A_RESULT)
    paper_for(session, first, "11")
    paper_for(session, first, "12")
    trial(session, "NCT00000002", raw_payload=LISTS_BACKGROUND)
    trial(session, "NCT00000003", last_update_posted=date(2024, 12, 31))
    trial(session, "NCT00000004", overall_status="ACTIVE_NOT_RECRUITING")
    claim_citing(session, "cites-two", "NCT00000002")
    claim_citing(session, "pending-event", "NCT00000004", approve=False)
    # Completed this year: two, one with results and a paper found by number.
    done = trial(
        session,
        "NCT00000005",
        overall_status="COMPLETED",
        completion_date="2026-02-14",
        has_results=True,
    )
    paper_for(session, done, "13")
    trial(session, "NCT00000006", overall_status="COMPLETED", completion_date="2026-05")
    # Terminated, withdrawn or suspended this year: one of each.
    trial(session, "NCT00000007", overall_status="TERMINATED", completion_date="2026-01")
    trial(session, "NCT00000008", overall_status="WITHDRAWN", completion_date="2026-03-01")
    trial(session, "NCT00000009", overall_status="SUSPENDED", completion_date="2026-12")
    # In no group: ended in another year, or with no completion date.
    trial(session, "NCT00000010", overall_status="COMPLETED", completion_date="2025-12-31")
    trial(session, "NCT00000011", overall_status="TERMINATED", completion_date=None)
    claim_citing(session, "cites-outside", "NCT00000010")

    coverage = coverage_of(session, 2026)

    under_way, completed, not_completed = coverage.groups
    assert [group.name for group in coverage.groups] == [
        "under way",
        "completed in 2026",
        "terminated, withdrawn or suspended in 2026",
    ]
    assert (under_way.trials, completed.trials, not_completed.trials) == (4, 2, 3)
    assert (under_way.with_listed_paper, under_way.with_pubmed_paper) == (1, 1)
    assert (under_way.cited_by_published_claim, under_way.with_results) == (1, 0)
    assert under_way.not_updated_since_before_last_year == 1
    assert (completed.with_results, completed.with_pubmed_paper) == (1, 1)
    assert (completed.cited_by_published_claim, completed.with_listed_paper) == (0, 0)
    total = coverage.total
    assert (total.trials, total.with_results, total.with_pubmed_paper) == (9, 1, 2)
    assert (total.with_listed_paper, total.cited_by_published_claim) == (1, 1)


def test_the_set_rolls_with_the_year(session: Session):
    """Scenario: The year turns"""
    trial(session, "NCT00000001")
    trial(session, "NCT00000002", overall_status="COMPLETED", completion_date="2026-06")

    assert coverage_of(session, 2026).total.trials == 2
    assert coverage_of(session, 2027).total.trials == 1
