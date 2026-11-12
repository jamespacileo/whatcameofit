"""The checked-in seed claim, tested through `load_seed` and the export it produces."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.csv_import import import_csv
from thenwhat.claims.entry import claim_count
from thenwhat.db.models import DecisionLog, EntityMatch
from thenwhat.domain import ClaimStatus, Decider, EvidenceStage, ReviewState
from thenwhat.export.build import build_export
from thenwhat.seed.load import load_seed, seeded_events

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
REPOSITORY = Path(__file__).resolve().parents[2]
SEED_FILE = REPOSITORY / "data" / "seed" / "tooth-regrowth-usag1.json"
SEED_EXPORT = REPOSITORY / "site" / "data" / "seed-export.json"


@pytest.fixture
def seed() -> dict[str, Any]:
    return json.loads(SEED_FILE.read_text())


def test_seed_names_the_registry_its_trial_is_in_and_how_the_trial_is_supplied(seed):
    registration = seed["trial_registration"]

    assert registration["registry"].startswith("jRCT")
    assert registration["on_clinicaltrials_gov"] is False
    assert "manual events" in registration["supplied_by"]


def test_seed_loads_as_an_approved_claim_with_its_status_derived(session: Session, seed):
    claim = load_seed(session, seed, now=NOW)

    assert claim is not None and claim.slug == "tooth-regrowth-usag1"
    assert (claim.review_state, claim.reviewed_by) == (ReviewState.APPROVED, Decider.SEED)
    assert claim.current_status is ClaimStatus.PHASE_1
    assert claim.evidence_stage is EvidenceStage.ANIMAL
    assert claim.first_reported_date is not None and claim.first_reported_date.year == 2021


def test_seed_decisions_are_the_seed_loaders_not_a_humans(session: Session, seed):
    claim = load_seed(session, seed, now=NOW)
    assert claim is not None

    deciders = {event.reviewed_by for event in seeded_events(session, claim)}
    deciders |= {match.reviewed_by for match in session.scalars(select(EntityMatch))}

    assert deciders == {Decider.SEED}
    assert session.scalars(select(DecisionLog)).all() == []


def test_loading_the_seed_twice_changes_nothing(session: Session, seed):
    load_seed(session, seed, now=NOW)

    assert load_seed(session, seed, now=NOW) is None
    assert claim_count(session) == 1


def normalised(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Claims with database ids replaced by positions, so two databases compare equal."""
    result = json.loads(json.dumps(claims))
    for claim in result:
        position = {event["id"]: index for index, event in enumerate(claim["events"])}
        for event in claim["events"]:
            event["id"] = position[event["id"]]
        claim["status"]["explained_by"] = [position[i] for i in claim["status"]["explained_by"]]
    return result


def test_checked_in_site_export_is_the_export_of_the_seed(session: Session, seed):
    """Regenerate site/data/seed-export.json after changing the seed (see README)."""
    load_seed(session, seed, now=NOW)

    fresh = json.loads(build_export(session, now=NOW).model_dump_json())
    checked_in = json.loads(SEED_EXPORT.read_text())

    assert normalised(checked_in["claims"]) == normalised(fresh["claims"])
    # The seed carries its outlet's icon, so a fresh checkout shows it with no fetch.
    assert [outlet["domain"] for outlet in fresh["outlets"]] == ["kyoto-u.ac.jp"]
    assert checked_in["outlets"] == fresh["outlets"]


@pytest.mark.parametrize("name", ["claims.csv", "claims-recent.csv"])
def test_seed_csv_imports_under_the_configured_verticals(session: Session, name: str):
    with (REPOSITORY / "data" / "seed" / name).open(encoding="utf-8-sig", newline="") as lines:
        result = import_csv(session, lines)

    assert result.claims > 0
