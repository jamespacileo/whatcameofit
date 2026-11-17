"""The store's natural-key form of every kind of record (openspec change
`cloudflare-source-of-truth`, task 4.1): Postgres rows to store records and back, and the
records held to `store/schema.sql` and `store/merge.sql` so that neither can drift.

The round trip: build rows, gather them as store records, empty the tables, place the
records back, gather again. What the store keeps must be the same, and no row id may
appear in a record.
"""

import importlib.util
import re
import sqlite3
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key
from thenwhat.db.models import (
    ArticleLead,
    Claim,
    ClaimChange,
    ClaimTerm,
    DecisionLog,
    Entity,
    EntityArticle,
    EntityMatch,
    EntitySubstance,
    EvidenceEvent,
    FailureFlag,
    LinkLead,
    LinkLeadLabel,
    LinkLeadLink,
    LinkShare,
    LlmUsage,
    MeasureClaim,
    MeasureDaily,
    OrganisationRecord,
    OutletIcon,
    PaperRecord,
    Promise,
    Reading,
    RegistryLoad,
    RegistryTrial,
    ReportedStatement,
    SourceArticle,
    TermRecord,
    TrialRead,
    WorkEntry,
)
from thenwhat.store.form import INLINE_PAYLOAD_LIMIT, Record, content_sha256, payload_of
from thenwhat.store.gather import gather
from thenwhat.store.place import place
from thenwhat.store.records import claim_actions

STORE = Path(__file__).resolve().parents[2] / "store"
T0 = datetime(2026, 3, 1, 9, 30, tzinfo=UTC)

KINDS = (
    "payload",
    "claim",
    "action",
    "source_article",
    "promise",
    "reported_statement",
    "entity",
    "entity_article",
    "entity_match",
    "claim_term",
    "source_record",
    "entity_substance",
    "evidence_event",
    "failure_flag",
    "trial_read",
    "registry_trial",
    "registry_load",
    "article_lead",
    "link_lead",
    "link_share",
    "link_lead_link",
    "link_lead_label",
    "decision",
    "usage",
    "measure_daily",
    "measure_claim",
    "work_entry",
    "outlet_icon",
)

# A trial record as the registry gives it, with the fields the wider record is read from.
STUDY: dict[str, Any] = {
    "protocolSection": {
        "identificationModule": {"nctId": "NCT01234567", "briefTitle": "A trial", "acronym": "AT"},
        "statusModule": {
            "overallStatus": "TERMINATED",
            "startDateStruct": {"date": "2024-02", "type": "ACTUAL"},
            "completionDateStruct": {"date": "2025-06-30", "type": "ACTUAL"},
        },
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Acme", "class": "INDUSTRY"}},
    },
    "hasResults": True,
}


def _claim(slug: str, **fields: Any) -> Claim:
    defaults: dict[str, Any] = {
        "headline": f"Headline of {slug}",
        "summary": "A summary.",
        "vertical": "cancer",
        "indication": "melanoma",
        "created_at": T0,
    }
    return Claim(slug=slug, **(defaults | fields))


def _world(session: Session) -> dict[str, Any]:
    """One of every kind, with the awkward cases the design names."""
    approved = {"review_state": "approved", "reviewed_at": T0, "reviewed_by": "rule"}
    kept = _claim(
        "drug-x-for-melanoma",
        first_reported_date=date(2025, 1, 2),
        evidence_stage="early_human",
        current_status="terminated",
        status_updated_at=T0,
        published_at=T0 + timedelta(hours=1),
        approach="small_molecule",
        **approved,
    )
    held = _claim(
        "drug-y-for-melanoma",
        awaiting_audit_at=T0,
        archived_at=T0 + timedelta(days=2),
        archive_reason="wrong intervention",
        review_state="approved",
        reviewed_at=T0,
        reviewed_by="assistant",
    )
    gone = _claim(
        "drug-x-tablets-for-melanoma",
        published_at=T0,
        archived_at=T0 + timedelta(days=3),
        archive_reason="merged into drug-x-for-melanoma: same treatment",
        **approved,
    )
    renamed = _claim(
        "drug-z-for-melanoma", reviewed_by="seed", review_state="approved", reviewed_at=T0
    )
    session.add_all([kept, held, gone, renamed])
    session.flush()
    gone.merged_into_id = kept.id
    session.add_all(
        [
            ClaimChange(
                claim_id=gone.id,
                kind="merge",
                into_claim_id=kept.id,
                reason="same treatment",
                decided_by="human",
                decided_at=T0 + timedelta(days=3),
                record={"names_gained": ["drug x tablets"], "articles": [1]},
            ),
            ClaimChange(
                claim_id=renamed.id,
                kind="rename",
                old_name="drug zz",
                new_name="drug z",
                former_slug="drug-zz-for-melanoma",
                decided_by="assistant",
                decided_at=T0 + timedelta(days=4),
            ),
        ]
    )

    article = SourceArticle(
        claim_id=kept.id,
        url="https://www.example.org/news/drug-x?utm_source=feed",
        outlet="Example News",
        title="Drug X shrinks tumours",
        published_date=date(2025, 1, 2),
        content_hash="ab" * 32,
    )
    other_article = SourceArticle(
        claim_id=kept.id,
        url="https://news.example.com/drug-x",
        outlet="Example",
        title="Drug X again",
        published_date=date(2025, 2, 1),
        archive_url="https://archive.example/x",
    )
    session.add_all([article, other_article])
    session.flush()
    session.add(
        Promise(
            claim_id=kept.id,
            source_article_id=article.id,
            description="A trial next year",
            parsed_date=date(2026, 1, 1),
        )
    )
    session.add(
        ReportedStatement(
            claim_id=kept.id,
            source_article_id=article.id,
            text="It shrank tumours in mice.",
            text_key="it shrank tumours in mice",
            kind="effect",
            firmness="fact",
            speaker="researcher",
            basis="animals",
            confidence=0.91,
            decision_ref=f"source_article:{article.id}:statement:1",
            article_read_at=T0,
            created_at=T0,
            **approved,
        )
    )

    intervention = Entity(
        claim_id=kept.id,
        type="intervention",
        name="drug x",
        synonyms=["dx-1"],
        search_phrases=["oral drug x"],
        named_by=["registry", "article"],
    )
    paper = Entity(
        claim_id=kept.id, type="paper", name="Drug X in mice", is_origin_paper=True, doi="10.1/abc"
    )
    company = Entity(claim_id=kept.id, type="company", name="Acme | Pharma")
    gone_intervention = Entity(claim_id=gone.id, type="intervention", name="drug x tablets")
    renamed_intervention = Entity(
        claim_id=renamed.id, type="intervention", name="drug z", synonyms=["drug zz"]
    )
    session.add_all([intervention, paper, company, gone_intervention, renamed_intervention])
    session.flush()
    session.add(EntityArticle(entity_id=company.id, source_article_id=article.id))
    match = EntityMatch(
        entity_id=intervention.id,
        source_name="clinicaltrials.gov",
        external_id="NCT01234567",
        score=0.97,
        record_summary="Phase 2, terminated",
        record_facts={"title": "A trial", "phases": ["phase_2"]},
        reasons=["name_in_interventions", "condition_matches"],
        created_at=T0,
        **approved,
    )
    gone_match = EntityMatch(
        entity_id=gone_intervention.id,
        source_name="clinicaltrials.gov",
        external_id="NCT01234567",
        score=0.9,
        created_at=T0,
    )
    session.add_all([match, gone_match])
    session.add(
        ClaimTerm(
            claim_id=kept.id,
            role="condition",
            source_name="mesh",
            external_id="D008545",
            label="Melanoma",
            score=0.88,
            fit="exact",
            reasons=[{"code": "label_equals", "count": 1}],
            created_at=T0,
            **approved,
        )
    )
    session.add_all(
        [
            TermRecord(
                source_name="mesh",
                external_id="D008545",
                url="https://mesh.example/D008545",
                payload={"label": "Melanoma"},
                fetched_at=T0,
            ),
            OrganisationRecord(
                source_name="ror",
                external_id="05abc",
                url="https://ror.example/05abc",
                payload={"name": "Acme"},
                fetched_at=T0,
            ),
            PaperRecord(
                identifier="10.1/abc",
                source_name="crossref",
                pubmed_id="123",
                payload={"title": "Drug X in mice"},
                fetched_at=T0,
            ),
            PaperRecord(identifier="pmid:999", source_name="pubmed", payload=None, fetched_at=T0),
            EntitySubstance(
                entity_id=intervention.id,
                source_name="gsrs",
                external_id="UNII1",
                url="https://gsrs.example/UNII1",
                payload={"names": ["drug x"] * 3},
                fetched_at=T0,
                codes=["DX-1"],
            ),
        ]
    )
    session.flush()

    # A payload over the inline limit: an R2 object, named by its checksum.
    big_payload = {"study": STUDY, "history": ["x" * 100] * (INLINE_PAYLOAD_LIMIT // 90)}
    event = EvidenceEvent(
        claim_id=kept.id,
        entity_match_id=match.id,
        type="trial_status_change",
        event_date=date(2025, 6, 30),
        date_basis="status_verified",
        source_name="clinicaltrials.gov",
        source_url="https://clinicaltrials.gov/study/NCT01234567",
        external_id="NCT01234567",
        trial_phases=["phase_3", "phase_2"],
        trial_state="terminated",
        summary="The trial was terminated.",
        confidence=1.0,
        raw_payload=big_payload,
        fetched_at=T0,
        dedupe_key="trial_status:NCT01234567:terminated",
        created_at=T0,
        **approved,
    )
    small_event = EvidenceEvent(
        claim_id=kept.id,
        type="regulatory_decision",
        event_date=date(2025, 7, 1),
        source_name="fda",
        source_url="https://fda.example/1",
        external_id="BLA1",
        regulatory_outcome="refused",
        summary="Refused.",
        confidence=0.8,
        raw_payload={"decision": "refused"},
        fetched_at=T0,
        dedupe_key="regulatory:BLA1",
        created_at=T0,
    )
    gone_event = EvidenceEvent(
        claim_id=gone.id,
        type="trial_registered",
        event_date=date(2024, 2, 1),
        source_name="clinicaltrials.gov",
        source_url="https://clinicaltrials.gov/study/NCT01234567",
        external_id="NCT01234567",
        summary="Registered.",
        confidence=1.0,
        raw_payload={"x": 1},
        fetched_at=T0,
        dedupe_key="trial_registered:NCT01234567",
        created_at=T0,
    )
    session.add_all([event, small_event, gone_event])
    session.flush()
    session.add(
        FailureFlag(
            claim_id=kept.id,
            trial_external_id="NCT01234567",
            evidence_event_id=event.id,
            source_url=event.source_url,
            created_at=T0,
        )
    )

    read = TrialRead(
        source_name="clinicaltrials.gov",
        trial_id="NCT01234567",
        input_hash="h1",
        instructions_version="3",
        provider="p",
        model="m",
        refusals=[{"outcome": 1, "kind": "measure", "reason": "not_in_field"}],
        read_at=T0,
    )
    session.add(read)
    session.flush()
    session.add_all(
        [
            Reading(
                trial_read_id=read.id,
                outcome=0,
                kind="measure",
                field="measure",
                words="tumour size",
                code="body_measure",
                confidence=0.9,
                decided_by="model",
            ),
            Reading(
                trial_read_id=read.id,
                outcome=0,
                kind="follow_up",
                field="time_frame",
                words="12 weeks",
                number=12,
                unit="weeks",
                confidence=0.95,
                decided_by="model",
            ),
        ]
    )

    # A registry trial with the wider record, and one with nothing beyond the listing.
    trial = RegistryTrial(
        registry_name="clinicaltrials.gov",
        external_id="NCT01234567",
        title="A trial",
        conditions=["Melanoma"],
        interventions=[{"type": "DRUG", "name": "Drug X", "otherNames": ["DX-1", "Oral X"]}],
        phases=["PHASE2"],
        overall_status="TERMINATED",
        start_date="2024-02",
        sponsor_class="INDUSTRY",
        search_name="drug x",
        search_indication="melanoma",
        start_date_type="ACTUAL",
        last_update_posted=date(2025, 7, 1),
        study_first_posted=date(2024, 1, 15),
        primary_completion_date="2025-05",
        primary_completion_date_type="ACTUAL",
        completion_date="2025-06-30",
        completion_date_type="ACTUAL",
        results_first_posted=date(2025, 8, 1),
        has_results=True,
        acronym="AT",
        lead_sponsor_name="Acme",
        raw_payload=STUDY,
        fetched_at=T0,
    )
    bare_trial = RegistryTrial(
        registry_name="clinicaltrials.gov",
        external_id="NCT07654321",
        title="Another",
        conditions=[],
        interventions=[],
        phases=[],
        raw_payload={"protocolSection": {}},
        fetched_at=T0,
    )
    session.add_all([trial, bare_trial])
    session.add(
        RegistryLoad(
            registry_name="clinicaltrials.gov",
            condition="melanoma",
            loaded_from=T0,
            completed_at=T0 + timedelta(minutes=5),
        )
    )
    session.flush()
    session.add(
        ArticleLead(
            registry_trial_id=trial.id,
            url="https://www.news.example/trial-story?ref=x",
            outlet="News",
            title="Trial story",
            published_date=date(2025, 7, 2),
            outlet_kind="general_news",
            source_name="gdelt",
            search_query="drug x melanoma",
            raw_result={"title": "Trial story"},
            fetched_at=T0,
        )
    )

    # A scored lead tied to the claim at an article's own address, and two never stored.
    lead_url = "https://news.example.com/drug-x"
    lead = LinkLead(
        url=lead_url,
        url_key=article_key(lead_url),
        url_key_version=2,
        outlet="news.example.com",
        outlet_kind="general_news",
        title="Drug X again",
        first_shared_at=T0,
        screen_outcome="in_scope",
        triage_score=0.81,
        triage_version=3,
        read_outcome="added_to_claim",
        claim_id=kept.id,
        source_article_id=other_article.id,
    )
    unscored = LinkLead(
        url="https://news.example.com/a",
        url_key="news.example.com/a",
        outlet="news.example.com",
        outlet_kind="general_news",
        title="A",
        first_shared_at=T0,
    )
    unlisted = LinkLead(
        url="https://blog.example/b",
        url_key="blog.example/b",
        outlet="blog.example",
        outlet_kind="unknown",
        title="B",
        first_shared_at=T0,
        triage_score=0.2,
        triage_version=3,
    )
    session.add_all([lead, unscored, unlisted])
    session.flush()
    session.add_all(
        [
            LinkShare(
                link_lead_id=lead.id,
                platform="reddit",
                community="science",
                shared_at=T0,
                score=120,
            ),
            LinkShare(
                link_lead_id=lead.id,
                platform="hackernews",
                community="hackernews",
                shared_at=T0,
                score=40,
                item_number=4242,
            ),
            LinkShare(
                link_lead_id=unscored.id,
                platform="reddit",
                community="science",
                shared_at=T0,
                score=1,
            ),
            LinkLeadLink(
                link_lead_id=lead.id, record_kind="claim", record_id=kept.id, reason="same_address"
            ),
            LinkLeadLink(
                link_lead_id=lead.id,
                record_kind="registry_trial",
                record_id=trial.id,
                reason="names_trial",
            ),
            LinkLeadLabel(
                link_lead_id=lead.id, label="treatment_report", labelled_by="human", labelled_at=T0
            ),
        ]
    )

    session.add_all(
        [
            DecisionLog(
                step="evidence_stage",
                input_ref=f"claim:{kept.id}",
                backend="model",
                model="m",
                options=["animal", "early_human"],
                output={"choice": "early_human"},
                confidence=0.7,
                created_at=T0,
            ),
            DecisionLog(
                step="term_match",
                input_ref=f"claim:{kept.id}:condition:mesh:D008545",
                backend="model",
                options=["yes", "no"],
                created_at=T0,
            ),
            DecisionLog(
                step="entity_match",
                input_ref=f"entity_match:{match.id}",
                backend="model",
                options=["yes", "no"],
                human_label="yes",
                created_at=T0,
            ),
            DecisionLog(
                step="statement_check",
                input_ref=f"source_article:{article.id}:statement:1",
                backend="model",
                options=["says_this"],
                error="timeout",
                created_at=T0,
            ),
            DecisionLog(
                step="same_claim",
                input_ref=f"link_lead:{lead.id}",
                backend="model",
                options=["none"],
                created_at=T0,
            ),
            DecisionLog(
                step="lookup_match",
                input_ref="lookup:abc",
                backend="model",
                options=["none"],
                created_at=T0,
            ),
            DecisionLog(
                step="lead_triage",
                input_ref=f"link_lead:{lead.id}",
                backend="model",
                options=["yes"],
                created_at=T0,
            ),
            LlmUsage(
                purpose="read",
                model="m",
                input_tokens=1000,
                output_tokens=200,
                cost_usd=Decimal("0.012345"),
                created_at=T0,
            ),
            MeasureDaily(
                day=date(2026, 3, 1),
                step="read",
                step_version=2,
                writer="device",
                outcome="done",
                spans=3,
                records=3,
                reused=0,
                ran_seconds=1.5,
                waited_seconds=0.25,
                waited_by_cause={"model": 0.25},
                requests_by_source={"crossref": 2},
                tokens_in=10,
                tokens_out=5,
                cost_usd=Decimal("0.5"),
                inner_cost_usd=Decimal("0.1"),
                rows_written=4,
            ),
            MeasureClaim(
                claim_id=kept.id,
                first_seen_at=T0,
                last_step_at=T0 + timedelta(hours=1),
                spans=2,
                ran_seconds=3.0,
                waited_seconds=1.0,
                cost_usd=Decimal("0.020000"),
            ),
            WorkEntry(
                record_kind="registry_trial",
                record_id=trial.id,
                step="news_search",
                step_version=1,
                outcome="done",
                attempts=1,
                requests_used=2,
                fingerprint="f1",
                last_attempt_at=T0,
            ),
            WorkEntry(
                record_kind="claim",
                record_id=kept.id,
                step="prepare",
                step_version=4,
                outcome="failed",
                attempts=2,
                requests_used=0,
                fingerprint="f2",
                stale=True,
                error="registry down",
                last_attempt_at=T0,
            ),
            WorkEntry(
                record_kind="link_lead",
                record_id=lead.id,
                step="triage",
                step_version=3,
                outcome="done",
                attempts=1,
                requests_used=0,
                fingerprint="f3",
                last_attempt_at=T0,
            ),
            OutletIcon(
                domain="example.org",
                icon_url="https://example.org/favicon.png",
                media_type="image/png",
                content=b"\x89PNG\x00\x01",
                fetched_at=T0,
            ),
            OutletIcon(domain="noicon.example", fetched_at=T0),
        ]
    )
    session.flush()
    return {"kept": kept, "gone": gone, "big_payload": big_payload}


# Every table the mapping reads, so that placing the records starts from nothing.
TABLES = (
    "claim, claim_change, source_article, promise, reported_statement, entity, entity_article,"
    " entity_match, claim_term, term_record, organisation_record, paper_record,"
    " entity_substance, evidence_event, failure_flag, trial_read, reading, registry_trial,"
    " registry_load, article_lead, link_lead, link_share, link_lead_link, link_lead_label,"
    " decision_log, llm_usage, measure_daily, measure_claim, work_entry, outlet_icon"
)


def _by_kind(records: list[Record]) -> dict[str, dict[str, dict[str, Any]]]:
    kinds: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in records:
        kinds[record.kind][record.key] = record.body
    return kinds


@pytest.fixture
def round_trip(session: Session) -> tuple[list[Record], list[Record]]:
    world = _world(session)
    before = gather(session)
    session.execute(text(f"TRUNCATE {TABLES} CASCADE"))
    session.expire_all()
    r2 = {payload_of(world["big_payload"]).sha256: payload_of(world["big_payload"]).text}
    place(session, before, r2)
    session.expire_all()
    return before, gather(session)


@pytest.mark.parametrize("kind", KINDS)
def test_each_kind_comes_back_as_the_store_keeps_it(round_trip, kind: str):
    before, after = round_trip
    first, second = _by_kind(before)[kind], _by_kind(after)[kind]
    assert first, f"the world builds no {kind}"
    assert second == first


def test_no_row_id_crosses_into_a_record(session: Session):
    world = _world(session)
    records = gather(session)
    ids = {str(world["kept"].id), str(world["gone"].id)}
    for record in records:
        if record.kind in ("decision", "usage"):
            continue  # named by their place in the run
        for name in ("claim_id", "entity_id", "source_article_id", "link_lead_id", "id"):
            assert name not in record.body, (record.kind, name)
    refs = {r.body["input_ref"] for r in records if r.kind == "decision"}
    assert refs == {
        "claim:drug-x-for-melanoma",
        "claim:drug-x-for-melanoma:condition:mesh:D008545",
        "entity_match:drug-x-for-melanoma|intervention|drug x|clinicaltrials.gov|NCT01234567",
        "source_article:drug-x-for-melanoma|example.org/news/drug-x:statement:1",
        "link_lead:news.example.com/drug-x",
        "lookup:abc",
    }
    assert not any(ref.endswith(tuple(ids)) for ref in refs)


def test_the_awkward_cases_take_their_natural_form(session: Session):
    world = _world(session)
    kinds = _by_kind(gather(session))

    # A payload over the inline limit travels by checksum only.
    big = payload_of(world["big_payload"])
    assert kinds["payload"][big.sha256] == {
        "sha256": big.sha256,
        "bytes": big.bytes,
        "r2_key": f"payload/{big.sha256}",
    }
    event = kinds["evidence_event"]["drug-x-for-melanoma|trial_status:NCT01234567:terminated"]
    assert event["payload_sha256"] == big.sha256
    assert event["match_entity_name"] == "drug x"
    # Phases in another order say the same.
    assert event["content_sha256"] == content_sha256(
        type="trial_status_change",
        event_date="2025-06-30",
        trial_state="terminated",
        trial_phases=["phase_2", "phase_3"],
        regulatory_outcome=None,
        external_id="NCT01234567",
    )

    # A source article is keyed by its address key, not its address as written.
    assert "drug-x-for-melanoma|example.org/news/drug-x" in kinds["source_article"]

    # The merged claim: its claim, its publication and its merge; the archive comes with
    # the merge, and what it keeps for itself is not sent under a slug the store reads as
    # the claim that stayed.
    gone = "drug-x-tablets-for-melanoma"
    assert gone in kinds["claim"]
    assert kinds["action"][f"merge|{gone}"] == {
        "action": "merge",
        "slug": gone,
        "into_slug": "drug-x-for-melanoma",
        "gains": ["drug x tablets"],
        "decided_by": "human",
        "at": "2026-03-04T09:30:00.000000+00:00",
    }
    assert f"publish|{gone}" in kinds["action"] and f"archive|{gone}" not in kinds["action"]
    assert not [key for key in kinds["entity"] if key.startswith(gone + "|")]
    assert not [key for key in kinds["evidence_event"] if key.startswith(gone + "|")]

    # Archive and audit state.
    held = kinds["claim"]["drug-y-for-melanoma"]
    assert held["awaiting_audit_at"] == "2026-03-01T09:30:00.000000+00:00"
    assert kinds["action"]["archive|drug-y-for-melanoma"]["reason"] == "wrong intervention"
    assert kinds["claim"]["drug-z-for-melanoma"]["origin"] == "seed"
    assert kinds["claim"]["drug-x-for-melanoma"]["origin"] == "backfill"

    # A snapshot holds no rename: it names a slug the store never had.
    assert not [key for key in kinds["action"] if key.startswith("rename|")]

    # The scored lead, tied to its claim; the unscored and the unlisted are not stored.
    assert set(kinds["link_lead"]) == {"news.example.com/drug-x"}
    assert kinds["link_lead"]["news.example.com/drug-x"]["claim_slug"] == "drug-x-for-melanoma"
    assert len(kinds["link_share"]) == 2

    # The registry trial with its wider record and its other names joined for search.
    trial = kinds["registry_trial"]["clinicaltrials.gov|NCT01234567"]
    assert trial["intervention_names"] == "Drug X; DX-1; Oral X"
    assert trial["has_results"] == 1 and trial["completion_date_type"] == "ACTUAL"

    # Link steps' ledger entries and lead triage decisions stay on the device.
    assert {r["record_kind"] for r in kinds["work_entry"].values()} == {"registry_trial", "claim"}
    assert all(r["step"] != "lead_triage" for r in kinds["decision"].values())


def test_the_merged_claim_comes_back_merged_and_archived(round_trip, session: Session):
    gone = session.scalars(select(Claim).where(Claim.slug == "drug-x-tablets-for-melanoma")).one()
    kept = session.scalars(select(Claim).where(Claim.slug == "drug-x-for-melanoma")).one()
    assert gone.merged_into_id == kept.id
    assert gone.archived_at == T0 + timedelta(days=3)
    assert gone.published_at == T0


# --- the mapping and store/schema.sql cannot drift ------------------------------------

KIND_TABLE = {
    "decision": "decision_log",
    "usage": "llm_usage",
    "unlisted_domain": "unlisted_domain_count",
}
# Fields that name a parent by natural key, or carry a column under another name.
NOT_COLUMNS = {
    "*": {"slug", "entity_type", "entity_name", "lead_url_key"},
    "promise": {"url_key"},
    "reported_statement": {"url_key"},
    "entity_article": {"url_key"},
    "article_lead": {"registry_name", "trial_id"},
    "link_lead": {"claim_slug"},
    "failure_flag": {"dedupe_key"},
    "evidence_event": {
        "match_entity_type",
        "match_entity_name",
        "match_source_name",
        "match_external_id",
    },
    "outlet_icon": {"content_hex"},
}
# What an action may carry (store/README.md, "Kinds and the keys their bodies carry").
ACTION_FIELDS = {
    "action",
    "slug",
    "at",
    "decided_by",
    "detail",
    "reason",
    "into_slug",
    "gains",
    "new_slug",
    "old_name",
    "new_name",
    "keep_old_name",
    "dedupe_key",
    "content_sha256",
}
# Columns the store fills itself: its row ids, the run, and when a trial was last checked.
FILLED_BY_STORE = {"id", "added_run", "changed_run", "run_id", "checked_at"}


def _schema() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript((STORE / "schema.sql").read_text())
    return connection


def _columns(connection: sqlite3.Connection, table: str) -> tuple[set[str], set[str]]:
    """A table's columns, and those a record must carry: NOT NULL, no default, not
    generated, not a reference to another table, not filled by the store."""
    rows = connection.execute(f"PRAGMA table_xinfo({table})").fetchall()
    assert rows, f"store/schema.sql has no table {table}"
    references = {row[3] for row in connection.execute(f"PRAGMA foreign_key_list({table})")}
    columns = {row[1] for row in rows}
    required = {
        name
        for _, name, _, notnull, default, _, hidden in rows
        if notnull
        and default is None
        and hidden == 0
        and name not in references
        and name not in FILLED_BY_STORE
    }
    return columns, required


def test_every_field_is_a_column_of_the_schema_and_every_required_column_is_there(session: Session):
    _world(session)
    connection = _schema()
    # The merge reads a record's fields in its statements and in the schema's views.
    merge = (STORE / "merge.sql").read_text() + (STORE / "schema.sql").read_text()
    read_by_merge = set(re.findall(r"body\s*->>?\s*'(\w+)'", merge))
    seen: set[str] = set()
    for record in gather(session):
        fields = set(record.body)
        unread = fields - read_by_merge
        assert not unread, (
            f"{record.kind} carries {sorted(unread)}, which store/merge.sql never reads"
        )
        if record.kind == "action":
            assert fields <= ACTION_FIELDS, (record.key, sorted(fields - ACTION_FIELDS))
            continue
        table = KIND_TABLE.get(record.kind, record.kind)
        columns, required = _columns(connection, table)
        named = NOT_COLUMNS["*"] | NOT_COLUMNS.get(record.kind, set())
        if record.kind == "claim":
            named -= {"slug"}
        extra = fields - columns - named
        assert not extra, f"{record.kind} carries {sorted(extra)}, which {table} has no column for"
        missing = required - fields
        assert not missing, (
            f"{record.kind} {record.key} lacks {sorted(missing)}, which {table} requires"
        )
        seen.add(record.kind)
    assert seen == set(KINDS) - {"action"}


def test_a_rename_names_the_claim_by_the_slug_it_had_and_comes_back(session: Session):
    """A rename is pushed when it is made (task 4.4), not from a snapshot."""
    _world(session)
    renamed = session.scalars(select(Claim).where(Claim.slug == "drug-z-for-melanoma")).one()
    change = session.scalars(select(ClaimChange).where(ClaimChange.kind == "rename")).one()
    (action,) = claim_actions(renamed, [change], {})
    assert action.body == {
        "action": "rename",
        "slug": "drug-zz-for-melanoma",
        "new_slug": "drug-z-for-melanoma",
        "old_name": "drug zz",
        "new_name": "drug z",
        "decided_by": "assistant",
        "at": "2026-03-05T09:30:00.000000+00:00",
    }
    session.delete(change)
    session.flush()
    place(session, [action])
    again = session.scalars(select(ClaimChange).where(ClaimChange.kind == "rename")).one()
    assert claim_actions(renamed, [again], {}) == [action]


def _proof() -> Any:
    spec = importlib.util.spec_from_file_location("store_proof", STORE / "proof" / "proof.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_records_merge_into_the_store_and_a_second_push_adds_nothing(session: Session):
    """Through store/merge.sql in plain SQLite, as the proof runs it: every record finds
    its parent (the run's counts reconcile), and the same records pushed again leave
    every table of the store as it was."""
    _world(session)
    staged = [(r.kind, r.key, r.body) for r in gather(session)]
    store = _proof().Store()
    ok, run = store.run(staged)
    assert ok, store.last_error
    report = store.report(run)
    counts: dict[str, int] = defaultdict(int)
    for kind, _, _ in staged:
        counts[kind] += 1
    assert {kind: resolved for kind, (resolved, *_) in report.items()} == counts

    tables = [
        name
        for (name,) in store.all(
            "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE '%fts%'"
            " AND name NOT IN ('run', 'run_step', 'run_stated', 'stg', 'merging', 'merge_report',"
            " 'merge_guard', 'store_step')"
        )
    ]

    def snapshot() -> dict[str, list[str]]:
        out = {}
        for table in tables:
            names = [row[1] for row in store.all(f"PRAGMA table_xinfo({table})")]
            kept = [
                n for n in names if n not in ("changed_run", "run_id", "resolved_run", "seen_at")
            ]
            out[table] = sorted(map(repr, store.all(f"SELECT {', '.join(kept)} FROM {table}")))
        return out

    first = snapshot()
    ok, again = store.run(staged)
    assert ok, store.last_error
    second = snapshot()
    # Decisions and spend are kept by run, and measurements are totals a merge adds to:
    # each is pushed once, by the run that made it, never again from a snapshot.
    by_run = ("decision_log", "llm_usage", "measure_daily", "measure_claim")
    assert {t: rows for t, rows in second.items() if t not in by_run} == {
        t: rows for t, rows in first.items() if t not in by_run
    }
    assert len(second["decision_log"]) == 2 * len(first["decision_log"])
    assert second["measure_daily"] != first["measure_daily"]
    added = {kind: n for kind, (_, n, _, _) in store.report(again).items() if n}
    assert added == {"decision": counts["decision"], "usage": counts["usage"]}
