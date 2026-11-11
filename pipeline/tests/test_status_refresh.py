"""Stored status, tested through `refresh_status` against the real database."""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from thenwhat.claims.status import refresh_status
from thenwhat.db.models import Claim, Entity, EntityMatch, EvidenceEvent, FailureFlag
from thenwhat.domain import (
    ClaimStatus,
    Decider,
    EntityType,
    EventType,
    RegulatoryOutcome,
    ReviewState,
    TrialPhase,
    TrialState,
)

FIRST_CHECK = datetime(2021, 1, 1, 9, 0, tzinfo=UTC)
SECOND_CHECK = datetime(2021, 2, 1, 9, 0, tzinfo=UTC)
ORIGIN_DOI = "10.1000/origin"


def add_claim(session: Session) -> Claim:
    claim = Claim(
        slug="tooth-regrowth-usag1",
        headline="h",
        summary="s",
        indication="i",
        vertical="dental-regeneration",
        first_reported_date=date(2019, 1, 1),
    )
    session.add(claim)
    session.flush()
    return claim


def add_event(
    session: Session,
    claim: Claim,
    type: EventType,
    on: date,
    *,
    external_id: str = "NCT1",
    approved: bool = True,
    **details,
) -> EvidenceEvent:
    state = details.get("trial_state") or details.get("regulatory_outcome") or ""
    event = EvidenceEvent(
        claim_id=claim.id,
        type=type,
        event_date=on,
        source_name="test",
        source_url="https://example.org/source",
        external_id=external_id,
        summary="s",
        confidence=1.0,
        raw_payload={},
        fetched_at=FIRST_CHECK,
        dedupe_key=f"test|{external_id}|{type}|{state}",
        **details,
    )
    if approved:
        event.review_state = ReviewState.APPROVED
        event.reviewed_at = FIRST_CHECK
        event.reviewed_by = Decider.HUMAN
    session.add(event)
    session.flush()
    return event


def add_started_phase_1_trial(session: Session, claim: Claim) -> list[EvidenceEvent]:
    phases = [TrialPhase.PHASE_1.value]
    return [
        add_event(
            session, claim, EventType.TRIAL_REGISTERED, date(2020, 1, 1), trial_phases=phases
        ),
        add_event(
            session,
            claim,
            EventType.TRIAL_STATUS_CHANGE,
            date(2020, 3, 1),
            trial_phases=phases,
            trial_state=TrialState.STARTED,
        ),
    ]


def add_origin_paper(session: Session, claim: Claim, *, match_approved: bool) -> None:
    paper = Entity(claim_id=claim.id, type=EntityType.PAPER, name="p", is_origin_paper=True)
    session.add(paper)
    session.flush()
    match = EntityMatch(
        entity_id=paper.id, source_name="crossref", external_id=ORIGIN_DOI, score=1.0
    )
    if match_approved:
        match.review_state = ReviewState.APPROVED
        match.reviewed_at = FIRST_CHECK
        match.reviewed_by = Decider.HUMAN
    session.add(match)
    session.flush()


def refresh(session: Session, claim: Claim, now: datetime = FIRST_CHECK, **inputs):
    inputs.setdefault("as_of", now.date())
    return refresh_status(session, claim, now=now, **inputs)


# --- when the stored status changes ----------------------------------------


def test_rederivation_with_no_change_keeps_the_status_updated_time(session: Session):
    """Scenario: Re-derivation with no change"""
    claim = add_claim(session)
    add_started_phase_1_trial(session, claim)
    refresh(session, claim, FIRST_CHECK)

    refresh(session, claim, SECOND_CHECK)

    assert claim.current_status is ClaimStatus.PHASE_1
    assert claim.status_updated_at == FIRST_CHECK


def test_new_status_is_stored_with_the_time_of_the_change(session: Session):
    claim = add_claim(session)
    refresh(session, claim, FIRST_CHECK)
    add_started_phase_1_trial(session, claim)

    refresh(session, claim, SECOND_CHECK)

    assert claim.current_status is ClaimStatus.PHASE_1
    assert claim.status_updated_at == SECOND_CHECK


def test_claim_whose_status_never_changed_has_no_status_updated_time(session: Session):
    claim = add_claim(session)

    refresh(session, claim)

    assert claim.current_status is ClaimStatus.PRECLINICAL_ONLY
    assert claim.status_updated_at is None


def test_overlay_appearing_counts_as_a_change(session: Session):
    claim = add_claim(session)
    add_started_phase_1_trial(session, claim)
    refresh(session, claim, FIRST_CHECK)
    quiet_for_three_years = datetime(2023, 3, 1, 9, 0, tzinfo=UTC)

    refresh(session, claim, quiet_for_three_years)

    assert (claim.current_status, claim.overlay_years) == (ClaimStatus.PHASE_1, 3)
    assert claim.status_updated_at == quiet_for_three_years


def test_refresh_returns_the_events_that_explain_the_status(session: Session):
    claim = add_claim(session)
    trial_events = add_started_phase_1_trial(session, claim)

    derivation = refresh(session, claim)

    assert derivation.explaining_event_ids == tuple(event.id for event in trial_events)


# --- what is read from the database ----------------------------------------


def test_pending_events_are_not_read(session: Session):
    claim = add_claim(session)
    add_started_phase_1_trial(session, claim)
    add_event(
        session,
        claim,
        EventType.TRIAL_STATUS_CHANGE,
        date(2020, 9, 1),
        approved=False,
        trial_state=TrialState.TERMINATED,
    )

    refresh(session, claim)

    assert claim.current_status is ClaimStatus.PHASE_1


def test_events_of_other_claims_are_not_read(session: Session):
    claim = add_claim(session)
    other = Claim(slug="other-claim", headline="h", summary="s", indication="i", vertical="v")
    session.add(other)
    session.flush()
    add_started_phase_1_trial(session, other)

    refresh(session, claim)

    assert claim.current_status is ClaimStatus.PRECLINICAL_ONLY


def test_failure_flag_is_read(session: Session):
    claim = add_claim(session)
    add_started_phase_1_trial(session, claim)
    results = add_event(session, claim, EventType.TRIAL_RESULTS_POSTED, date(2020, 12, 1))
    session.add(
        FailureFlag(
            claim_id=claim.id,
            trial_external_id="NCT1",
            evidence_event_id=results.id,
            source_url="https://example.org/results",
        )
    )
    session.flush()

    refresh(session, claim)

    assert claim.current_status is ClaimStatus.FAILED


def test_regulatory_approval_is_read(session: Session):
    claim = add_claim(session)
    add_event(
        session,
        claim,
        EventType.REGULATORY_DECISION,
        date(2020, 6, 1),
        external_id="regulator/notice-1",
        regulatory_outcome=RegulatoryOutcome.APPROVED,
    )

    refresh(session, claim)

    assert claim.current_status is ClaimStatus.APPROVED


def test_retraction_of_the_origin_paper_is_read_through_its_approved_match(session: Session):
    claim = add_claim(session)
    add_origin_paper(session, claim, match_approved=True)
    add_event(session, claim, EventType.RETRACTION, date(2020, 6, 1), external_id=ORIGIN_DOI)

    refresh(session, claim)

    assert claim.current_status is ClaimStatus.RETRACTED


def test_unapproved_origin_paper_match_does_not_identify_the_origin_paper(session: Session):
    claim = add_claim(session)
    add_origin_paper(session, claim, match_approved=False)
    add_event(session, claim, EventType.RETRACTION, date(2020, 6, 1), external_id=ORIGIN_DOI)

    refresh(session, claim)

    assert claim.current_status is ClaimStatus.PRECLINICAL_ONLY


def test_no_signal_threshold_is_passed_through(session: Session):
    claim = add_claim(session)
    add_started_phase_1_trial(session, claim)

    refresh(session, claim, datetime(2022, 3, 1, 9, 0, tzinfo=UTC), no_signal_years=2)

    assert claim.overlay_years == 2
