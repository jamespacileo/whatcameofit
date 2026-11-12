"""Suggesting a group from trials' MeSH terms: the pure table, then the claim's line."""

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from thenwhat.claims.entry import add_claim
from thenwhat.claims.mesh_areas import GroupSuggestion, suggest_groups, suggestion_line
from thenwhat.cli import app
from thenwhat.db.models import Claim, Entity, EntityMatch, EvidenceEvent
from thenwhat.domain import Decider, EventType, ReviewState

FIXTURES = Path(__file__).parent / "fixtures" / "clinicaltrials"
NOW = datetime(2026, 11, 12, tzinfo=UTC)


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


def test_trial_pointing_to_one_group():
    assert suggest_groups([fixture("study_NCT02586935.json")]) == [
        GroupSuggestion("mental-health", "Mental Disorders")
    ]


def test_trial_pointing_to_several_groups_lists_each_with_its_term():
    suggestions = suggest_groups([fixture("study_NCT06497504_conditions.json")])

    assert [(s.group, s.mesh_term) for s in suggestions] == [
        ("gut-and-liver", "Digestive System Diseases"),
        ("immune-system-and-allergies", "Immune System Diseases"),
        ("infections", "Infections"),
    ]


def test_no_usable_term_suggests_nothing():
    broad = {
        "derivedSection": {
            "conditionBrowseModule": {
                "meshes": [{"id": "D000375", "term": "Aging"}],
                "ancestors": [{"id": "D012816", "term": "Signs and Symptoms"}],
            }
        }
    }
    assert suggest_groups([broad, {"protocolSection": {}}]) == []


@pytest.fixture
def claim(session: Session) -> Claim:
    return add_claim(
        session,
        slug="hepatitis-b-ex1",
        headline="Drug clears hepatitis B",
        vertical="infections",
        intervention="EX-1",
        indication="Chronic hepatitis B",
    )


def approve_trial(session: Session, claim: Claim, payload: dict[str, Any]) -> None:
    entity = session.scalars(select(Entity).where(Entity.claim_id == claim.id)).one()
    match = EntityMatch(
        entity_id=entity.id,
        source_name="clinicaltrials.gov",
        external_id="NCT06497504",
        score=0.9,
        review_state=ReviewState.APPROVED,
        reviewed_at=NOW,
        reviewed_by=Decider.HUMAN,
    )
    session.add(match)
    session.flush()
    session.add(
        EvidenceEvent(
            claim_id=claim.id,
            entity_match_id=match.id,
            type=EventType.TRIAL_REGISTERED,
            event_date=date(2024, 7, 1),
            source_name="clinicaltrials.gov",
            source_url="https://clinicaltrials.gov/study/NCT06497504",
            external_id="NCT06497504",
            summary="Trial registered.",
            confidence=1.0,
            raw_payload=payload,
            fetched_at=NOW,
            dedupe_key="registered:NCT06497504",
        )
    )
    session.flush()


def test_line_without_approved_trials_says_why(session: Session, claim: Claim):
    assert suggestion_line(session, claim) == (
        "Health area: no suggestion, as no trial match is approved."
    )


def test_review_list_shows_the_suggestion_and_leaves_the_vertical(
    session: Session, claim: Claim, monkeypatch: pytest.MonkeyPatch
):
    approve_trial(session, claim, fixture("study_NCT06497504_conditions.json"))

    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    result = CliRunner().invoke(
        app, ["review", "list", "--claim", claim.slug, "--kind", "claim"], env={"COLUMNS": "300"}
    )

    assert result.exit_code == 0, result.output
    assert (
        "Health area suggested: Gut and liver (MeSH: Digestive System Diseases);"
        " Immune system and allergies (MeSH: Immune System Diseases);"
        " Infections (MeSH: Infections). Filed under: Infections." in result.output
    )
    assert claim.vertical == "infections"
