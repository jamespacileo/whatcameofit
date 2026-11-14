"""The export that feeds the site, tested through `build_export` and `write_export`
on a real database. Scenario names are from openspec site-publishing and trial-facts."""

import copy
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import add_synonym
from thenwhat.claims.entry import add_article, add_claim, add_promise, archive_claim
from thenwhat.db.models import Claim, Entity, EntityMatch, EvidenceEvent
from thenwhat.domain import (
    Decider,
    EntityType,
    EventType,
    EvidenceStage,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.events.fetch import event_row
from thenwhat.events.manual import add_manual_event
from thenwhat.events.trial import trial_events
from thenwhat.export.build import SCHEMA_VERSION, build_export, export_json_schema, write_export
from thenwhat.review.queue import confirm_stage, decide_item
from thenwhat.seed.load import load_seed
from thenwhat.sources.base import SourceRecord

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


def add_registry_events(
    session: Session,
    claim: Claim,
    study: dict[str, Any],
    *,
    fetched_at: datetime = EARLIER,
    approve: bool = True,
) -> list[EvidenceEvent]:
    """Store the events a fetch of `study` creates, each keeping the record as its
    payload. As in a real fetch, a fact the claim already has gets no second event."""
    nct_id = study["protocolSection"]["identificationModule"]["nctId"]
    record = SourceRecord(
        "clinicaltrials.gov",
        nct_id,
        f"https://clinicaltrials.gov/study/{nct_id}",
        study,
        fetched_at,
    )
    held = set(
        session.scalars(select(EvidenceEvent.dedupe_key).where(EvidenceEvent.claim_id == claim.id))
    )
    stored: list[EvidenceEvent] = []
    for draft in trial_events(record):
        if draft.dedupe_key in held:
            continue
        event = event_row(claim, draft)
        session.add(event)
        session.flush()
        if approve:
            decide_item(session, "event", event.id, ReviewState.APPROVED, now=EARLIER)
        stored.append(event)
    return stored


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
        "confidence": 1.0,
    }


def test_scores_are_shown_as_items_publish_by_rule_but_payloads_and_reviews_are_not(
    session: Session, fixture_json
):
    """Since docs/adr/0001-publish-by-rule-archive-to-remove.md the score is the
    disclosure, so every event's confidence is exported. Stored registry records and
    who reviewed what stay private (openspec open-data: no registry record)."""
    claim = new_claim(session)
    add_event(session)
    add_registry_events(session, claim, fixture_json("clinicaltrials/study_NCT02586935.json"))

    text = json.dumps(exported(session))

    assert '"confidence": 1.0' in text
    assert "raw_payload" not in text and "review_state" not in text and "reviewed_by" not in text
    assert "protocolSection" not in text and "Holland Bloorview" in text


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


# --- decisions made by the assistant (openspec auto-publish) ---------------------------


def test_claim_approved_by_the_assistant_is_published_and_says_no_person_checked_it(
    session: Session,
):
    claim = new_claim(session, approved=False)
    decide_item(session, "claim", claim.id, ReviewState.APPROVED, now=EARLIER, by=Decider.ASSISTANT)

    export = exported(session)

    assert claim_in(export)["checked_by_person"] is False
    assert export["preview"] is False


def test_operator_approved_claim_is_marked_as_checked_by_a_person(session: Session):
    new_claim(session)

    assert claim_in(exported(session))["checked_by_person"] is True


def test_assistant_approved_event_marks_an_operator_claim_unchecked(session: Session):
    new_claim(session)
    event = add_event(session, approve=False)
    decide_item(session, "event", event.id, ReviewState.APPROVED, now=EARLIER, by=Decider.ASSISTANT)

    assert claim_in(exported(session))["checked_by_person"] is False

    # Once the operator makes the decision their own, the claim is marked as checked.
    decide_item(session, "event", event.id, ReviewState.APPROVED, now=EARLIER)
    assert claim_in(exported(session))["checked_by_person"] is True


# --- matches and their confidence (openspec auto-publish) ---------------------------


def add_match(session: Session, claim: Claim, external_id: str, score: float, state: ReviewState):
    intervention = session.scalars(
        select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).one()
    match = EntityMatch(
        entity_id=intervention.id,
        source_name="clinicaltrials.gov",
        external_id=external_id,
        score=score,
        record_summary=f"{external_id}: a trial",
    )
    session.add(match)
    session.flush()
    if state is not ReviewState.PENDING:
        decide_item(session, "match", match.id, state, now=EARLIER)
    return match


def test_matches_carry_their_confidence_approved_first(session: Session):
    """Scenario: Claim with one rule-approved trial and one pending candidate"""
    claim = new_claim(session)
    add_match(session, claim, "NCT00000009", 0.3, ReviewState.PENDING)
    add_match(session, claim, "NCT00000001", 0.92, ReviewState.APPROVED)
    add_match(session, claim, "NCT00000005", 0.01, ReviewState.REJECTED)

    matches = claim_in(exported(session))["matches"]

    assert [(m["external_id"], m["state"], m["score"]) for m in matches] == [
        ("NCT00000001", "approved", 0.92),
        ("NCT00000009", "candidate", 0.3),
    ]
    assert matches[0]["url"] == "https://clinicaltrials.gov/study/NCT00000001"
    assert matches[0]["decided_by"] == "human"
    assert matches[1]["decided_by"] is None


def test_at_most_five_candidates_are_exported(session: Session):
    claim = new_claim(session)
    for number in range(7):
        add_match(session, claim, f"NCT0000001{number}", 0.1 + number / 100, ReviewState.PENDING)

    matches = claim_in(exported(session))["matches"]

    assert len(matches) == 5
    assert matches[0]["external_id"] == "NCT00000016"


def test_export_carries_retired_verticals_with_their_successors(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("thenwhat.export.build.RETIRED_VERTICALS", {"teeth": "mouth-and-teeth"})

    export = exported(session)

    assert export["retired_verticals"] == [{"slug": "teeth", "successor": "mouth-and-teeth"}]


# --- trials and their facts (openspec trial-facts) -----------------------------------

MARCH = datetime(2026, 3, 9, 8, 0, tzinfo=UTC)
OCTOBER = datetime(2026, 10, 3, 8, 0, tzinfo=UTC)
SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "seed" / "tooth-regrowth-usag1.json"


def study(fixture_json, name: str) -> dict[str, Any]:
    return copy.deepcopy(fixture_json(f"clinicaltrials/{name}.json"))


def test_trial_with_four_approved_events_is_listed_once_with_its_facts(
    session: Session, fixture_json
):
    """Scenario: Trial with four approved events"""
    claim = new_claim(session)
    record = study(fixture_json, "study_NCT01596231_results")
    # The recorded start date carries no type, so it is marked actual to give a started event.
    record["protocolSection"]["statusModule"]["startDateStruct"]["type"] = "ACTUAL"
    events = add_registry_events(session, claim, record, fetched_at=OCTOBER)
    assert len(events) == 4

    export = exported(session)
    [trial] = claim_in(export)["trials"]

    assert {key: trial[key] for key in trial if key != "facts"} == {
        "trial_id": "NCT01596231",
        "source_name": "clinicaltrials.gov",
        "url": "https://clinicaltrials.gov/study/NCT01596231",
        "title": "Kudzu Treatment for Alcohol Abuse",
        "phases": ["phase_2"],
        "state": "completed",
        "facts_as_of": "2026-10-03T08:00:00Z",
    }
    facts = trial["facts"]
    assert facts["participants"] == {"count": 20, "basis": "actual"}
    assert (facts["allocation"], facts["masking"]) == ("randomised", "double")
    assert facts["sponsor"] == {"name": "Mclean Hospital", "kind": "other"}
    [outcome] = facts["results"]["outcomes"]
    assert [(group["title"], group["analysed"], group["value"]) for group in outcome["groups"]] == [
        ("Placebo", "10", "3.4"),
        ("Kudzu", "10", "1.9"),
    ]
    assert "significantly reduced" not in json.dumps(export)
    jsonschema.validate(export, export_json_schema())


def test_facts_are_read_from_the_most_recently_fetched_record(session: Session, fixture_json):
    """Scenario: Two stored records for one trial"""
    claim = new_claim(session)
    earlier = study(fixture_json, "study_NCT02586935")
    earlier["protocolSection"]["statusModule"]["overallStatus"] = "RECRUITING"
    earlier["protocolSection"]["designModule"]["enrollmentInfo"] = {
        "count": 100,
        "type": "ESTIMATED",
    }
    registered = add_registry_events(session, claim, earlier, fetched_at=MARCH)
    completed = add_registry_events(
        session, claim, study(fixture_json, "study_NCT02586935"), fetched_at=OCTOBER
    )
    assert [event.fetched_at for event in registered] == [MARCH, MARCH]
    assert [event.trial_state for event in completed] == [TrialState.COMPLETED]

    [trial] = claim_in(exported(session))["trials"]

    assert trial["facts_as_of"] == "2026-10-03T08:00:00Z"
    assert trial["facts"]["participants"] == {"count": 83, "basis": "actual"}
    assert trial["state"] == "completed"


def test_trial_whose_events_are_all_pending_or_rejected_is_not_listed(
    session: Session, fixture_json
):
    """Scenario: Trial whose events are all pending"""
    claim = new_claim(session)
    add_event(session)
    add_registry_events(session, claim, study(fixture_json, "study_NCT02586935"), approve=False)
    rejected = add_event(session, approve=False, external_id="NCT9", summary="Another trial.")
    decide_item(session, "event", rejected.id, ReviewState.REJECTED, now=EARLIER)

    assert [trial["trial_id"] for trial in claim_in(exported(session))["trials"]] == ["NCT1"]


def test_trial_entered_by_hand_is_listed_without_facts(session: Session):
    """Scenario: Trial entered by hand from a registry with no client"""
    new_claim(session)
    add_event(session)
    add_event(
        session,
        type=EventType.TRIAL_STATUS_CHANGE,
        trial_state=TrialState.STARTED,
        event_date=date(2024, 10, 1),
        summary="Trial started.",
        source_url="https://registry.example/NCT1/history",
    )
    add_event(session, external_id="NCT2", source_url="https://registry.example/NCT2")

    trials = claim_in(exported(session))["trials"]

    assert trials == [
        {
            "trial_id": "NCT1",
            "source_name": "manual entry",
            "url": "https://registry.example/NCT1/history",
            "title": None,
            "phases": ["phase_1"],
            "state": "under_way",
            "facts_as_of": None,
            "facts": None,
        },
        {
            "trial_id": "NCT2",
            "source_name": "manual entry",
            "url": "https://registry.example/NCT2",
            "title": None,
            "phases": ["phase_1"],
            "state": "not_started",
            "facts_as_of": None,
            "facts": None,
        },
    ]


def test_seed_claims_jrct_trial_is_listed_without_facts(session: Session):
    load_seed(session, json.loads(SEED_FILE.read_text()), now=EARLIER)

    assert claim_in(exported(session), "tooth-regrowth-usag1")["trials"] == [
        {
            "trial_id": "jRCT2051240154",
            "source_name": "jRCT",
            "url": "https://jrct.mhlw.go.jp/en-latest-detail/jRCT2051240154",
            "title": None,
            "phases": ["phase_1"],
            "state": "completed",
            "facts_as_of": None,
            "facts": None,
        }
    ]


def test_every_event_carries_its_confidence(session: Session, fixture_json):
    claim = new_claim(session)
    add_event(session)
    paper = add_event(
        session,
        type=EventType.FOLLOWUP_PAPER,
        external_id="10.1000/a",
        trial_phases=[],
        summary="A follow-up paper.",
    )
    paper.confidence = 0.612345
    add_registry_events(session, claim, study(fixture_json, "study_NCT02586935"))
    session.flush()

    events = claim_in(exported(session))["events"]

    assert {event["summary"]: event["confidence"] for event in events} == {
        "Phase 1 trial registered.": 1.0,
        "A follow-up paper.": 0.6123,
        "Trial NCT02586935 registered (Phase 2).": 1.0,
        "Trial NCT02586935 started.": 1.0,
        "Trial NCT02586935 completed.": 1.0,
    }


def test_posted_result_with_a_high_p_value_leaves_the_status_unchanged(
    session: Session, fixture_json
):
    """Scenario: Posted result with a high p value"""
    claim = new_claim(session)
    record = study(fixture_json, "study_NCT04951479_comparison")
    measures = record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"]
    measures[0]["analyses"][0]["pValue"] = "0.6"
    events = add_registry_events(session, claim, record)

    with_results = claim_in(exported(session))
    [comparison] = with_results["trials"][0]["facts"]["results"]["outcomes"][0]["comparisons"]
    assert comparison["p_value"] == "0.6"

    without = {key: value for key, value in record.items() if key != "resultsSection"}
    for event in events:
        event.raw_payload = without
    session.flush()
    without_results = claim_in(exported(session))

    assert without_results["trials"][0]["facts"]["results"] is None
    assert without_results["status"]["code"] == with_results["status"]["code"]
    assert without_results["status"]["explained_by"] == with_results["status"]["explained_by"]
