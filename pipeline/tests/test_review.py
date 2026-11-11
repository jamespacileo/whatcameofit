"""Review, tested through the functions of `thenwhat.review.queue` on a real database.

Scenario names are from openspec review.
"""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.claims.entry import EntryError, InvalidUrl, add_article, add_claim, edit_claim
from thenwhat.db.models import Claim, DecisionLog, EntityMatch, EvidenceEvent, FailureFlag
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import suggest_evidence_stage
from thenwhat.domain import (
    ClaimStatus,
    Decider,
    EventType,
    EvidenceStage,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.events.manual import add_manual_event
from thenwhat.resolve.service import resolve_claim
from thenwhat.review.decisions import record_decision
from thenwhat.review.queue import (
    ItemNotFound,
    Kind,
    confirm_stage,
    decide_item,
    flag_failure,
    pending_items,
)
from thenwhat.sources.base import SourceRecord

EARLIER = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
SLUG = "tooth-regrowth-ex1"
ARTICLE = "https://news.example.org/2018/teeth"
REGISTRY = "https://registry.example/NCT1"


class Backend:
    """Scores every candidate as a likely match and suggests one evidence stage."""

    name = "fake"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        choice = "match" if step == "entity_match" else "early_human"
        rest = 0.2 / (len(options) - 1)
        return BackendAnswer(choice, {o: 0.8 if o == choice else rest for o in options})


class Trials:
    def __init__(self, *nct_ids: str) -> None:
        self.nct_ids = nct_ids

    def search_trials(self, intervention: str) -> list[SourceRecord]:
        return [
            SourceRecord("clinicaltrials.gov", i, f"https://clinicaltrials.gov/study/{i}", {}, NOW)
            for i in self.nct_ids
        ]


class NoDois:
    def work(self, doi: str) -> None:
        return None


def new_claim(session: Session, slug: str = SLUG, **overrides: Any) -> Claim:
    values: dict[str, Any] = {
        "slug": slug,
        "headline": "Antibody regrows teeth in mice",
        "vertical": "dental-regeneration",
        "intervention": f"EX-1 antibody {slug}",
        "indication": "tooth agenesis",
        "summary": "An antibody restored missing teeth in mice.",
    }
    claim = add_claim(session, **(values | overrides))
    add_article(
        session,
        slug,
        url=ARTICLE,
        outlet="Example News",
        title="t",
        published_date=date(2018, 3, 10),
    )
    return claim


def approved_claim(session: Session, slug: str = SLUG) -> Claim:
    claim = new_claim(session, slug)
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=EARLIER)
    session.flush()
    return claim


def candidates(session: Session, claim: Claim, *nct_ids: str) -> list[EntityMatch]:
    return resolve_claim(
        session, claim, trials=Trials(*nct_ids), dois=NoDois(), backend=Backend(), now=EARLIER
    )


def trial_event(session: Session, slug: str = SLUG, **overrides: Any) -> EvidenceEvent:
    values: dict[str, Any] = {
        "type": EventType.TRIAL_REGISTERED,
        "event_date": date(2024, 9, 1),
        "source_url": REGISTRY,
        "summary": "Phase 1 trial registered.",
        "external_id": "NCT1",
        "trial_phases": [TrialPhase.PHASE_1],
    }
    return add_manual_event(session, slug, now=EARLIER, **(values | overrides))


def started_event(session: Session, **overrides: Any) -> EvidenceEvent:
    return trial_event(
        session,
        type=EventType.TRIAL_STATUS_CHANGE,
        trial_state=TrialState.STARTED,
        event_date=date(2024, 10, 1),
        summary="Trial started.",
        **overrides,
    )


def approve(session: Session, kind: Kind, item) -> None:
    decide_item(session, kind, item.id, ReviewState.APPROVED, now=NOW)


# --- decisions -------------------------------------------------------------------


def test_operator_approval_records_the_time_and_a_human_decider(session: Session):
    """Scenario: Operator approves a match"""
    [match] = candidates(session, approved_claim(session), "NCT1")

    decide_item(session, "match", match.id, ReviewState.APPROVED, now=NOW)

    assert (match.review_state, match.reviewed_at, match.reviewed_by) == (
        ReviewState.APPROVED,
        NOW,
        Decider.HUMAN,
    )


def test_rejected_event_is_kept(session: Session):
    """Scenario: Rejected event"""
    approved_claim(session)
    event = trial_event(session)

    decide_item(session, "event", event.id, ReviewState.REJECTED, now=NOW)

    assert session.get(EvidenceEvent, event.id) is event
    assert event.review_state is ReviewState.REJECTED


def test_rule_approved_event_can_be_rejected_by_the_operator(session: Session):
    """Scenario: Rule-approved event found to be wrong"""
    approved_claim(session)
    event = trial_event(session)
    record_decision(event, ReviewState.APPROVED, by=Decider.RULE, now=EARLIER)

    decide_item(session, "event", event.id, ReviewState.REJECTED, now=NOW)

    assert (event.review_state, event.reviewed_by, event.reviewed_at) == (
        ReviewState.REJECTED,
        Decider.HUMAN,
        NOW,
    )


def test_draft_claim_can_be_approved(session: Session):
    claim = new_claim(session)

    decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=NOW)

    assert claim.review_state is ReviewState.APPROVED


def test_draft_claim_without_a_summary_cannot_be_approved(session: Session):
    claim = new_claim(session, summary="")

    with pytest.raises(EntryError, match="summary"):
        decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=NOW)

    edit_claim(session, claim.slug, summary="Now it has one.")
    decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=NOW)
    assert claim.review_state is ReviewState.APPROVED


def test_unknown_item_is_refused(session: Session):
    with pytest.raises(ItemNotFound):
        decide_item(session, "event", 999_999, ReviewState.APPROVED, now=NOW)


# --- status follows review ---------------------------------------------------------


def test_approving_a_started_event_moves_the_claim_to_its_phase(session: Session):
    """Scenario: Approving a started event"""
    claim = approved_claim(session)
    approve(session, "event", trial_event(session))
    assert claim.current_status is ClaimStatus.TRIAL_REGISTERED

    approve(session, "event", started_event(session))

    assert claim.current_status is ClaimStatus.PHASE_1
    assert claim.status_updated_at == NOW


def test_rejecting_an_approved_event_takes_it_out_of_the_status(session: Session):
    claim = approved_claim(session)
    registered = trial_event(session)
    approve(session, "event", registered)

    decide_item(session, "event", registered.id, ReviewState.REJECTED, now=NOW)

    assert claim.current_status is ClaimStatus.PRECLINICAL_ONLY


def test_rejecting_a_match_rejects_the_events_that_came_from_it(session: Session):
    claim = approved_claim(session)
    [match] = candidates(session, claim, "NCT1")
    approve(session, "match", match)
    event = trial_event(session)
    event.entity_match_id = match.id
    record_decision(event, ReviewState.APPROVED, by=Decider.RULE, now=EARLIER)
    session.flush()

    decide_item(session, "match", match.id, ReviewState.REJECTED, now=NOW)

    assert (event.review_state, event.reviewed_by) == (ReviewState.REJECTED, Decider.HUMAN)
    assert claim.current_status is ClaimStatus.PRECLINICAL_ONLY


# --- queue ---------------------------------------------------------------------------


def test_queue_for_one_claim_lists_its_pending_items_with_source_links(session: Session):
    """Scenario: Queue for one claim"""
    claim = approved_claim(session)
    candidates(session, claim, "NCT1", "NCT2")
    trial_event(session)
    started_event(session)
    trial_event(session, external_id="NCT9", source_url="https://registry.example/NCT9")
    other = approved_claim(session, "other-claim")
    candidates(session, other, "NCT7")

    items = pending_items(session, claim_slug=SLUG)

    assert [item.kind for item in items] == ["match", "match", "event", "event", "event"]
    assert all(item.claim_slug == SLUG and item.source_url for item in items)
    assert items[0].source_url == "https://clinicaltrials.gov/study/NCT1"
    assert items[0].score == pytest.approx(0.8)
    assert "EX-1 antibody" in items[0].assertion and "NCT1" in items[0].assertion
    assert "Phase 1 trial registered." in items[2].assertion


def test_queue_for_all_claims_includes_draft_claims(session: Session):
    draft = new_claim(session)
    candidates(session, approved_claim(session, "other-claim"), "NCT7")

    items = pending_items(session)

    assert [(item.kind, item.claim_slug) for item in items] == [
        ("claim", SLUG),
        ("match", "other-claim"),
    ]
    assert items[0].id == draft.id and items[0].source_url == ARTICLE


def test_queue_can_be_narrowed_to_one_kind(session: Session):
    claim = approved_claim(session)
    candidates(session, claim, "NCT1")
    trial_event(session)

    assert [item.kind for item in pending_items(session, kind="event")] == ["event"]


def test_decided_items_leave_the_queue(session: Session):
    claim = approved_claim(session)
    [match] = candidates(session, claim, "NCT1")

    decide_item(session, "match", match.id, ReviewState.REJECTED, now=NOW)

    assert pending_items(session) == []


def test_empty_queue_is_empty(session: Session):
    """Scenario: Empty queue"""
    approved_claim(session)

    assert pending_items(session) == []


# --- failure flag --------------------------------------------------------------------


def results_posted(session: Session) -> EvidenceEvent:
    event = trial_event(
        session,
        type=EventType.TRIAL_RESULTS_POSTED,
        event_date=date(2026, 1, 15),
        summary="Results posted.",
    )
    approve(session, "event", event)
    return event


def claim_with_a_completed_trial(session: Session) -> Claim:
    claim = approved_claim(session)
    approve(session, "event", trial_event(session))
    approve(session, "event", started_event(session))
    return claim


def test_flag_with_a_source_marks_the_trial_failed(session: Session):
    """Scenario: Flag with a source"""
    claim = claim_with_a_completed_trial(session)
    results = results_posted(session)

    flag = flag_failure(
        session,
        SLUG,
        trial_id="NCT1",
        event_id=results.id,
        source_url="https://registry.example/NCT1/results",
        now=NOW,
    )

    assert (flag.trial_external_id, flag.evidence_event_id) == ("NCT1", results.id)
    assert claim.current_status is ClaimStatus.FAILED


@pytest.mark.parametrize("source_url", ["", "see the paper"])
def test_flag_without_a_source_is_refused(session: Session, source_url: str):
    """Scenario: Flag without a source"""
    claim = claim_with_a_completed_trial(session)
    results = results_posted(session)

    with pytest.raises(InvalidUrl):
        flag_failure(
            session, SLUG, trial_id="NCT1", event_id=results.id, source_url=source_url, now=NOW
        )

    assert session.scalars(select(FailureFlag)).all() == []
    assert claim.current_status is ClaimStatus.PHASE_1


def test_results_posted_without_a_flag_leaves_the_trial_unflagged(session: Session):
    """Scenario: Results posted without a flag"""
    claim = claim_with_a_completed_trial(session)

    results_posted(session)

    assert session.scalars(select(FailureFlag)).all() == []
    assert claim.current_status is ClaimStatus.PHASE_1


def test_flag_must_rest_on_an_approved_event_of_the_same_claim(session: Session):
    claim_with_a_completed_trial(session)
    pending = trial_event(session, type=EventType.TRIAL_RESULTS_POSTED, summary="Results posted.")

    with pytest.raises(EntryError, match="approved"):
        flag_failure(
            session, SLUG, trial_id="NCT1", event_id=pending.id, source_url=REGISTRY, now=NOW
        )


# --- human labels --------------------------------------------------------------------


def labels(session: Session, step: str) -> list[str | None]:
    query = select(DecisionLog).where(DecisionLog.step == step).order_by(DecisionLog.id)
    return [entry.human_label for entry in session.scalars(query)]


def test_rejecting_a_scored_match_labels_the_suggestion_not_a_match(session: Session):
    """Scenario: Match scored by a decision step"""
    [match] = candidates(session, approved_claim(session), "NCT1")
    assert labels(session, "entity_match") == [None]

    decide_item(session, "match", match.id, ReviewState.REJECTED, now=NOW)

    assert labels(session, "entity_match") == ["not_a_match"]


def test_approving_a_scored_match_labels_the_suggestion_match(session: Session):
    [match] = candidates(session, approved_claim(session), "NCT1")

    decide_item(session, "match", match.id, ReviewState.APPROVED, now=NOW)

    assert labels(session, "entity_match") == ["match"]


def test_operator_correcting_the_suggested_stage_sets_stage_and_label(session: Session):
    """Scenario: Operator corrects the suggestion"""
    claim = approved_claim(session)
    suggestion = suggest_evidence_stage(session, Backend(), claim, now=EARLIER)
    assert suggestion.choice == "early_human" and claim.evidence_stage is None

    confirm_stage(session, SLUG, EvidenceStage.ANIMAL)

    assert claim.evidence_stage is EvidenceStage.ANIMAL
    assert labels(session, "evidence_stage") == ["animal"]


def test_stage_can_be_set_when_nothing_was_suggested(session: Session):
    claim = approved_claim(session)

    confirm_stage(session, SLUG, EvidenceStage.IN_VITRO)

    assert claim.evidence_stage is EvidenceStage.IN_VITRO
    assert entities_of(session, claim)  # the claim is otherwise untouched
