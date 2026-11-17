"""The trial listing the site's search and trial page are built with, from synthetic
rows in the test database. Scenario names are from openspec trial-pages."""

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from thenwhat.claims.entry import add_claim, archive_claim
from thenwhat.cli import app
from thenwhat.db.models import Claim, RegistryTrial
from thenwhat.domain import EventType, ReviewState, TrialPhase
from thenwhat.events.manual import add_manual_event
from thenwhat.export.trials_listing import (
    COLUMNS,
    UnknownSet,
    build_listing,
    listing_json_schema,
    write_listing,
)
from thenwhat.review.queue import decide_item

EARLIER = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
READ = datetime(2026, 11, 17, 4, 0, tzinfo=UTC)
SET = "active-since-2025"
CHECKED_IN_SCHEMA = Path(__file__).resolve().parents[2] / "site" / "trials-listing.schema.json"


def trial(session: Session, external_id: str, **fields: Any) -> RegistryTrial:
    defaults: dict[str, Any] = {
        "registry_name": "clinicaltrials.gov",
        "external_id": external_id,
        "title": f"Synthetic study {external_id}",
        "conditions": ["Synthetic condition"],
        "interventions": [{"type": "DRUG", "name": "EX-1", "otherNames": ["Examplumab"]}],
        "phases": ["PHASE3"],
        "overall_status": "RECRUITING",
        "last_update_posted": date(2026, 3, 1),
        "raw_payload": {},
        "fetched_at": EARLIER,
    }
    row = RegistryTrial(**(defaults | fields))
    session.add(row)
    session.flush()
    return row


def claim_citing(session: Session, slug: str, external_id: str, approve: bool = True) -> Claim:
    claim = add_claim(
        session,
        slug=slug,
        headline="A synthetic treatment was reported",
        vertical="mouth-and-teeth",
        intervention=f"EX-1 {slug}",
        indication="synthetic condition",
        summary="A synthetic summary.",
    )
    decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=EARLIER)
    event = add_manual_event(
        session,
        slug,
        now=EARLIER,
        type=EventType.TRIAL_REGISTERED,
        event_date=date(2025, 9, 1),
        source_url=f"https://clinicaltrials.gov/study/{external_id}",
        summary="Phase 3 trial registered.",
        external_id=external_id,
        trial_phases=[TrialPhase.PHASE_3],
    )
    if approve:
        decide_item(session, "event", event.id, ReviewState.APPROVED, now=EARLIER)
    return claim


def rows(session: Session) -> dict[str, dict[str, Any]]:
    listing = json.loads(build_listing(session, SET).model_dump_json())
    return {row[0]: dict(zip(COLUMNS, row, strict=True)) for row in listing["trials"]}


def test_a_listed_trial_holds_registry_facts_as_codes(session: Session):
    trial(
        session,
        "NCT00000011",
        title="A study of EX-1",
        acronym="EXAMPLE-1",
        phases=["PHASE2", "PHASE3"],
        conditions=["Condition A", "Condition B"],
        interventions=[
            {"type": "DRUG", "name": "EX-1", "otherNames": ["Examplumab"]},
            {"type": "DRUG", "name": "Placebo", "otherNames": []},
            {"type": "DRUG", "name": "EX-1"},
        ],
        fetched_at=READ,
    )
    trial(session, "NCT00000012", overall_status="NOT_YET_RECRUITING", acronym=None)

    listing = build_listing(session, SET)

    assert listing.records_read == READ.date()
    assert rows(session)["NCT00000011"] == {
        "id": "NCT00000011",
        "title": "A study of EX-1",
        "acronym": "EXAMPLE-1",
        "phases": ["phase_2", "phase_3"],
        # The registry's recruiting states are all "under_way".
        "state": "under_way",
        "updated": "2026-03-01",
        "conditions": ["Condition A", "Condition B"],
        # Names alone, each once: no other names, no kinds.
        "interventions": ["EX-1", "Placebo"],
        "claim": None,
    }
    assert rows(session)["NCT00000012"]["state"] == "not_started"
    assert "recruit" not in listing.model_dump_json().lower()


def test_a_trial_outside_the_named_set_is_not_listed(session: Session):
    """Scenario: A trial outside the named set"""
    trial(session, "NCT00000021")
    trial(session, "NCT00000022", phases=["PHASE1"], overall_status="COMPLETED")
    trial(session, "NCT00000023", last_update_posted=date(2024, 6, 1))
    # Another registry's trial, and an identifier the trial page cannot read.
    trial(session, "T0001", registry_name="demo-registry")
    trial(session, "2024-000001-10")

    assert list(rows(session)) == ["NCT00000021"]


def test_only_a_published_claim_is_named_as_citing(session: Session):
    """Scenario: A trial cited only by a claim awaiting audit"""
    for number in range(1, 6):
        trial(session, f"NCT0000003{number}")
    claim_citing(session, "published-b", "NCT00000031")
    claim_citing(session, "published-a", "NCT00000031")
    claim_citing(session, "held", "NCT00000032").awaiting_audit_at = EARLIER
    claim_citing(session, "event-pending", "NCT00000033", approve=False)
    claim_citing(session, "taken-down", "NCT00000034")
    archive_claim(session, "taken-down", reason="synthetic", now=EARLIER)
    session.flush()

    listed = rows(session)

    # The first slug by name when several claims cite one trial.
    assert listed["NCT00000031"]["claim"] == "published-a"
    for uncited in ("NCT00000032", "NCT00000033", "NCT00000034", "NCT00000035"):
        assert listed[uncited]["claim"] is None


def test_an_unknown_set_is_refused_with_the_list(session: Session):
    with pytest.raises(UnknownSet, match="active-since-2025"):
        build_listing(session, "every-trial")


def test_written_listing_validates_against_the_checked_in_schema(session: Session, tmp_path: Path):
    trial(session, "NCT00000041", acronym="EXAMPLE-4")
    trial(session, "NCT00000042", phases=["NA"], last_update_posted=date(2025, 1, 1))
    claim_citing(session, "published", "NCT00000041")
    target = tmp_path / "out" / "trials-listing.json"

    write_listing(session, target, SET)

    text = target.read_text()
    assert text.count("\n") == 1, "the listing is one line"
    jsonschema.validate(json.loads(text), json.loads(CHECKED_IN_SCHEMA.read_text()))
    assert not list(target.parent.glob("*.tmp"))


def test_checked_in_schema_matches_the_models():
    """Regenerate with `thenwhat trials-listing --write-schema
    site/trials-listing.schema.json` after a change."""
    assert json.loads(CHECKED_IN_SCHEMA.read_text()) == listing_json_schema()


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.session.open_session", test_session)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    runner = CliRunner()

    def invoke(*arguments: str) -> Result:
        return runner.invoke(app, ["trials-listing", *arguments])

    return invoke


def test_the_command_writes_the_listing_and_says_what_it_holds(
    run, session: Session, tmp_path: Path
):
    trial(session, "NCT00000051")
    trial(session, "NCT00000052")
    claim_citing(session, "published", "NCT00000052")
    target = tmp_path / "trials-listing.json"

    result = run("--out", str(target))

    assert result.exit_code == 0, result.output
    said = " ".join(result.output.split())
    assert "Listed 2 trials of active-since-2025" in said
    assert "1 cited by a published claim" in said
    assert [row[0] for row in json.loads(target.read_text())["trials"]] == [
        "NCT00000051",
        "NCT00000052",
    ]


def test_the_command_refuses_an_unknown_set_and_writes_nothing(run, tmp_path: Path):
    target = tmp_path / "trials-listing.json"

    result = run("--out", str(target), "--set", "every-trial")

    assert result.exit_code == 1
    assert 'No set of trials is named "every-trial"' in " ".join(result.output.split())
    assert not target.exists()
