"""Each constraint must refuse the row it exists to refuse."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from thenwhat.db.models import (
    Claim,
    Entity,
    EntityMatch,
    EvidenceEvent,
    FailureFlag,
    SourceArticle,
)
from thenwhat.domain import EntityType, EventType, RegulatoryOutcome, TrialState

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def add_claim(session: Session, slug: str = "tooth-regrowth-usag1") -> Claim:
    claim = Claim(slug=slug, headline="h", summary="s", indication="i", vertical="mouth-and-teeth")
    session.add(claim)
    session.flush()
    return claim


def add_entity(session: Session, claim: Claim, **overrides) -> Entity:
    values = {"claim_id": claim.id, "type": EntityType.INTERVENTION, "name": "TRG-035"}
    entity = Entity(**(values | overrides))
    session.add(entity)
    session.flush()
    return entity


def add_match(session: Session, entity: Entity, **overrides) -> EntityMatch:
    values = {
        "entity_id": entity.id,
        "source_name": "clinicaltrials.gov",
        "external_id": "NCT00000001",
        "score": 0.8,
    }
    match = EntityMatch(**(values | overrides))
    session.add(match)
    session.flush()
    return match


def event(claim: Claim, **overrides) -> EvidenceEvent:
    values = {
        "claim_id": claim.id,
        "type": EventType.TRIAL_REGISTERED,
        "event_date": date(2024, 9, 1),
        "source_name": "clinicaltrials.gov",
        "source_url": "https://clinicaltrials.gov/study/NCT00000001",
        "external_id": "NCT00000001",
        "summary": "Trial registered",
        "confidence": 1.0,
        "raw_payload": {"id": "NCT00000001"},
        "fetched_at": NOW,
        "dedupe_key": "clinicaltrials.gov|NCT00000001|trial_registered|",
    }
    return EvidenceEvent(**(values | overrides))


def add_event(session: Session, claim: Claim, **overrides) -> EvidenceEvent:
    row = event(claim, **overrides)
    session.add(row)
    session.flush()
    return row


def violated_constraint(error: IntegrityError) -> str | None:
    """Name of the constraint Postgres reported, so a test proves which rule refused the row."""
    return getattr(getattr(error.orig, "diag", None), "constraint_name", None)


def assert_refused(session: Session, constraint: str) -> None:
    with pytest.raises(IntegrityError) as raised:
        session.flush()
    assert violated_constraint(raised.value) == constraint


# --- claim ---------------------------------------------------------------


def test_duplicate_slug_is_refused(session: Session):
    add_claim(session, "enamel-gel")
    session.add(Claim(slug="enamel-gel", headline="h", summary="s", indication="i", vertical="v"))

    assert_refused(session, "uq_claim_slug")


@pytest.mark.parametrize(
    "slug", ["Tooth-Regrowth", "tooth_regrowth", "-tooth", "tooth--regrowth", "a" * 61]
)
def test_malformed_slug_is_refused(session: Session, slug: str):
    session.add(Claim(slug=slug, headline="h", summary="s", indication="i", vertical="v"))

    assert_refused(session, "ck_claim_slug_format")


def test_sixty_character_slug_is_accepted(session: Session):
    add_claim(session, "a" * 60)


# --- source article ------------------------------------------------------


def article(claim: Claim, url: str = "https://example.org/a") -> SourceArticle:
    return SourceArticle(
        claim_id=claim.id, url=url, outlet="o", title="t", published_date=date(2018, 3, 10)
    )


def test_duplicate_article_url_on_one_claim_is_refused(session: Session):
    claim = add_claim(session)
    session.add(article(claim))
    session.flush()
    session.add(article(claim))

    assert_refused(session, "uq_source_article_claim_url")


def test_same_article_url_on_two_claims_is_accepted(session: Session):
    session.add(article(add_claim(session, "claim-one")))
    session.add(article(add_claim(session, "claim-two")))

    session.flush()


# --- entity --------------------------------------------------------------


def test_second_origin_paper_is_refused(session: Session):
    claim = add_claim(session)
    add_entity(session, claim, type=EntityType.PAPER, name="first", is_origin_paper=True)
    session.add(
        Entity(claim_id=claim.id, type=EntityType.PAPER, name="second", is_origin_paper=True)
    )

    assert_refused(session, "uq_entity_origin_paper_per_claim")


def test_origin_paper_on_each_of_two_claims_is_accepted(session: Session):
    for slug in ("claim-one", "claim-two"):
        add_entity(session, add_claim(session, slug), type=EntityType.PAPER, is_origin_paper=True)


def test_origin_paper_that_is_not_a_paper_is_refused(session: Session):
    claim = add_claim(session)
    session.add(Entity(claim_id=claim.id, type=EntityType.COMPANY, name="c", is_origin_paper=True))

    assert_refused(session, "ck_entity_origin_paper_is_paper")


# --- entity match --------------------------------------------------------


def test_duplicate_match_is_refused(session: Session):
    entity = add_entity(session, add_claim(session))
    add_match(session, entity)
    session.add(
        EntityMatch(
            entity_id=entity.id,
            source_name="clinicaltrials.gov",
            external_id="NCT00000001",
            score=0.1,
        )
    )

    assert_refused(session, "uq_entity_match_entity_source_external")


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_match_score_outside_zero_to_one_is_refused(session: Session, score: float):
    entity = add_entity(session, add_claim(session))
    session.add(EntityMatch(entity_id=entity.id, source_name="s", external_id="x", score=score))

    assert_refused(session, "ck_entity_match_score_range")


# --- evidence event ------------------------------------------------------


def test_duplicate_dedupe_key_on_one_claim_is_refused(session: Session):
    claim = add_claim(session)
    add_event(session, claim)
    session.add(event(claim))

    assert_refused(session, "uq_evidence_event_claim_dedupe")


def test_same_dedupe_key_on_two_claims_is_accepted(session: Session):
    add_event(session, add_claim(session, "claim-one"))
    add_event(session, add_claim(session, "claim-two"))


@pytest.mark.parametrize("source_url", ["", "   "])
def test_event_without_source_url_is_refused(session: Session, source_url: str):
    session.add(event(add_claim(session), source_url=source_url))

    assert_refused(session, "ck_evidence_event_source_url_present")


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_event_confidence_outside_zero_to_one_is_refused(session: Session, confidence: float):
    session.add(event(add_claim(session), confidence=confidence))

    assert_refused(session, "ck_evidence_event_confidence_range")


def test_status_change_without_state_is_refused(session: Session):
    session.add(event(add_claim(session), type=EventType.TRIAL_STATUS_CHANGE))

    assert_refused(session, "ck_evidence_event_status_change_has_state")


def test_state_on_an_event_that_is_not_a_status_change_is_refused(session: Session):
    session.add(event(add_claim(session), trial_state=TrialState.STARTED))

    assert_refused(session, "ck_evidence_event_status_change_has_state")


def test_status_change_with_state_is_accepted(session: Session):
    add_event(
        session,
        add_claim(session),
        type=EventType.TRIAL_STATUS_CHANGE,
        trial_state=TrialState.STARTED,
    )


def test_regulatory_decision_without_outcome_is_refused(session: Session):
    session.add(event(add_claim(session), type=EventType.REGULATORY_DECISION))

    assert_refused(session, "ck_evidence_event_regulatory_decision_has_outcome")


def test_outcome_on_an_event_that_is_not_a_regulatory_decision_is_refused(session: Session):
    session.add(event(add_claim(session), regulatory_outcome=RegulatoryOutcome.APPROVED))

    assert_refused(session, "ck_evidence_event_regulatory_decision_has_outcome")


@pytest.mark.parametrize("outcome", list(RegulatoryOutcome))
def test_regulatory_decision_with_outcome_is_accepted(session: Session, outcome: RegulatoryOutcome):
    add_event(
        session,
        add_claim(session),
        type=EventType.REGULATORY_DECISION,
        regulatory_outcome=outcome,
    )


# --- failure flag --------------------------------------------------------


def flag(claim: Claim, evidence: EvidenceEvent, source_url: str = "https://example.org/r"):
    return FailureFlag(
        claim_id=claim.id,
        trial_external_id="NCT00000001",
        evidence_event_id=evidence.id,
        source_url=source_url,
    )


def test_failure_flag_without_source_url_is_refused(session: Session):
    claim = add_claim(session)
    session.add(flag(claim, add_event(session, claim), source_url=""))

    assert_refused(session, "ck_failure_flag_source_url_present")


def test_second_failure_flag_for_one_trial_is_refused(session: Session):
    claim = add_claim(session)
    evidence = add_event(session, claim)
    session.add(flag(claim, evidence))
    session.flush()
    session.add(flag(claim, evidence))

    assert_refused(session, "uq_failure_flag_claim_trial")


# --- review columns ------------------------------------------------------

REVIEWED_TABLES = ["claim", "entity_match", "evidence_event"]


@pytest.fixture
def reviewed_rows(session: Session) -> None:
    """One pending row in every table that has review columns."""
    claim = add_claim(session)
    match = add_match(session, add_entity(session, claim))
    add_event(session, claim, entity_match_id=match.id)


@pytest.mark.parametrize("table", REVIEWED_TABLES)
def test_unknown_review_state_is_refused(session: Session, reviewed_rows: None, table: str):
    with pytest.raises(IntegrityError) as raised:
        # Time and decider are set so that only the state value itself is at fault.
        session.execute(
            text(
                f"UPDATE {table} SET review_state = 'maybe', reviewed_at = now(),"
                " reviewed_by = 'human'"
            )
        )

    assert violated_constraint(raised.value) == f"ck_{table}_review_state"


@pytest.mark.parametrize("table", REVIEWED_TABLES)
@pytest.mark.parametrize(
    "assignment",
    [
        "review_state = 'approved'",
        "review_state = 'approved', reviewed_at = now()",
        "review_state = 'approved', reviewed_by = 'human'",
        "reviewed_at = now(), reviewed_by = 'human'",
    ],
)
def test_decision_without_time_and_decider_is_refused(
    session: Session, reviewed_rows: None, table: str, assignment: str
):
    with pytest.raises(IntegrityError) as raised:
        session.execute(text(f"UPDATE {table} SET {assignment}"))

    assert violated_constraint(raised.value) == f"ck_{table}_review_decision_recorded"


@pytest.mark.parametrize("table", REVIEWED_TABLES)
@pytest.mark.parametrize("decider", ["human", "rule"])
def test_recorded_decision_is_accepted(
    session: Session, reviewed_rows: None, table: str, decider: str
):
    session.execute(
        text(
            f"UPDATE {table} SET review_state = 'rejected', reviewed_at = now(),"
            " reviewed_by = :decider"
        ),
        {"decider": decider},
    )
