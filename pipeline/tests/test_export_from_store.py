"""The export taken from a SQLite file of the truth store's schema, tested by holding it
to the export the database gives for the same records (openspec truth-store, "The export
is assembled once, from either store"). No network: the store file is filled from the
test database through `store/merge.sql`, with a folder standing in for the object store.
"""

import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session

from store_support import assert_same_export, both_exports, store_of
from test_export import (
    ARTICLE,
    EARLIER,
    NOW,
    SLUG,
    add_event,
    add_match,
    add_origin_paper,
    add_registry_events,
    new_claim,
    study,
)
from thenwhat.claims.corrections import merge_claims, rename_intervention
from thenwhat.claims.entry import add_article, archive_claim, clear_audit
from thenwhat.domain import (
    ClaimStatus,
    Decider,
    EventType,
    EvidenceStage,
    RegulatoryOutcome,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.export.build import build_export
from thenwhat.export.compare import canonical_bytes, compare
from thenwhat.export.store_records import StoreFault, StoreRecords
from thenwhat.review.queue import confirm_stage, flag_failure
from thenwhat.seed.load import load_seed

SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "seed" / "tooth-regrowth-usag1.json"


def claim_in(export: dict[str, Any], slug: str = SLUG) -> dict[str, Any]:
    return next(claim for claim in export["claims"] if claim["slug"] == slug)


# --- the cases the cut-over is judged on ---------------------------------------------


def test_seeded_example_is_the_same_from_the_store(session: Session, tmp_path: Path):
    """Scenario: Same records, same export"""
    load_seed(session, json.loads(SEED_FILE.read_text()), now=EARLIER)

    export = assert_same_export(session, tmp_path, NOW)

    [claim] = export["claims"]
    assert claim["slug"] == "tooth-regrowth-usag1"
    assert claim["events"] and claim["trials"] and claim["articles"]
    assert export["outlets"]


def test_archived_claim_is_listed_the_same(session: Session, tmp_path: Path):
    """Scenario: Archived, merged and held claims"""
    new_claim(session)
    new_claim(session, "never-published")
    build_export(session, now=EARLIER)  # publishes both
    archive_claim(session, SLUG, reason="wrong trial", now=NOW)
    new_claim(session, "taken-down-unpublished")
    archive_claim(session, "taken-down-unpublished", reason="never right", now=NOW)

    export = assert_same_export(session, tmp_path, NOW)

    assert export["archived"] == [{"slug": SLUG, "on": "2026-11-20"}]
    assert [claim["slug"] for claim in export["claims"]] == ["never-published"]


def test_merged_claims_address_moves_the_same(session: Session, tmp_path: Path):
    """Scenario: Archived, merged and held claims"""
    new_claim(session)
    new_claim(session, "tooth-regrowth-twin")
    build_export(session, now=EARLIER)
    merge_claims(
        session,
        "tooth-regrowth-twin",
        SLUG,
        reason="one antibody",
        by=Decider.HUMAN,
        now=NOW,
        same_treatment_accepted=True,
    )

    export = assert_same_export(session, tmp_path / "a", NOW)

    assert export["moved"] == [{"slug": "tooth-regrowth-twin", "to": SLUG}]
    assert [claim["slug"] for claim in export["claims"]] == [SLUG]

    # Once the kept claim is taken down too, both addresses answer gone, from either.
    archive_claim(session, SLUG, reason="wrong trial", now=NOW)
    export = assert_same_export(session, tmp_path / "b", NOW)
    assert export["moved"] == []
    assert [entry["slug"] for entry in export["archived"]] == [SLUG, "tooth-regrowth-twin"]


def test_renamed_claims_old_address_moves_the_same(session: Session, tmp_path: Path):
    """Scenario: Archived, merged and held claims"""
    new_claim(session)
    add_event(session)
    build_export(session, now=EARLIER)
    rename_intervention(
        session, SLUG, f"EX-1 antibody {SLUG}", "TRG-035", by=Decider.HUMAN, now=NOW, reslug=True
    )

    export = assert_same_export(session, tmp_path, NOW)

    assert export["moved"] == [{"slug": SLUG, "to": "trg-035-tooth-agenesis"}]
    assert claim_in(export, "trg-035-tooth-agenesis")["events"]


def test_claim_awaiting_audit_is_left_out_by_both(session: Session, tmp_path: Path):
    """Scenario: Archived, merged and held claims"""
    held = new_claim(session)
    held.awaiting_audit_at = EARLIER
    new_claim(session, "released")
    session.flush()

    export = assert_same_export(session, tmp_path / "a", NOW)

    assert [claim["slug"] for claim in export["claims"]] == ["released"]
    assert export["archived"] == []

    clear_audit(session, [SLUG])
    export = assert_same_export(session, tmp_path / "b", NOW)
    assert [claim["slug"] for claim in export["claims"]] == ["released", SLUG]


def _started(session: Session, phase: TrialPhase) -> None:
    add_event(session, trial_phases=[phase])
    add_event(
        session,
        type=EventType.TRIAL_STATUS_CHANGE,
        event_date=date(2024, 10, 1),
        summary="Trial started.",
        trial_state=TrialState.STARTED,
        trial_phases=[phase],
    )


def _no_trial(session: Session) -> None:
    pass


def _preclinical(session: Session) -> None:
    confirm_stage(session, SLUG, EvidenceStage.ANIMAL, now=EARLIER)


def _registered(session: Session) -> None:
    add_event(session)


def _approved(session: Session) -> None:
    add_event(session)
    add_event(
        session,
        type=EventType.REGULATORY_DECISION,
        event_date=date(2026, 5, 1),
        summary="Approved by the regulator.",
        source_url="https://regulator.example/decision",
        external_id="decision-1",
        trial_phases=[],
        regulatory_outcome=RegulatoryOutcome.APPROVED,
    )


def _failed(session: Session) -> None:
    add_event(session)
    posted = add_event(
        session,
        type=EventType.TRIAL_RESULTS_POSTED,
        event_date=date(2026, 2, 1),
        summary="Results posted.",
    )
    flag_failure(
        session,
        SLUG,
        trial_id="NCT1",
        event_id=posted.id,
        source_url="https://registry.example/NCT1/results",
        now=EARLIER,
    )


def _terminated(session: Session) -> None:
    add_event(session)
    add_event(
        session,
        type=EventType.TRIAL_STATUS_CHANGE,
        event_date=date(2025, 1, 5),
        summary="Trial terminated.",
        trial_state=TrialState.TERMINATED,
    )


def _retracted(session: Session) -> None:
    add_origin_paper(session, "10.1000/origin")
    add_event(session)
    add_event(
        session,
        type=EventType.RETRACTION,
        event_date=date(2026, 6, 1),
        summary="The paper was retracted.",
        source_url="https://doi.org/10.1000/origin",
        external_id="10.1000/origin",
        trial_phases=[],
    )


@pytest.mark.parametrize(
    ("status", "evidence"),
    [
        (ClaimStatus.NO_TRIAL_FOUND, _no_trial),
        (ClaimStatus.PRECLINICAL_ONLY, _preclinical),
        (ClaimStatus.TRIAL_REGISTERED, _registered),
        (ClaimStatus.PHASE_1, lambda session: _started(session, TrialPhase.PHASE_1)),
        (ClaimStatus.PHASE_2, lambda session: _started(session, TrialPhase.PHASE_2)),
        (ClaimStatus.PHASE_3, lambda session: _started(session, TrialPhase.PHASE_3)),
        (ClaimStatus.APPROVED, _approved),
        (ClaimStatus.FAILED, _failed),
        (ClaimStatus.TERMINATED, _terminated),
        (ClaimStatus.RETRACTED, _retracted),
    ],
    ids=lambda value: value.value if isinstance(value, ClaimStatus) else "",
)
def test_status_from_each_rule_is_the_same(
    session: Session, tmp_path: Path, status: ClaimStatus, evidence: Any
):
    """Scenario: Every status"""
    new_claim(session)
    evidence(session)

    export = assert_same_export(session, tmp_path, NOW)

    held = claim_in(export)["status"]
    assert held["code"] == status.value
    assert held["history"][-1]["code"] == status.value


def test_quiet_claims_overlay_is_derived_the_same_at_the_exports_date(
    session: Session, tmp_path: Path
):
    """Scenario: Every status"""
    new_claim(session)

    export = assert_same_export(session, tmp_path, NOW)

    assert claim_in(export)["status"]["overlay_years"] == 8
    # The store's file holds no overlay for the claim: it was derived while exporting.
    with sqlite3.connect(tmp_path / "store.db") as db:
        assert db.execute("SELECT overlay_years FROM claim").fetchall() == [(None,)]


# --- what the reader does with the store's own shape ----------------------------------


def test_registry_record_kept_as_an_object_gives_the_same_trial_facts(
    session: Session, tmp_path: Path, fixture_json
):
    """Scenario: A payload kept as an object"""
    claim = new_claim(session)
    add_registry_events(session, claim, study(fixture_json, "study_NCT03491397_rows"))

    export = assert_same_export(session, tmp_path, NOW)

    [trial] = claim_in(export)["trials"]
    assert trial["facts"]["results"] is not None
    objects = list((tmp_path / "objects" / "payload").iterdir())
    assert objects, "the record is larger than the store keeps in a row"


def test_export_refuses_a_payload_that_is_not_the_one_its_checksum_names(
    session: Session, tmp_path: Path, fixture_json
):
    """Scenario: A payload that is missing or altered"""
    claim = new_claim(session)
    add_registry_events(session, claim, study(fixture_json, "study_NCT03491397_rows"))
    records, _ = store_of(session, tmp_path, NOW)
    [held] = list((tmp_path / "objects" / "payload").iterdir())

    held.write_bytes(held.read_bytes().replace(b"NCT03491397", b"NCT00000000"))
    with pytest.raises(StoreFault, match="does not have that checksum"):
        build_export(records, now=NOW)

    held.unlink()
    with pytest.raises(StoreFault, match="is not in"):
        build_export(records, now=NOW)
    records.close()


def test_export_from_the_store_writes_nothing_to_it(session: Session, tmp_path: Path):
    """Scenario: Reading only"""
    new_claim(session)
    add_event(session)
    records, _ = store_of(session, tmp_path, NOW)
    before = (tmp_path / "store.db").read_bytes()

    export = build_export(records, now=NOW)
    records.close()

    assert [claim.slug for claim in export.claims] == [SLUG]
    assert (tmp_path / "store.db").read_bytes() == before
    # The claim had no published time; who states the publication is told which.
    assert records.first_published == [SLUG]


def test_file_without_the_stores_schema_is_refused(tmp_path: Path):
    """Scenario: Not a store file"""
    sqlite3.connect(tmp_path / "other.db").execute("CREATE TABLE claim (id INTEGER)").close()

    with pytest.raises(StoreFault, match="does not have the store's schema"):
        StoreRecords(tmp_path / "other.db")
    with pytest.raises(StoreFault, match="No store file"):
        StoreRecords(tmp_path / "absent.db")


def test_matches_scored_and_read_are_the_same_with_their_readings(session: Session, tmp_path: Path):
    """A match's reading is the latest scoring decision about it, which the store files
    under the match's natural key."""
    claim = new_claim(session)
    add_match(session, claim, "NCT1", 0.92, ReviewState.APPROVED)
    for number in range(2, 9):
        add_match(session, claim, f"NCT{number}", 0.1 * number, ReviewState.PENDING)

    export = assert_same_export(session, tmp_path, NOW, match_accept_above=0.8)

    matches = claim_in(export)["matches"]
    assert [match["state"] for match in matches] == ["approved"] + ["candidate"] * 5


# --- the comparison itself ------------------------------------------------------------


def test_comparison_names_the_claim_and_the_place_that_differ(session: Session, tmp_path: Path):
    """Scenario: A difference is named"""
    new_claim(session)
    add_event(session)
    new_claim(session, "second-claim")
    from_database, from_store = both_exports(session, tmp_path, NOW)
    claim_in(from_store)["events"][0]["summary"] = "Something else."
    from_store["archived"].append({"slug": "gone", "on": "2026-01-01"})

    comparison = compare(from_database, from_store)

    assert not comparison.same
    assert [(d.part, d.claim) for d in comparison.differences] == [
        ("archived", False),
        (SLUG, True),
    ]
    assert any("events[0].summary" in place for place in comparison.differences[1].places)
    assert comparison.lines()[0].startswith("The two exports differ: 1 of 2 claims")


def test_comparison_looks_past_row_ids_and_order_among_equals_and_nothing_else(
    session: Session, tmp_path: Path
):
    """Scenario: What the comparison looks past"""
    new_claim(session)
    first = add_event(session)
    add_event(session, external_id="NCT2", source_url="https://registry.example/NCT2")
    add_article(
        session,
        SLUG,
        url=ARTICLE + "-again",
        outlet="Example News",
        title="More mice",
        published_date=date(2018, 3, 10),
    )
    export = json.loads(build_export(session, now=NOW).model_dump_json())

    # Other row ids, the two same-day events and articles the other way round, made later.
    other = json.loads(json.dumps(export))
    [claim] = other["claims"]
    for event in claim["events"]:
        event["id"] += 1000
    claim["status"]["explained_by"] = [number + 1000 for number in claim["status"]["explained_by"]]
    claim["events"].reverse()
    claim["articles"].reverse()
    other["generated_at"] = datetime(2027, 1, 1, tzinfo=UTC).isoformat()
    assert compare(export, other).same
    assert canonical_bytes(export) == canonical_bytes(other)

    # An event out of its date order is not looked past.
    late = json.loads(json.dumps(export))
    next(e for e in late["claims"][0]["events"] if e["id"] == first.id)["event_date"] = "2025-01-01"
    assert not compare(export, late).same
