"""The export that feeds the site, tested through `build_export` and `write_export`
on a real database. Scenario names are from openspec site-publishing and trial-facts."""

import copy
import dataclasses
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.corrections import merge_claims, rename_intervention
from thenwhat.claims.entities import add_entity, add_synonym, entities_of, set_origin_paper
from thenwhat.claims.entry import (
    add_article,
    add_claim,
    add_promise,
    archive_claim,
    clear_audit,
    edit_claim,
)
from thenwhat.db.models import (
    Claim,
    ClaimTerm,
    Entity,
    EntityMatch,
    EvidenceEvent,
    PaperRecord,
    ReportedStatement,
    SourceArticle,
    TermRecord,
)
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import suggest_evidence_stage
from thenwhat.domain import (
    Decider,
    EntityType,
    EventType,
    EvidenceStage,
    ReviewState,
    StatementBasis,
    StatementFirmness,
    StatementKind,
    StatementSpeaker,
    TermFit,
    TermRole,
    TrialPhase,
    TrialState,
)
from thenwhat.events.fetch import event_row
from thenwhat.events.manual import add_manual_event
from thenwhat.events.paper_facts import reduced
from thenwhat.events.trial import trial_events
from thenwhat.export.build import SCHEMA_VERSION, build_export, export_json_schema, write_export
from thenwhat.review.decisions import record_decision
from thenwhat.review.queue import confirm_stage, decide_item
from thenwhat.seed.load import load_seed
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.terms import SOURCES as LISTED_SOURCES

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


def test_merged_claims_address_leads_to_the_kept_claim(session: Session):
    """Scenario: Merged claim's address (openspec site-publishing)"""
    new_claim(session)
    new_claim(session, "tooth-regrowth-twin")
    exported(session, now=EARLIER)
    merge_claims(
        session,
        "tooth-regrowth-twin",
        SLUG,
        reason="one antibody",
        by=Decider.HUMAN,
        now=NOW,
        same_treatment_accepted=True,
    )

    export = exported(session, now=NOW)

    assert [claim["slug"] for claim in export["claims"]] == [SLUG]
    assert export["moved"] == [{"slug": "tooth-regrowth-twin", "to": SLUG}]
    assert export["archived"] == []
    assert "one antibody" not in json.dumps(export)

    # Once the kept claim is taken down too, both addresses answer gone.
    archive_claim(session, SLUG, reason="wrong trial", now=NOW)
    export = exported(session, now=NOW)
    assert export["moved"] == []
    assert [entry["slug"] for entry in export["archived"]] == [SLUG, "tooth-regrowth-twin"]


def test_renamed_claims_old_address_leads_to_its_new_one(session: Session):
    """Scenario: Renamed claim's old address (openspec site-publishing)"""
    new_claim(session)
    exported(session, now=EARLIER)
    rename_intervention(
        session, SLUG, f"EX-1 antibody {SLUG}", "TRG-035", by=Decider.HUMAN, now=NOW, reslug=True
    )

    export = exported(session, now=NOW)

    assert [claim["slug"] for claim in export["claims"]] == ["trg-035-tooth-agenesis"]
    assert export["moved"] == [{"slug": SLUG, "to": "trg-035-tooth-agenesis"}]


def test_claim_archived_before_it_was_published_is_not_listed(session: Session):
    new_claim(session)
    archive_claim(session, SLUG, reason="never right", now=NOW)

    assert exported(session, now=NOW)["archived"] == []


def test_claim_awaiting_audit_is_left_out_until_its_hold_is_cleared(session: Session):
    """Scenarios: Held until audited, Audit passed"""
    claim = new_claim(session)
    claim.awaiting_audit_at = EARLIER
    session.flush()

    held = exported(session, now=NOW)

    assert held["claims"] == [] and held["archived"] == []
    assert claim.published_at is None

    clear_audit(session, [SLUG])

    assert [claim["slug"] for claim in exported(session, now=NOW)["claims"]] == [SLUG]
    assert claim.published_at == NOW


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
            "published_by": None,
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


def test_a_match_carries_its_record_field_by_field_once_it_is_read(session: Session):
    """Openspec registry-record-rows: a match read into fields carries them; one stored
    before the fields were kept carries none."""
    claim = new_claim(session)
    read = add_match(session, claim, "NCT00000001", 0.7, ReviewState.PENDING)
    read.record_facts = {
        "title": "EX-1 in tooth agenesis",
        "conditions": ["Tooth Agenesis"],
        "interventions": ["EX-1"],
        "phases": ["phase_2"],
        "state": "under_way",
    }
    add_match(session, claim, "NCT00000002", 0.6, ReviewState.PENDING)
    session.flush()

    first, second = claim_in(exported(session))["matches"]

    assert first["record"] == {**read.record_facts, "participants": None}
    assert second["record"] is None


def test_export_says_the_score_a_match_needs_to_be_approved_by_rule(session: Session):
    """Openspec registry-record-rows: the site says what a possible record lacks."""
    assert build_export(session, now=NOW, match_accept_above=0.8).match_accept_above == 0.8
    # With the rule off only a person approves a match, and there is no score to name.
    assert build_export(session, now=NOW).match_accept_above is None


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
        "papers": ["pmid:26048637"],
        "readings": [],
        "claim_arm": None,
    }
    facts = trial["facts"]
    assert facts["participants"] == {"count": 20, "basis": "actual"}
    assert (facts["allocation"], facts["masking"]) == ("randomised", "double")
    assert facts["sponsor"] == {"name": "Mclean Hospital", "kind": "other"}
    # The record's arms, in its order, with the registry's "Dietary Supplement: " dropped.
    assert facts["arms"] == [
        {"label": "Placebo", "kind": "placebo_comparator", "interventions": ["Placebo"]},
        {"label": "Kudzu", "kind": "active_comparator", "interventions": ["Kudzu"]},
    ]
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
            "papers": [],
            "readings": [],
            "claim_arm": None,
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
            "papers": [],
            "readings": [],
            "claim_arm": None,
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
            "papers": [],
            "readings": [],
            "claim_arm": None,
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


# --- papers and their facts (openspec paper-facts) --------------------------------------

TRIAL_REPORT_DOI = "10.1056/nejmoa2206038"
TRIAL_REPORT_PMID = "35658024"
NO_ROLE_DETAILS = {
    "trial_id": None,
    "listed": None,
    "event_id": None,
    "score": None,
    "reasons": [],
    "decided_by": None,
    "summary": None,
}


def role(name: str, **details: Any) -> dict[str, Any]:
    return {"role": name} | NO_ROLE_DETAILS | details


def index_record(fixture_json, name: str = "pmid_35658024_trial_report") -> dict[str, Any]:
    return copy.deepcopy(fixture_json(f"europepmc/{name}.json")["resultList"]["result"][0])


def store_paper(session: Session, record: dict[str, Any] | None, *, pubmed_id: str | None = None):
    """A paper record as a fetch stores it: reduced, or with no payload when the index
    does not hold the paper."""
    doi = record["doi"].lower() if record else None
    number = record["pmid"] if record else pubmed_id
    session.add(
        PaperRecord(
            identifier=doi or f"pmid:{number}",
            source_name="europepmc",
            pubmed_id=number,
            payload=reduced(record) if record else None,
            fetched_at=OCTOBER,
        )
    )
    session.flush()


def with_references(record: dict[str, Any], *entries: tuple[str, str]) -> dict[str, Any]:
    record["protocolSection"]["referencesModule"] = {
        "references": [
            {"pmid": pubmed_id, "type": kind, "citation": "Example A. A made-up citation."}
            for pubmed_id, kind in entries
        ]
    }
    return record


def add_origin_paper(session: Session, doi: str, slug: str = SLUG) -> EntityMatch:
    origin = add_entity(session, slug, type=EntityType.PAPER, name="Origin", doi=doi)
    set_origin_paper(session, slug, "Origin")
    match = EntityMatch(entity_id=origin.id, source_name="crossref", external_id=doi, score=1.0)
    record_decision(match, ReviewState.APPROVED, by=Decider.HUMAN, now=EARLIER)
    session.add(match)
    session.flush()
    return match


def add_follow_up(session: Session, doi: str, state: ReviewState) -> EvidenceEvent:
    event = add_event(
        session,
        approve=False,
        type=EventType.FOLLOWUP_PAPER,
        event_date=date(2021, 5, 1),
        source_url=f"https://europepmc.org/article/MED/{doi.rsplit('/', 1)[-1]}",
        summary="A later study",
        external_id=doi,
        trial_phases=[],
    )
    decide_item(session, "event", event.id, state, now=EARLIER)
    return event


def test_origin_paper_that_a_trial_also_lists_is_exported_once_with_both_roles(
    session: Session, fixture_json
):
    """Scenario: Origin paper that a trial also lists"""
    claim = new_claim(session)
    add_origin_paper(session, TRIAL_REPORT_DOI)
    store_paper(session, index_record(fixture_json))
    record = with_references(
        study(fixture_json, "study_NCT01596231_results"), (TRIAL_REPORT_PMID, "RESULT")
    )
    add_registry_events(session, claim, record, fetched_at=OCTOBER)

    exported_claim = claim_in(exported(session))

    [paper] = exported_claim["papers"]
    assert paper["identifier"] == TRIAL_REPORT_DOI
    assert paper["url"] == f"https://doi.org/{TRIAL_REPORT_DOI}"
    assert paper["record_url"] == "https://europepmc.org/article/MED/35658024"
    assert paper["roles"] == [
        role("origin"),
        role("trial_result", trial_id="NCT01596231", listed="listed_by_sponsor"),
    ]
    assert paper["facts_as_of"] == "2026-10-03T08:00:00Z"
    assert paper["facts"] == {
        "title": "Tirzepatide Once Weekly for the Treatment of Obesity.",
        "journal": "The New England journal of medicine",
        "year": 2022,
        "kinds": ["randomised_trial", "clinical_trial", "article"],
        "open_access": False,
        "retracted": False,
        "studied_in": ["people"],
    }
    assert exported_claim["trials"][0]["papers"] == [TRIAL_REPORT_DOI]


def test_paper_behind_a_rejected_event_is_not_exported(session: Session):
    """Scenario: Paper behind a rejected event"""
    new_claim(session)
    add_follow_up(session, "10.1000/rejected", ReviewState.REJECTED)
    approved = add_follow_up(session, "10.1000/later", ReviewState.APPROVED)

    papers = claim_in(exported(session))["papers"]

    assert [paper["identifier"] for paper in papers] == ["10.1000/later"]
    assert papers[0]["roles"] == [role("follow_up", event_id=approved.id)]
    # No record of it is stored yet, so it is listed with its link only.
    assert (papers[0]["facts"], papers[0]["facts_as_of"]) == (None, None)


def test_paper_the_index_does_not_hold_is_listed_with_its_number_and_link_only(
    session: Session, fixture_json
):
    """Scenario: Paper the index does not hold"""
    claim = new_claim(session)
    store_paper(session, None, pubmed_id="26048637")
    add_registry_events(session, claim, study(fixture_json, "study_NCT01596231_results"))

    [paper] = claim_in(exported(session))["papers"]

    assert paper == {
        "identifier": "pmid:26048637",
        "url": "https://pubmed.ncbi.nlm.nih.gov/26048637/",
        "record_url": None,
        "roles": [role("trial_result", trial_id="NCT01596231", listed="linked_by_registry")],
        "facts_as_of": None,
        "facts": None,
    }


def test_trial_lists_its_sponsor_listed_and_its_registry_linked_paper(
    session: Session, fixture_json
):
    claim = new_claim(session)
    store_paper(session, index_record(fixture_json))
    record = with_references(
        study(fixture_json, "study_NCT01596231_results"),
        ("111", "BACKGROUND"),
        (TRIAL_REPORT_PMID, "RESULT"),
        ("26048637", "DERIVED"),
    )
    add_registry_events(session, claim, record)

    exported_claim = claim_in(exported(session))

    assert exported_claim["trials"][0]["papers"] == [TRIAL_REPORT_DOI, "pmid:26048637"]
    assert [
        (paper["identifier"], paper["roles"][0]["listed"]) for paper in exported_claim["papers"]
    ] == [
        (TRIAL_REPORT_DOI, "listed_by_sponsor"),
        ("pmid:26048637", "linked_by_registry"),
    ]


def test_papers_of_a_trial_with_only_pending_events_are_not_exported(
    session: Session, fixture_json
):
    claim = new_claim(session)
    add_registry_events(
        session, claim, study(fixture_json, "study_NCT01596231_results"), approve=False
    )

    assert claim_in(exported(session))["papers"] == []


def test_exported_papers_carry_no_abstract_and_no_author(session: Session, fixture_json):
    new_claim(session)
    add_origin_paper(session, TRIAL_REPORT_DOI)
    store_paper(session, index_record(fixture_json))

    text = json.dumps(claim_in(exported(session))["papers"])

    assert "Jastreboff" not in text and "Abstract replaced" not in text


def test_retracted_results_paper_leaves_the_status_unchanged(session: Session, fixture_json):
    """Scenario: Retracted results paper"""
    claim = new_claim(session)
    record = with_references(
        study(fixture_json, "study_NCT01596231_results"), ("9500320", "RESULT")
    )
    add_registry_events(session, claim, record)
    without = claim_in(exported(session))
    assert without["papers"][0]["facts"] is None

    store_paper(session, index_record(fixture_json, "pmid_9500320_retracted"))
    with_paper = claim_in(exported(session))

    assert with_paper["papers"][0]["facts"]["retracted"] is True
    assert with_paper["status"] == without["status"]
    assert with_paper["events"] == without["events"]


def test_paper_of_a_study_in_people_leaves_a_preclinical_claim_as_it_is(
    session: Session, fixture_json
):
    """Scenario: Claim with no trial and a paper of a study in people"""
    claim = new_claim(session)
    confirm_stage(session, claim.slug, EvidenceStage.ANIMAL, now=EARLIER)
    without = claim_in(exported(session))

    add_origin_paper(session, TRIAL_REPORT_DOI)
    store_paper(session, index_record(fixture_json))
    with_paper = claim_in(exported(session))

    assert with_paper["papers"][0]["facts"]["studied_in"] == ["people"]
    assert without["status"]["code"] == "preclinical_only"
    assert with_paper["status"] == without["status"]


# --- related papers (openspec related-research, "Export and site") ----------------------


def add_related(
    session: Session, claim: Claim, external_id: str, score: float, state: ReviewState
) -> EntityMatch:
    intervention = entities_of(session, claim)[0]
    match = EntityMatch(
        entity_id=intervention.id,
        source_name="openalex",
        external_id=external_id,
        score=score,
        record_summary="A study of EX-1 in tooth agenesis. 2023. article. Journal of Examples",
        reasons=["named_in_title", "indication_named"],
    )
    if state is not ReviewState.PENDING:
        record_decision(match, state, by=Decider.RULE, now=EARLIER)
    session.add(match)
    session.flush()
    return match


def test_approved_related_papers_are_exported_as_papers_with_score_and_reasons(
    session: Session, fixture_json
):
    claim = new_claim(session)
    add_related(session, claim, TRIAL_REPORT_DOI, 0.93, ReviewState.APPROVED)
    add_related(session, claim, "W4400000001", 0.85, ReviewState.APPROVED)
    add_related(session, claim, "10.1000/pending", 0.5, ReviewState.PENDING)
    add_related(session, claim, "10.1000/rejected", 0.01, ReviewState.REJECTED)
    store_paper(session, index_record(fixture_json))

    exported_claim = claim_in(exported(session))

    held, unheld = exported_claim["papers"]
    summary = "A study of EX-1 in tooth agenesis. 2023. article. Journal of Examples"
    related = role(
        "related",
        score=0.93,
        reasons=["named_in_title", "indication_named"],
        decided_by="rule",
        summary=summary,
    )
    assert (held["identifier"], held["roles"]) == (TRIAL_REPORT_DOI, [related])
    assert held["facts"]["year"] == 2022
    # A paper known only to the search source keeps that source's link and has no facts.
    assert (unheld["identifier"], unheld["url"], unheld["facts"]) == (
        "openalex:W4400000001",
        "https://openalex.org/W4400000001",
        None,
    )
    assert unheld["roles"][0]["score"] == 0.85
    # Papers found by search are papers, never registry matches of the claim.
    assert exported_claim["matches"] == []
    assert "abstract" not in json.dumps(exported_claim["papers"]).lower()


# --- background cards (openspec knowledge-cards) ----------------------------------------


def add_term(
    session: Session,
    claim: Claim,
    identifier: str,
    label: str,
    *,
    fit: TermFit | None = TermFit.EXACT,
    score: float = 0.95,
    role: TermRole = TermRole.CONDITION,
    definition: str | None = "The vocabulary's OWN WORDS for the term.",
    state: ReviewState = ReviewState.APPROVED,
    record: bool = True,
    reasons: list[dict[str, Any]] | None = None,
) -> ClaimTerm:
    """A scored link between the claim and a vocabulary term, with the term's record."""
    term = ClaimTerm(
        claim_id=claim.id,
        role=role,
        source_name="mesh",
        external_id=identifier,
        label=label,
        fit=fit,
        score=score,
        reasons=reasons or [{"code": "filed_by_registry", "trials": 5, "of": 6}],
    )
    if state is not ReviewState.PENDING:
        record_decision(term, state, by=Decider.RULE, now=EARLIER)
    session.add(term)
    if record and session.get(TermRecord, ("mesh", identifier)) is None:
        session.add(
            TermRecord(
                source_name="mesh",
                external_id=identifier,
                url=f"https://id.nlm.nih.gov/mesh/{identifier}",
                payload={
                    "term": {
                        "@id": f"http://id.nlm.nih.gov/mesh/2026/{identifier}",
                        "label": {"@language": "en", "@value": label},
                    },
                    "concept": {"scopeNote": {"@value": definition}} if definition else None,
                },
                fetched_at=EARLIER,
            )
        )
    session.flush()
    return term


def test_exact_term_makes_the_card_when_a_broader_one_is_approved_too(session: Session):
    """Scenario: Exact and broader terms both approved"""
    claim = new_claim(session)
    add_term(session, claim, "D000001", "Dental Diseases", fit=TermFit.BROADER, score=0.99)
    add_term(session, claim, "D000002", "Anodontia", score=0.9)
    add_term(session, claim, "D000003", "Tooth Abnormalities", score=0.85)
    add_term(session, claim, "D000004", "Jaw", fit=None, score=0.0, state=ReviewState.REJECTED)
    add_term(session, claim, "D000005", "Tooth Loss", score=0.5, state=ReviewState.PENDING)

    data = exported(session)

    assert data["claims"][0]["background"] == [
        {
            "kind": "condition",
            "fit": "exact",
            "label": "Anodontia",
            "name": None,
            "definition": "The vocabulary's OWN WORDS for the term.",
            "definition_source": None,
            "url": "https://id.nlm.nih.gov/mesh/D000002",
            "source": "mesh",
            "external_id": "D000002",
            "version": "2026",
            "score": 0.9,
            "molecule_kind": None,
            "mechanisms": [],
            "facts_source": None,
            "reasons": [
                {
                    "code": "filed_by_registry",
                    "trials": 5,
                    "of": 6,
                    "name": None,
                    "entry_term": None,
                    "kind": None,
                    "type": None,
                    "word": None,
                    "sources": None,
                }
            ],
            "decided_by": "rule",
            "read_at": "2026-11-19T09:00:00Z",
        }
    ]
    assert data["card_sources"] == [
        {
            "name": "mesh",
            "title": "Medical Subject Headings (MeSH)",
            "credit": "Medical Subject Headings (MeSH), U.S. National Library of Medicine",
            "licence": "NLM terms and conditions for MeSH data",
            "url": "https://www.nlm.nih.gov/mesh/meshhome.html",
            "terms_url": (
                "https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html"
            ),
            "in_data_file": True,
        }
    ]
    # The footer's list of data sources credits the vocabulary.
    assert data["sources"][-1] == {
        "name": "Medical Subject Headings (MeSH)",
        "url": "https://www.nlm.nih.gov/mesh/meshhome.html",
    }


def test_only_a_broader_term_makes_a_card_marked_broader(session: Session):
    """Scenario: Only a broader term"""
    claim = new_claim(session)
    add_term(session, claim, "D000001", "Dental Diseases", fit=TermFit.BROADER, score=0.9)
    add_term(
        session,
        claim,
        "D000009",
        "Antibodies",
        fit=TermFit.BROADER,
        score=0.85,
        role=TermRole.INTERVENTION,
    )

    cards = exported(session)["claims"][0]["background"]

    assert [(card["kind"], card["fit"], card["label"]) for card in cards] == [
        ("condition", "broader", "Dental Diseases"),
        ("intervention", "broader", "Antibodies"),
    ]


def test_term_with_no_definition_makes_a_card_with_its_label_and_link(session: Session):
    """Scenario: Term with no definition"""
    claim = new_claim(session)
    add_term(session, claim, "D000002", "Anodontia", definition=None)

    [card] = exported(session)["claims"][0]["background"]

    assert card["definition"] is None
    assert (card["label"], card["url"]) == ("Anodontia", "https://id.nlm.nih.gov/mesh/D000002")


def test_claim_with_no_approved_term_or_no_stored_record_has_no_card(session: Session):
    claim = new_claim(session)
    add_term(session, claim, "D000005", "Tooth Loss", score=0.5, state=ReviewState.PENDING)
    add_term(session, claim, "D000002", "Anodontia", record=False)

    data = exported(session)

    assert data["claims"][0]["background"] == []
    assert data["card_sources"] == []
    assert [source["name"] for source in data["sources"]] == [
        "ClinicalTrials.gov",
        "Europe PMC",
        "Crossref",
        # Listed always: its terms ask for a statement, which the site shows by the list.
        "RxNorm",
    ]


def test_source_not_marked_accepted_gives_no_card(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Share-alike source not yet accepted"""
    claim = new_claim(session)
    add_term(session, claim, "D000002", "Anodontia")
    monkeypatch.setitem(
        LISTED_SOURCES, "mesh", dataclasses.replace(LISTED_SOURCES["mesh"], accepted=False)
    )

    data = exported(session)

    assert data["claims"][0]["background"] == []
    assert data["card_sources"] == []


KIND_REASONS = [
    {"code": "kind_chosen", "kind": "antibody"},
    {"code": "registry_lists_type", "type": "BIOLOGICAL", "trials": 2},
]


def add_kind(session: Session, claim: Claim, score: float = 0.9) -> ClaimTerm:
    return add_term(
        session,
        claim,
        "D000911",
        "Antibodies, Monoclonal",
        fit=TermFit.KIND,
        score=score,
        role=TermRole.INTERVENTION,
        reasons=KIND_REASONS,
    )


def add_named_gene(
    session: Session,
    claim: Claim,
    fixture_json,
    *,
    identifier: str = "ENSG00000186810",
    score: float = 0.95,
    reasons: list[dict[str, Any]] | None = None,
) -> ClaimTerm:
    """An approved link to a gene named in the intervention, with the gene's record."""
    target = fixture_json("opentargets/target_cxcr3.json")["data"]["target"]
    link = ClaimTerm(
        claim_id=claim.id,
        role=TermRole.TARGET,
        source_name="opentargets",
        external_id=identifier,
        label="CXCR3" if identifier == target["id"] else "OTHER1",
        fit=TermFit.EXACT,
        score=score,
        reasons=reasons or [{"code": "word_equals_symbol", "word": "CXCR3"}],
    )
    record_decision(link, ReviewState.APPROVED, by=Decider.RULE, now=EARLIER)
    session.add(link)
    session.add(
        TermRecord(
            source_name="opentargets",
            external_id=identifier,
            url=f"https://platform.opentargets.org/target/{identifier}",
            payload=target
            if identifier == target["id"]
            else {"id": identifier, "approvedSymbol": "OTHER1", "approvedName": "another gene"},
            fetched_at=EARLIER,
        )
    )
    session.flush()
    return link


def test_broader_term_makes_the_intervention_card_when_a_kind_is_approved_too(session: Session):
    """Scenario: Broader term and kind both approved"""
    claim = new_claim(session)
    add_kind(session, claim, score=0.99)
    add_term(
        session,
        claim,
        "D000009",
        "Antibodies",
        fit=TermFit.BROADER,
        score=0.85,
        role=TermRole.INTERVENTION,
    )

    cards = exported(session)["claims"][0]["background"]

    assert [(card["kind"], card["fit"], card["label"]) for card in cards] == [
        ("intervention", "broader", "Antibodies")
    ]


def test_only_a_kind_makes_a_card_marked_as_the_kind_of_intervention(session: Session):
    """Scenario: Only a kind"""
    claim = new_claim(session)
    add_kind(session, claim)

    [card] = exported(session)["claims"][0]["background"]

    assert (card["kind"], card["fit"], card["label"]) == (
        "intervention",
        "kind",
        "Antibodies, Monoclonal",
    )
    assert card["score"] == 0.9 and card["decided_by"] == "rule"
    assert card["definition"] == "The vocabulary's OWN WORDS for the term."
    assert [
        {name: value for name, value in reason.items() if value is not None}
        for reason in card["reasons"]
    ] == KIND_REASONS


def test_entry_term_reason_is_exported_with_the_entry_term_and_the_name(session: Session):
    claim = new_claim(session)
    reason = {
        "code": "entry_term_equals_name",
        "entry_term": "Tooth Agenesis",
        "name": "tooth agenesis",
    }
    add_term(session, claim, "D000002", "Anodontia", reasons=[reason])

    [card] = exported(session)["claims"][0]["background"]

    assert [
        {name: value for name, value in given.items() if value is not None}
        for given in card["reasons"]
    ] == [reason]


def test_supplementary_records_note_is_the_definition_and_its_paper_is_not_exported(
    session: Session, fixture_json
):
    """Scenario: Supplementary record"""
    claim = new_claim(session)
    add_term(
        session,
        claim,
        "C000729680",
        "orforglipron",
        role=TermRole.INTERVENTION,
        record=False,
        reasons=[{"code": "label_equals_name", "name": "Orforglipron"}],
    )
    supplementary = fixture_json("mesh/supplementary_orforglipron.json")
    session.add(
        TermRecord(
            source_name="mesh",
            external_id="C000729680",
            url="https://id.nlm.nih.gov/mesh/C000729680",
            payload={
                "term": supplementary,
                "concept": fixture_json("mesh/concept_orforglipron.json"),
            },
            fetched_at=EARLIER,
        )
    )
    session.flush()

    data = exported(session)

    [card] = data["claims"][0]["background"]
    assert card["definition"] == "An oral, non-peptide glucagon-like peptide-1 receptor agonist"
    assert (card["label"], card["version"], card["fit"]) == ("orforglipron", "2026", "exact")
    # The paper NLM took the record from is in the stored record and nowhere in the export.
    assert supplementary["source"]["@value"].startswith("Nature")
    assert "Nature" not in json.dumps(data)


def test_named_gene_with_no_drug_record_gives_a_target_card_in_its_sources_words(
    session: Session, fixture_json
):
    """Scenario: Named gene and no drug record"""
    claim = new_claim(session)
    add_kind(session, claim)
    add_named_gene(session, claim, fixture_json)
    # A second approved gene with a lower score gives no second card.
    lower = add_named_gene(session, claim, fixture_json, identifier="ENSG00000171243", score=0.85)

    data = exported(session)

    kind, target = data["claims"][0]["background"]
    assert kind["fit"] == "kind"
    described = fixture_json("opentargets/target_cxcr3.json")["data"]["target"]
    assert target == {
        "kind": "target",
        "fit": "exact",
        "label": "CXCR3",
        "name": "C-X-C motif chemokine receptor 3",
        # The first function description, word for word, with its isoform prefix and
        # its inline citations, and UniProt named as where the words are from.
        "definition": described["functionDescriptions"][0],
        "definition_source": "uniprot",
        "url": "https://platform.opentargets.org/target/ENSG00000186810",
        "source": "opentargets",
        "external_id": "ENSG00000186810",
        "version": None,
        "score": 0.95,
        "molecule_kind": None,
        "mechanisms": [],
        "facts_source": None,
        "reasons": [
            {
                "code": "word_equals_symbol",
                "trials": None,
                "of": None,
                "name": None,
                "entry_term": None,
                "kind": None,
                "type": None,
                "word": "CXCR3",
                "sources": None,
            }
        ],
        "decided_by": "rule",
        "read_at": "2026-11-19T09:00:00Z",
    }
    assert target["definition"].startswith("[Isoform 1]: ") and "(PubMed:" in target["definition"]
    assert described["functionDescriptions"][1] not in json.dumps(data)
    assert lower.review_state is ReviewState.APPROVED
    # Both sources are credited, Open Targets with the citation it asks for.
    credits = {source["name"]: source for source in data["card_sources"]}
    assert list(credits) == ["mesh", "opentargets", "uniprot"]
    assert "Buniello, A. et al. (2025)" in credits["opentargets"]["credit"]
    assert (credits["uniprot"]["licence"], credits["uniprot"]["in_data_file"]) == (
        "CC BY 4.0",
        True,
    )
    assert [source["name"] for source in data["sources"]][-2:] == [
        "Open Targets Platform",
        "UniProt, through Open Targets Platform",
    ]


def test_synonym_reason_carries_the_word_and_the_sources_that_give_it(
    session: Session, fixture_json
):
    claim = new_claim(session)
    add_named_gene(
        session,
        claim,
        fixture_json,
        reasons=[{"code": "word_equals_synonym", "word": "USAG-1", "sources": ["uniprot"]}],
    )

    [card] = exported(session)["claims"][0]["background"]

    assert [
        {name: value for name, value in reason.items() if value is not None}
        for reason in card["reasons"]
    ] == [{"code": "word_equals_synonym", "word": "USAG-1", "sources": ["uniprot"]}]


def test_target_description_is_left_out_while_its_origin_is_not_accepted(
    session: Session, fixture_json, monkeypatch: pytest.MonkeyPatch
):
    claim = new_claim(session)
    add_named_gene(session, claim, fixture_json)
    monkeypatch.setitem(
        LISTED_SOURCES, "uniprot", dataclasses.replace(LISTED_SOURCES["uniprot"], accepted=False)
    )

    data = exported(session)

    [card] = data["claims"][0]["background"]
    assert (card["label"], card["definition"], card["definition_source"]) == ("CXCR3", None, None)
    assert [source["name"] for source in data["card_sources"]] == ["opentargets"]
    assert "Receptor for the C-X-C chemokines" not in json.dumps(data)


def test_approved_named_gene_gives_no_card_while_its_source_is_not_accepted(
    session: Session, fixture_json, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Target source not yet accepted"""
    claim = new_claim(session)
    link = add_named_gene(session, claim, fixture_json)
    monkeypatch.setitem(
        LISTED_SOURCES,
        "opentargets",
        dataclasses.replace(LISTED_SOURCES["opentargets"], accepted=False),
    )

    data = exported(session)

    assert data["claims"][0]["background"] == []
    assert data["card_sources"] == []
    assert "CXCR3" not in json.dumps(data)
    # The link and the gene's record stay stored.
    assert link.review_state is ReviewState.APPROVED
    assert session.get(TermRecord, ("opentargets", "ENSG00000186810")) is not None


def test_kind_and_named_gene_links_do_not_change_the_status_or_what_explains_it(
    session: Session, fixture_json
):
    claim = new_claim(session)
    add_event(session)
    confirm_stage(session, SLUG, EvidenceStage.ANIMAL, now=EARLIER)

    def decided() -> tuple[Any, Any, Any]:
        [shown] = exported(session)["claims"]
        return shown["status"], shown["evidence_stage"], shown["events"]

    before = decided()
    add_kind(session, claim)
    add_named_gene(session, claim, fixture_json)

    cards = exported(session)["claims"][0]["background"]
    assert [(card["kind"], card["fit"]) for card in cards] == [
        ("intervention", "kind"),
        ("target", "exact"),
    ]
    assert decided() == before


def add_drug(session: Session, claim: Claim, fixture_json, fixture: str, name: str) -> ClaimTerm:
    """An approved link to the drug source's record of the intervention, as the fixture
    `opentargets/drugs_<fixture>.json` holds it under `name`."""
    hits = fixture_json(f"opentargets/drugs_{fixture}.json")["data"]["search"]["hits"]
    drug = next(hit["object"] for hit in hits if hit["object"]["name"] == name)
    link = ClaimTerm(
        claim_id=claim.id,
        role=TermRole.DRUG,
        source_name="opentargets",
        external_id=drug["id"],
        label=name,
        fit=TermFit.EXACT,
        reasons=[{"code": "drug_name_equals_name", "name": name.capitalize()}],
    )
    record_decision(link, ReviewState.APPROVED, by=Decider.RULE, now=EARLIER)
    session.add(link)
    session.add(
        TermRecord(
            source_name="opentargets",
            external_id=drug["id"],
            url=f"https://platform.opentargets.org/drug/{drug['id']}",
            payload=drug,
            fetched_at=EARLIER,
        )
    )
    session.flush()
    return link


def cards_by_kind(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {card["kind"]: card for card in data["claims"][0]["background"]}


def test_old_component_links_are_not_exported_as_the_whole_combination(
    session: Session, fixture_json
):
    claim = new_claim(session)
    [intervention] = entities_of(session, claim)
    intervention.name = "EX-1 plus semaglutide"
    component = add_term(session, claim, "C100001", "Semaglutide", role=TermRole.INTERVENTION)
    drug = add_drug(session, claim, fixture_json, "semaglutide", "SEMAGLUTIDE")
    add_term(session, claim, "D000001", "Anodontia")

    data = exported(session)

    assert [(c["kind"], c["label"]) for c in data["claims"][0]["background"]] == [
        ("condition", "Anodontia")
    ]
    assert component.review_state is drug.review_state is ReviewState.APPROVED


def test_old_component_drug_does_not_mask_a_branded_whole_regimen(session: Session, fixture_json):
    claim = new_claim(session)
    [intervention] = entities_of(session, claim)
    intervention.name = "Dualex"
    intervention.synonyms = ["EX-1 plus semaglutide", "semaglutide"]
    add_drug(session, claim, fixture_json, "semaglutide", "SEMAGLUTIDE")
    whole = add_drug(session, claim, fixture_json, "tirzepatide", "TIRZEPATIDE")
    whole.label = "DUALEX"
    record = session.get(TermRecord, (whole.source_name, whole.external_id))
    assert record is not None
    record.payload = {**record.payload, "name": "DUALEX"}

    cards = cards_by_kind(exported(session))

    assert cards["drug"]["label"] == "DUALEX"
    assert "target" not in cards, "The suppressed component's GLP1R target must not leak."


def test_drug_with_one_protein_target_gives_a_drug_card_and_that_targets_card(
    session: Session, fixture_json
):
    """Scenarios: Drug with one protein target, Drug record and named gene disagree"""
    claim = new_claim(session)
    add_drug(session, claim, fixture_json, "semaglutide", "SEMAGLUTIDE")
    # An approved link to another gene named in the intervention does not win.
    add_named_gene(session, claim, fixture_json)

    data = exported(session)

    assert [card["kind"] for card in data["claims"][0]["background"]] == ["drug", "target"]
    drug, target = cards_by_kind(data)["drug"], cards_by_kind(data)["target"]
    assert drug == {
        "kind": "drug",
        "fit": "exact",
        "label": "SEMAGLUTIDE",
        "name": None,
        "definition": None,
        "definition_source": None,
        "url": "https://platform.opentargets.org/drug/CHEMBL2108724",
        "source": "opentargets",
        "external_id": "CHEMBL2108724",
        "version": None,
        # Found by its exact name: a reason a reader can check, and no percentage.
        "score": None,
        "molecule_kind": "protein",
        "mechanisms": [{"action": "agonist", "target": "Glucagon-like peptide 1 receptor"}],
        "facts_source": "chembl",
        "reasons": [
            {
                "code": "drug_name_equals_name",
                "trials": None,
                "of": None,
                "name": "Semaglutide",
                "entry_term": None,
                "kind": None,
                "type": None,
                "word": None,
                "sources": None,
            }
        ],
        "decided_by": "rule",
        "read_at": "2026-11-19T09:00:00Z",
    }
    assert (target["label"], target["name"], target["score"]) == (
        "GLP1R",
        "glucagon like peptide 1 receptor",
        None,
    )
    assert target["url"] == "https://platform.opentargets.org/target/ENSG00000112164"
    assert (target["definition_source"], target["facts_source"]) == ("uniprot", "chembl")
    described = fixture_json("opentargets/drugs_semaglutide.json")["data"]["search"]["hits"][0]
    gene = described["object"]["mechanismsOfAction"]["rows"][0]["targets"][0]
    assert target["definition"] == gene["functionDescriptions"][0]
    assert [
        {name: value for name, value in reason.items() if value is not None}
        for reason in target["reasons"]
    ] == [{"code": "drug_record_names_target", "name": "SEMAGLUTIDE"}]
    assert "CXCR3" not in json.dumps(data)
    assert [source["name"] for source in data["card_sources"]] == [
        "opentargets",
        "chembl",
        "uniprot",
    ]
    chembl = data["card_sources"][1]
    assert (chembl["licence"], chembl["in_data_file"]) == ("CC BY-SA 3.0 Unported", False)


def test_drug_with_two_targets_gives_both_mechanisms_and_no_target_card(
    session: Session, fixture_json
):
    """Scenarios: Named peptide with two targets, Drug with two targets"""
    claim = new_claim(session)
    add_drug(session, claim, fixture_json, "tirzepatide", "TIRZEPATIDE")

    [card] = exported(session)["claims"][0]["background"]

    assert (card["kind"], card["molecule_kind"]) == ("drug", "protein")
    assert card["mechanisms"] == [
        {"action": "agonist", "target": "Gastric inhibitory polypeptide receptor"},
        {"action": "agonist", "target": "Glucagon-like peptide 1 receptor"},
    ]


def test_drug_with_two_targets_leaves_the_target_card_to_an_approved_named_gene(
    session: Session, fixture_json
):
    claim = new_claim(session)
    add_drug(session, claim, fixture_json, "tirzepatide", "TIRZEPATIDE")
    add_named_gene(session, claim, fixture_json)

    cards = cards_by_kind(exported(session))

    assert list(cards) == ["drug", "target"]
    assert (cards["target"]["label"], cards["target"]["score"]) == ("CXCR3", 0.95)
    assert cards["target"]["facts_source"] is None


def test_drug_with_no_mechanism_on_record_carries_its_kind_of_molecule_only(
    session: Session, fixture_json
):
    """Scenario: Drug with no mechanism on record"""
    claim = new_claim(session)
    add_drug(session, claim, fixture_json, "orforglipron", "ORFORGLIPRON")

    [card] = exported(session)["claims"][0]["background"]

    assert (card["molecule_kind"], card["mechanisms"]) == ("small_molecule", [])


def test_no_phase_approval_or_indication_of_a_drug_is_stored_or_exported(
    session: Session, fixture_json
):
    claim = new_claim(session)
    link = add_drug(session, claim, fixture_json, "semaglutide", "SEMAGLUTIDE")
    record = session.get(TermRecord, ("opentargets", link.external_id))
    assert record is not None

    def names(value: Any) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {name for item in value.values() for name in names(item)}
        if isinstance(value, list):
            return {name for item in value for name in names(item)}
        return set()

    held = names(record.payload) | names(cards_by_kind(exported(session)))
    for word in ("phase", "approv", "indication", "withdrawn", "blackbox", "tradename"):
        assert not [
            name
            for name in held
            if word in name.lower() and name != "approvedSymbol" and name != "approvedName"
        ], word


def test_no_drug_card_or_drug_records_target_while_the_share_alike_source_is_not_accepted(
    session: Session, fixture_json, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Share-alike source not yet accepted"""
    claim = new_claim(session)
    link = add_drug(session, claim, fixture_json, "semaglutide", "SEMAGLUTIDE")
    add_named_gene(session, claim, fixture_json)
    monkeypatch.setitem(
        LISTED_SOURCES, "chembl", dataclasses.replace(LISTED_SOURCES["chembl"], accepted=False)
    )

    data = exported(session)

    # The named gene gives the target card again; nothing drawn from ChEMBL is there.
    assert [(card["kind"], card["label"]) for card in data["claims"][0]["background"]] == [
        ("target", "CXCR3")
    ]
    assert "chembl" not in [source["name"] for source in data["card_sources"]]
    assert "agonist" not in json.dumps(data) and "GLP1R" not in json.dumps(data)
    assert link.review_state is ReviewState.APPROVED


def test_drug_cards_do_not_change_the_status_or_what_explains_it(session: Session, fixture_json):
    claim = new_claim(session)
    add_event(session)
    confirm_stage(session, SLUG, EvidenceStage.ANIMAL, now=EARLIER)

    def decided() -> tuple[Any, Any, Any]:
        [shown] = exported(session)["claims"]
        return shown["status"], shown["evidence_stage"], shown["events"]

    before = decided()
    add_drug(session, claim, fixture_json, "semaglutide", "SEMAGLUTIDE")

    assert len(exported(session)["claims"][0]["background"]) == 2
    assert decided() == before


def test_cards_do_not_change_the_status_or_what_explains_it(session: Session):
    """Scenario: Card for an approved drug class"""
    claim = new_claim(session)
    add_event(session)
    confirm_stage(session, SLUG, EvidenceStage.ANIMAL, now=EARLIER)

    def decided() -> tuple[Any, Any, Any]:
        [shown] = exported(session)["claims"]
        return shown["status"], shown["evidence_stage"], shown["events"]

    before = decided()
    add_term(
        session,
        claim,
        "D000009",
        "Antibodies",
        role=TermRole.INTERVENTION,
        definition="Agents APPROVED for the treatment of many conditions.",
    )

    assert len(exported(session)["claims"][0]["background"]) == 1
    assert decided() == before


# --- reported statements (openspec reported-statements) --------------------------------


def add_statement(
    session: Session, claim: Claim, text: str, state: ReviewState, confidence: float = 0.9
) -> ReportedStatement:
    [article] = session.scalars(select(SourceArticle).where(SourceArticle.claim_id == claim.id))
    statement = ReportedStatement(
        claim_id=claim.id,
        source_article_id=article.id,
        text=text,
        text_key=text.casefold(),
        kind=StatementKind.EFFECT,
        firmness=StatementFirmness.FACT,
        speaker=StatementSpeaker.ARTICLE,
        basis=StatementBasis.PEOPLE,
        confidence=confidence,
        decision_ref=f"source_article:{article.id}:statement:{len(text)}",
        article_read_at=EARLIER,
    )
    if state is not ReviewState.PENDING:
        record_decision(statement, state, by=Decider.RULE, now=EARLIER)
    session.add(statement)
    session.flush()
    return statement


def test_claim_carries_its_approved_statements_only(session: Session):
    """Scenarios: Claim with four approved and two pending statements; Pending statement"""
    claim = new_claim(session)
    for n in range(4):
        add_statement(session, claim, f"Approved statement {n}.", ReviewState.APPROVED, 0.91)
    for n in range(2):
        add_statement(session, claim, f"Pending statement {n}.", ReviewState.PENDING, 0.6)
    add_statement(session, claim, "Rejected statement.", ReviewState.REJECTED)

    statements = claim_in(exported(session))["reported_statements"]

    assert [s["text"] for s in statements] == [f"Approved statement {n}." for n in range(4)]
    assert statements[0] == {
        "text": "Approved statement 0.",
        "kind": "effect",
        "firmness": "fact",
        "speaker": "article",
        "basis": "people",
        "confidence": 0.91,
        "article_url": ARTICLE,
        "read_on": "2026-11-19",
    }


def test_statements_leave_status_explaining_events_and_evidence_stage_unchanged(
    session: Session,
):
    """Scenario: Statement with a basis in people"""
    claim = new_claim(session)
    confirm_stage(session, SLUG, EvidenceStage.ANIMAL, now=EARLIER)
    add_event(session)
    before = claim_in(exported(session))

    add_statement(session, claim, "It eased symptoms in a study in people.", ReviewState.APPROVED)
    after = claim_in(exported(session))

    assert len(after["reported_statements"]) == 1
    for field in ("status", "evidence_stage", "events"):
        assert after[field] == before[field]


def test_a_statement_decided_by_the_assistant_says_no_person_checked_the_claim(
    session: Session,
):
    claim = new_claim(session)
    statement = add_statement(session, claim, "It eased symptoms.", ReviewState.PENDING)
    assert claim_in(exported(session))["checked_by_person"] is True

    decide_item(
        session, "statement", statement.id, ReviewState.APPROVED, now=NOW, by=Decider.ASSISTANT
    )

    assert claim_in(exported(session))["checked_by_person"] is False


# --- evidence stage, lower band (openspec review, ADR 0004) --------------------------


class StageReading:
    """A backend that reads every claim as an early human study with one probability."""

    name = "fake"

    def __init__(self, probability: float) -> None:
        self.probability = probability

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        rest = [option for option in options if option != "early_human"]
        shares = {"early_human": self.probability, "animal": 1 - self.probability - 0.02}
        shares |= {option: 0.01 for option in rest if option != "animal"}
        return BackendAnswer("early_human", shares, confidence=0.9)


def test_an_unconfirmed_stage_reading_is_exported_apart_and_does_not_set_the_status(
    session: Session,
):
    """Scenario: Lower-band reading is shown and not used"""
    claim = new_claim(session)
    suggest_evidence_stage(session, StageReading(0.7), claim, now=NOW)

    out = claim_in(exported(session))

    assert out["evidence_stage"] is None
    assert out["evidence_stage_reading"] == {
        "stage": "early_human",
        "score": 0.7,
        "also": [{"stage": "animal", "score": pytest.approx(0.28)}],
    }
    assert out["status"]["code"] == "no_trial_found"


def test_a_stage_reading_is_not_exported_when_weak_or_when_the_stage_is_confirmed(
    session: Session,
):
    """Scenarios: Reading below the lower band; Confirmed stage"""
    weak = new_claim(session)
    suggest_evidence_stage(session, StageReading(0.45), weak, now=NOW)
    assert claim_in(exported(session))["evidence_stage_reading"] is None

    suggest_evidence_stage(session, StageReading(0.7), weak, now=NOW)
    confirm_stage(session, SLUG, EvidenceStage.ANIMAL, now=NOW)
    out = claim_in(exported(session))
    assert out["evidence_stage"] == "animal" and out["evidence_stage_reading"] is None


# --- what the registry lists beside the approach (openspec site-publishing) ----------


def claim_with_a_drug_trial(session: Session, fixture_json, approach: str) -> Claim:
    claim = new_claim(session)
    edit_claim(session, SLUG, approach=approach)
    entity = session.scalars(select(Entity).where(Entity.claim_id == claim.id)).one()
    entity.synonyms = ["tideglusib"]
    add_registry_events(session, claim, fixture_json("clinicaltrials/study_NCT02586935.json"))
    return claim


def test_registry_type_is_exported_when_it_supports_the_approach(session: Session, fixture_json):
    """Scenario: Registry supports the approach. A person set it; the registry agrees."""
    claim_with_a_drug_trial(session, fixture_json, "drug")

    assert claim_in(exported(session))["approach_basis"] == {"type": "DRUG", "trials": 1}


def test_no_registry_type_is_exported_for_an_approach_it_does_not_support(
    session: Session, fixture_json
):
    """Scenario: Approach the registry does not support"""
    claim_with_a_drug_trial(session, fixture_json, "gene-therapy")

    assert claim_in(exported(session))["approach_basis"] is None


def test_no_registry_type_is_exported_for_a_claim_with_no_approach(session: Session, fixture_json):
    """Scenario: Claim with no approach"""
    claim_with_a_drug_trial(session, fixture_json, "")

    assert claim_in(exported(session))["approach_basis"] is None


# --- clinical categories (openspec clinical-classification) -------------------------


def store_descriptor(
    session: Session, identifier: str, label: str, tree: str, broader: str | None = None
) -> None:
    year = "http://id.nlm.nih.gov/mesh/2026"
    term: dict[str, Any] = {
        "@id": f"{year}/{identifier}",
        "label": {"@language": "en", "@value": label},
        "treeNumber": f"{year}/{tree}",
    }
    if broader:
        term["broaderDescriptor"] = f"{year}/{broader}"
    session.add(
        TermRecord(
            source_name="mesh",
            external_id=identifier,
            url=f"https://id.nlm.nih.gov/mesh/{identifier}",
            payload={"term": term, "concept": None},
            fetched_at=EARLIER,
        )
    )
    session.flush()


TRIAL_SOURCE = {"kind": "trial", "identifier": "NCT02586935", "score": None}


def autism_tree(session: Session) -> None:
    """The descriptors the recorded trial's two condition terms need, to the tree's top."""
    store_descriptor(session, "D001523", "Mental Disorders", "F03")
    store_descriptor(session, "D065886", "Neurodevelopmental Disorders", "F03.625", "D001523")
    store_descriptor(
        session, "D002659", "Child Development Disorders, Pervasive", "F03.625.164", "D065886"
    )
    store_descriptor(
        session, "D000067877", "Autism Spectrum Disorder", "F03.625.164.113", "D002659"
    )
    store_descriptor(session, "D001321", "Autistic Disorder", "F03.625.164.113.500", "D000067877")


def test_a_claims_clinical_categories_are_exported_with_the_tree_above_them(
    session: Session, fixture_json
):
    """Scenarios: Trial with a condition term; Ancestor is not a category"""
    claim = new_claim(session)
    add_registry_events(session, claim, fixture_json("clinicaltrials/study_NCT02586935.json"))
    autism_tree(session)

    export = exported(session)

    assert claim_in(export)["clinical_categories"] == [
        {"identifier": "D000067877", "sources": [TRIAL_SOURCE]},
        {"identifier": "D001321", "sources": [TRIAL_SOURCE]},
    ]
    clinical = export["clinical"]
    assert (clinical["mesh_years"], clinical["claims_not_read"]) == (["2026"], 0)
    assert [node["identifier"] for node in clinical["nodes"]] == [
        "D000067877",
        "D001321",
        "D001523",
        "D002659",
        "D065886",
    ]
    top = next(node for node in clinical["nodes"] if node["identifier"] == "D001523")
    assert top == {
        "identifier": "D001523",
        "label": "Mental Disorders",
        "tree_numbers": ["F03"],
        "broader": [],
    }


def test_categories_are_left_out_and_counted_while_a_mesh_record_is_not_read(
    session: Session, fixture_json
):
    """Scenario: Record not yet read"""
    claim = new_claim(session)
    add_registry_events(session, claim, fixture_json("clinicaltrials/study_NCT02586935.json"))
    store_descriptor(session, "D001321", "Autistic Disorder", "F03.625.164.113.500", "D000067877")

    export = exported(session)

    assert claim_in(export)["clinical_categories"] is None
    assert export["clinical"] == {"mesh_years": [], "nodes": [], "claims_not_read": 1}


def test_a_claim_whose_records_give_no_category_exports_an_empty_list(session: Session):
    """Scenario: Claim with no approved trial or paper"""
    new_claim(session)

    export = exported(session)

    assert claim_in(export)["clinical_categories"] == []
    assert export["clinical"]["claims_not_read"] == 0


def test_the_reading_of_a_claims_own_condition_is_exported_with_its_score(session: Session):
    """Scenario: Claim with a checked condition term. No trial and no paper gives it."""
    claim = new_claim(session)
    autism_tree(session)
    term = ClaimTerm(
        claim_id=claim.id,
        role=TermRole.CONDITION,
        source_name="mesh",
        external_id="D000067877",
        label="Autism Spectrum Disorder",
        score=0.93126,
        fit=TermFit.EXACT,
    )
    session.add(term)
    session.flush()
    decide_item(session, "term", term.id, ReviewState.APPROVED, now=EARLIER)

    export = exported(session)

    assert claim_in(export)["clinical_categories"] == [
        {
            "identifier": "D000067877",
            "sources": [{"kind": "term", "identifier": "D000067877", "score": 0.9313}],
        }
    ]
    assert "D001523" in [node["identifier"] for node in export["clinical"]["nodes"]]
