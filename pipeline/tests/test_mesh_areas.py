"""The group suggested for a claim, from its clinical categories and the topic mapping.
The mapping itself is tested in test_clinical_pure.py."""

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
from thenwhat.cli import app
from thenwhat.clinical.service import suggestion_line
from thenwhat.db.models import Claim, Entity, EntityMatch, EvidenceEvent, TermRecord
from thenwhat.domain import Decider, EventType, ReviewState

FIXTURES = Path(__file__).parent / "fixtures" / "clinicaltrials"
NOW = datetime(2026, 11, 12, tzinfo=UTC)


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


YEAR = "http://id.nlm.nih.gov/mesh/2026"
# The recorded trial's two condition terms and the tops of the trees each sits in.
DESCRIPTORS: dict[str, tuple[str, list[str], list[str]]] = {
    "D007239": ("Infections", ["C01"], []),
    "D004066": ("Digestive System Diseases", ["C06"], []),
    "D007154": ("Immune System Diseases", ["C20"], []),
    "D006509": ("Hepatitis B", ["C01.925.440.435", "C06.552.380.705.437"], ["D007239", "D004066"]),
    "D000163": (
        "Acquired Immunodeficiency Syndrome",
        ["C01.221.250.875.040", "C20.673.480.040"],
        ["D007154", "D007239"],
    ),
}


def store_descriptors(session: Session) -> None:
    for identifier, (label, trees, broader) in DESCRIPTORS.items():
        session.add(
            TermRecord(
                source_name="mesh",
                external_id=identifier,
                url=f"https://id.nlm.nih.gov/mesh/{identifier}",
                payload={
                    "term": {
                        "@id": f"{YEAR}/{identifier}",
                        "label": {"@language": "en", "@value": label},
                        "treeNumber": [f"{YEAR}/{tree}" for tree in trees],
                        "broaderDescriptor": [f"{YEAR}/{one}" for one in broader],
                    },
                    "concept": None,
                },
                fetched_at=NOW,
            )
        )
    session.flush()


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
            review_state=ReviewState.APPROVED,
            reviewed_at=NOW,
            reviewed_by=Decider.RULE,
        )
    )
    session.flush()


def test_line_without_approved_trials_says_why(session: Session, claim: Claim):
    assert suggestion_line(session, claim) == (
        "Health area: no suggestion, as its approved trials and papers give no category."
    )


def test_line_says_when_the_mesh_records_are_not_read(session: Session, claim: Claim):
    approve_trial(session, claim, fixture("study_NCT06497504_conditions.json"))

    assert suggestion_line(session, claim) == (
        "Health area: no suggestion, as the MeSH records of its clinical categories are"
        " not read yet; run `thenwhat clinical tree`."
    )


def test_review_list_shows_the_suggestion_and_leaves_the_vertical(
    session: Session, claim: Claim, monkeypatch: pytest.MonkeyPatch
):
    approve_trial(session, claim, fixture("study_NCT06497504_conditions.json"))
    store_descriptors(session)

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
        "Health area suggested: Gut and liver (MeSH: Hepatitis B, under Digestive System"
        " Diseases); Immune system and allergies (MeSH: Acquired Immunodeficiency Syndrome,"
        " under Immune System Diseases); Infections (MeSH: Acquired Immunodeficiency"
        " Syndrome, under Infections). Filed under: Infections." in result.output
    )
    assert claim.vertical == "infections"
