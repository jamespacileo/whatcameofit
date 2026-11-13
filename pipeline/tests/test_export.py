"""The export that feeds the site, tested through `build_export` and `write_export`
on a real database. Scenario names are from openspec site-publishing."""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from sqlalchemy.orm import Session

from thenwhat.claims.entities import add_synonym
from thenwhat.claims.entry import add_article, add_claim, add_promise, archive_claim
from thenwhat.db.models import Claim, EvidenceEvent
from thenwhat.domain import (
    Decider,
    EventType,
    EvidenceStage,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.events.manual import add_manual_event
from thenwhat.export.build import SCHEMA_VERSION, build_export, export_json_schema, write_export
from thenwhat.review.queue import confirm_stage, decide_item

EARLIER = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
SLUG = "tooth-regrowth-ex1"
ARTICLE = "https://news.example.org/2018/teeth"
CHECKED_IN_SCHEMA = Path(__file__).resolve().parents[2] / "site" / "export.schema.json"


def new_claim(session: Session, slug: str = SLUG, approved: bool = True) -> Claim:
    claim = add_claim(
        session,
        slug=slug,
        headline="Antibody regrows teeth in mice",
        vertical="mouth-and-teeth",
        intervention=f"EX-1 antibody {slug}",
        indication="tooth agenesis",
        summary="An antibody restored missing teeth in mice.",
    )
    add_article(
        session,
        slug,
        url=ARTICLE,
        outlet="Example News",
        title="Mice regrow teeth",
        published_date=date(2018, 3, 10),
    )
    add_promise(session, slug, article_url=ARTICLE, description="human trials by 2025")
    if approved:
        decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=EARLIER)
    return claim


def add_event(
    session: Session, slug: str = SLUG, approve: bool = True, **overrides: Any
) -> EvidenceEvent:
    values: dict[str, Any] = {
        "type": EventType.TRIAL_REGISTERED,
        "event_date": date(2024, 9, 1),
        "source_url": "https://registry.example/NCT1",
        "summary": "Phase 1 trial registered.",
        "external_id": "NCT1",
        "trial_phases": [TrialPhase.PHASE_1],
    }
    event = add_manual_event(session, slug, now=EARLIER, **(values | overrides))
    if approve:
        decide_item(session, "event", event.id, ReviewState.APPROVED, now=EARLIER)
    return event


def exported(session: Session, now: datetime = NOW) -> dict[str, Any]:
    return json.loads(build_export(session, now=now).model_dump_json())


def claim_in(export: dict[str, Any], slug: str = SLUG) -> dict[str, Any]:
    return next(claim for claim in export["claims"] if claim["slug"] == slug)


# --- publication gate ------------------------------------------------------------


def test_claim_with_mixed_events_exports_only_the_approved_ones(session: Session):
    """Scenario: Claim with mixed events"""
    new_claim(session)
    add_event(session)
    add_event(
        session,
        type=EventType.TRIAL_STATUS_CHANGE,
        trial_state=TrialState.STARTED,
        event_date=date(2024, 10, 1),
        summary="Trial started.",
    )
    add_event(
        session,
        type=EventType.FOLLOWUP_PAPER,
        external_id="10.1000/a",
        trial_phases=[],
        summary="A follow-up paper.",
    )
    add_event(
        session,
        approve=False,
        type=EventType.FOLLOWUP_PAPER,
        external_id="10.1000/pending",
        trial_phases=[],
        summary="PENDING-PAPER",
    )
    rejected = add_event(
        session,
        approve=False,
        type=EventType.FOLLOWUP_PAPER,
        external_id="10.1000/rejected",
        trial_phases=[],
        summary="REJECTED-PAPER",
    )
    decide_item(session, "event", rejected.id, ReviewState.REJECTED, now=EARLIER)

    export = exported(session)

    assert len(claim_in(export)["events"]) == 3
    assert "PENDING-PAPER" not in json.dumps(export) and "REJECTED-PAPER" not in json.dumps(export)


def test_draft_claim_is_not_exported(session: Session):
    """Scenario: Draft claim"""
    new_claim(session)
    new_claim(session, "still-a-draft", approved=False)

    assert [claim["slug"] for claim in exported(session)["claims"]] == [SLUG]


def test_rejected_claim_is_not_exported(session: Session):
    claim = new_claim(session)
    decide_item(session, "claim", claim.id, ReviewState.REJECTED, now=EARLIER)

    assert exported(session)["claims"] == []


def test_archived_claim_leaves_the_export_and_is_listed(session: Session):
    """Scenario: Archived claim"""
    new_claim(session)
    exported(session, now=EARLIER)
    archive_claim(session, SLUG, reason="wrong trial", now=NOW)

    export = exported(session, now=NOW)

    assert export["claims"] == []
    assert export["archived"] == [{"slug": SLUG, "on": "2026-11-20"}]
    assert "wrong trial" not in json.dumps(export)


def test_claim_archived_before_it_was_published_is_not_listed(session: Session):
    new_claim(session)
    archive_claim(session, SLUG, reason="never right", now=NOW)

    assert exported(session, now=NOW)["archived"] == []


# --- what a claim carries ----------------------------------------------------------


def test_exported_claim_carries_what_its_page_shows(session: Session):
    claim = new_claim(session)
    add_synonym(session, SLUG, f"EX-1 antibody {SLUG}", "TRG-999")
    confirm_stage(session, SLUG, EvidenceStage.ANIMAL, now=NOW)
    registered = add_event(session)
    started = add_event(
        session,
        type=EventType.TRIAL_STATUS_CHANGE,
        trial_state=TrialState.STARTED,
        event_date=date(2024, 10, 1),
        summary="Trial started.",
    )

    out = claim_in(exported(session))

    assert out["headline"] == claim.headline and out["summary"] == claim.summary
    assert out["vertical"] == "mouth-and-teeth" and out["indication"] == "tooth agenesis"
    assert out["intervention"] == {"name": f"EX-1 antibody {SLUG}", "synonyms": ["TRG-999"]}
    assert out["first_reported_date"] == "2018-03-10" and out["evidence_stage"] == "animal"
    assert out["status"] == {
        "code": "phase_1",
        "overlay_years": None,
        "updated_at": EARLIER.isoformat().replace("+00:00", "Z"),
        "explained_by": [registered.id, started.id],
        "history": [
            {"on": "2018-03-10", "code": "preclinical_only"},
            {"on": "2024-09-01", "code": "trial_registered"},
            {"on": "2024-10-01", "code": "phase_1"},
        ],
    }
    assert out["articles"] == [
        {
            "url": ARTICLE,
            "outlet": "Example News",
            "title": "Mice regrow teeth",
            "published_date": "2018-03-10",
            "archive_url": None,
        }
    ]
    assert out["promises"] == [
        {"description": "human trials by 2025", "parsed_date": "2025-12-31", "article_url": ARTICLE}
    ]
    assert out["events"][0] == {
        "id": registered.id,
        "type": "trial_registered",
        "event_date": "2024-09-01",
        "date_basis": "entered by operator",
        "summary": "Phase 1 trial registered.",
        "source_name": "manual entry",
        "source_url": "https://registry.example/NCT1",
        "trial_id": "NCT1",
        "trial_phases": ["phase_1"],
        "trial_state": None,
        "regulatory_outcome": None,
    }


def test_export_never_carries_raw_payloads_or_review_internals(session: Session):
    new_claim(session)
    add_event(session)

    text = json.dumps(exported(session))

    assert "raw_payload" not in text and "confidence" not in text and "review_state" not in text


def test_export_states_when_it_was_made_and_when_data_was_last_checked(session: Session):
    new_claim(session)
    add_event(session)

    export = exported(session)

    assert export["schema_version"] == SCHEMA_VERSION
    assert export["generated_at"] == "2026-11-20T10:00:00Z"
    assert export["last_checked_at"] == "2026-11-19T09:00:00Z"
    assert {
        "slug": "mouth-and-teeth",
        "title": "Mouth and teeth",
        "group": {"slug": "mouth-and-teeth", "title": "Mouth and teeth"},
    } in export["verticals"]
    assert any(source["name"] == "ClinicalTrials.gov" for source in export["sources"])


def test_export_with_no_claims_is_still_valid(session: Session):
    export = exported(session)

    assert export["claims"] == [] and export["last_checked_at"] is None
    jsonschema.validate(export, export_json_schema())


# --- overlay and publication time --------------------------------------------------


def test_overlay_is_recomputed_at_export_time(session: Session):
    claim = new_claim(session)
    add_event(session)
    assert claim.overlay_years is None

    later = datetime(2028, 9, 1, 8, 0, tzinfo=UTC)
    out = claim_in(exported(session, now=later))

    assert out["status"]["code"] == "trial_registered" and out["status"]["overlay_years"] == 4
    assert claim.overlay_years == 4


def test_first_export_sets_the_published_time_and_later_exports_keep_it(session: Session):
    claim = new_claim(session)
    assert claim.published_at is None

    exported(session, now=NOW)
    exported(session, now=datetime(2026, 12, 1, tzinfo=UTC))

    assert claim.published_at == NOW


# --- schema --------------------------------------------------------------------------


def test_written_export_validates_against_the_checked_in_schema(session: Session, tmp_path: Path):
    """The site validates against this same file before it builds."""
    new_claim(session)
    add_event(session)
    target = tmp_path / "out" / "export.json"

    write_export(session, target, now=NOW)

    schema = json.loads(CHECKED_IN_SCHEMA.read_text())
    jsonschema.validate(json.loads(target.read_text()), schema)


def test_checked_in_schema_matches_the_models():
    """Regenerate with `thenwhat export --write-schema site/export.schema.json` after a change."""
    assert json.loads(CHECKED_IN_SCHEMA.read_text()) == export_json_schema()


# --- decisions made by the assistant ---------------------------------------------


def preview(session: Session) -> dict[str, Any]:
    return json.loads(build_export(session, now=NOW, preview=True).model_dump_json())


def test_claim_approved_by_the_assistant_stays_out_of_the_export(session: Session):
    """Scenario: Claim approved by the assistant"""
    claim = new_claim(session, approved=False)
    decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=EARLIER, by=Decider.ASSISTANT)

    export = exported(session)

    assert export["claims"] == []
    assert export["preview"] is False


def test_preview_export_includes_it_and_says_no_person_checked_it(session: Session):
    """Scenario: Preview export"""
    claim = new_claim(session, approved=False)
    decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=EARLIER, by=Decider.ASSISTANT)

    export = preview(session)

    assert export["preview"] is True
    assert claim_in(export)["checked_by_person"] is False


def test_operator_approved_claim_is_marked_as_checked_by_a_person(session: Session):
    new_claim(session)

    assert claim_in(exported(session))["checked_by_person"] is True
    # A preview with nothing of the assistant's in it is not marked as one.
    assert preview(session)["preview"] is False


def test_assistant_approved_event_keeps_an_operator_approved_claim_out(session: Session):
    """Scenario: Operator's claim with an assistant's event"""
    new_claim(session)
    event = add_event(session, approve=False)
    decide_item(session, "event", event.id, ReviewState.APPROVED, now=EARLIER, by=Decider.ASSISTANT)

    assert exported(session)["claims"] == []
    assert claim_in(preview(session))["checked_by_person"] is False

    # Once the operator makes the decision their own, the claim is published.
    decide_item(session, "event", event.id, ReviewState.APPROVED, now=EARLIER)
    assert claim_in(exported(session))["checked_by_person"] is True


def test_export_carries_retired_verticals_with_their_successors(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("thenwhat.export.build.RETIRED_VERTICALS", {"teeth": "mouth-and-teeth"})

    export = exported(session)

    assert export["retired_verticals"] == [{"slug": "teeth", "successor": "mouth-and-teeth"}]
