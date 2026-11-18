"""The named registry drafting batch plans, writes and replays on the Mac writer."""

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from backfill_support import add_trials
from test_registry_claim_plan import study
from thenwhat.backfill.trial_sets import REGISTRY_CLAIMS_2026
from thenwhat.claims.entry import add_article, add_claim, add_registry_claim, articles_of
from thenwhat.cli import app
from thenwhat.db.models import AuditBatch, Claim, Entity, EntityMatch, LlmUsage
from thenwhat.domain import Decider, DraftedFrom, EntityType, ReviewState
from thenwhat.review.decisions import record_decision


@pytest.fixture
def invoke(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("DECISION_BACKEND", "llm")
    monkeypatch.setenv("LLM_MODEL", "openai:fixture")
    runner = CliRunner()
    return lambda *arguments: runner.invoke(app, ["draft-from-registry", *arguments])


def eligible_set(session: Session, folder: Path) -> Path:
    condition = "Example Neoplasm"
    trials = add_trials(session, 5, registry="clinicaltrials.gov")
    for index, stored in enumerate(trials, 1):
        stored.external_id = f"NCT{index:08d}"
        stored.overall_status = "RECRUITING"
        stored.last_update_posted = date(2026, 11, 16)
        names = ["Drug: Alpha XR", "Drug: Beta"] if index < 3 else ["Drug: Z-231"]
        if index == 5:
            names, condition = ["Drug: Z-999"], "Unsupported Condition"
        record = study(
            [condition],
            [{"type": "EXPERIMENTAL", "label": "Test Arm", "interventionNames": names}],
        )
        record["protocolSection"]["identificationModule"] = {
            "nctId": stored.external_id,
            "briefTitle": "A study for " + condition,
        }
        if index != 5:
            record["derivedSection"] = {
                "conditionBrowseModule": {"meshes": [{"id": "D000001", "term": condition}]},
            }
        stored.raw_payload = record
    session.flush()

    descriptors = folder / "desc2026.xml"
    descriptors.write_text(
        "<DescriptorRecordSet>"
        "<DescriptorRecord><DescriptorUI>D009369</DescriptorUI>"
        "<DescriptorName><String>Neoplasms</String></DescriptorName>"
        "<TreeNumberList><TreeNumber>C04</TreeNumber></TreeNumberList></DescriptorRecord>"
        "<DescriptorRecord><DescriptorUI>D000001</DescriptorUI>"
        "<DescriptorName><String>Example Neoplasm</String></DescriptorName>"
        "<TreeNumberList><TreeNumber>C04.200</TreeNumber></TreeNumberList></DescriptorRecord>"
        "</DescriptorRecordSet>",
        encoding="utf-8",
    )
    return descriptors


def test_draft_batch_reuses_a_verified_alias_and_replays_without_writing_twice(
    session: Session, invoke, tmp_path: Path
):
    descriptors = eligible_set(session, tmp_path)
    existing = add_claim(
        session,
        slug="existing-claim",
        headline="An article heading",
        summary="An example.",
        vertical="cancer",
        intervention="Example Oral Tablet",
        indication="Example Neoplasm",
    )
    entity = session.scalar(
        select(Entity).where(Entity.claim_id == existing.id, Entity.type == EntityType.INTERVENTION)
    )
    assert entity is not None
    entity.synonyms = ["Z-231"]
    add_article(
        session,
        existing.slug,
        url="https://example.com/fixture-study",
        outlet="Example News",
        title="An article heading",
        published_date=date(2026, 11, 16),
    )
    record_decision(existing, ReviewState.APPROVED, by=Decider.HUMAN, now=datetime.now(UTC))
    session.add(
        LlmUsage(
            purpose="decision:entity_match",
            model="openai:fixture",
            input_tokens=25,
            output_tokens=10,
            cost_usd=Decimal("0.020000"),
            created_at=datetime.now(UTC),
        )
    )
    session.flush()
    args = (
        REGISTRY_CLAIMS_2026,
        "--batch",
        "sandbox-batch",
        "--limit",
        "2",
        "--mesh-descriptors",
        str(descriptors),
    )
    first = invoke(*args)
    assert first.exit_code == 0, first.output
    first = json.loads(first.output)
    assert first["trial_count"] == 5
    assert first["held_groups_by_reason"] == {
        "existing_claim_needs_verification": 1,
        "vertical_needs_review": 1,
    }
    assert len(first["actions"]) == 1
    assert session.scalar(select(func.count()).select_from(Claim)) == 1

    [candidate] = first["existing_claim_candidates"]
    verified_id = "NCT00000003"
    attestation = {
        "group_id": candidate["group_id"],
        "trial_id": verified_id,
        "slug": existing.slug,
        "trial_sha256": candidate["trial_sha256"][verified_id],
        "claim_sha256": candidate["claim_sha256"][existing.slug],
        "reviewed_by": "fixture assistant",
        "reason": "Fixture verifies identity and indication.",
    }
    links = tmp_path / "verified.json"
    links.write_text(json.dumps({"schema_version": 1, "links": [attestation]}), encoding="utf-8")
    args += ("--verified-links", str(links))
    checked = invoke(*args)
    assert checked.exit_code == 0, checked.output
    preview = json.loads(checked.output)
    assert [row["operation"] for row in preview["actions"]] == ["draft", "nominate"]
    assert preview["actions"][0]["trial_ids"] == ["NCT00000001", "NCT00000002"]
    assert preview["actions"][1]["trial_ids"] == [verified_id]
    assert "NCT00000004" in next(
        row["trials"]
        for row in preview["held_groups"]
        if row["reason"] == "existing_claim_needs_verification"
    )
    assert Decimal(preview["preparation_estimate"]["known_candidate_match_cost_usd"]) == Decimal(
        "0.04"
    )
    assert session.get(AuditBatch, "sandbox-batch") is None

    refusal = invoke(*args, "--apply-plan", first["apply_plan"])
    assert refusal.exit_code == 1 and "plan changed" in refusal.output
    assert session.scalars(select(Claim)).all() == [existing]
    assert not existing.registry_candidate_trial_ids

    original_summary = existing.summary
    existing.summary = "A changed interpretation of the first report."
    session.flush()
    stale = invoke(*args, "--apply-plan", preview["apply_plan"])
    assert stale.exit_code == 1 and "changed. Review it again." in stale.output
    assert not existing.registry_candidate_trial_ids
    existing.summary = original_summary
    session.flush()

    applied = invoke(*args, "--apply-plan", preview["apply_plan"])
    assert applied.exit_code == 0, applied.output
    receipt = json.loads(applied.output)
    assert receipt["nominated"] == {existing.slug: [verified_id]}
    [slug] = receipt["drafted"]
    claim = session.scalar(select(Claim).where(Claim.slug == slug))
    assert claim and claim.drafting_trial_ids == ["NCT00000001", "NCT00000002"]
    assert claim.drafted_from is DraftedFrom.REGISTRY and claim.review_state is ReviewState.PENDING
    assert claim.audit_batch == "sandbox-batch" and claim.headline is None
    assert not articles_of(session, claim)
    assert not session.scalars(select(EntityMatch)).all()

    repeated = invoke(*args, "--apply-plan", preview["apply_plan"])
    assert repeated.exit_code == 0, repeated.output
    repeated_report = json.loads(repeated.output)
    assert repeated_report["outcome"] == "already_applied"
    assert repeated_report["drafted"] == [] and repeated_report["nominated"] == {}
    assert existing.registry_candidate_trial_ids == [verified_id]
    assert session.scalar(select(func.count()).select_from(Claim)) == 2

    new_batch = invoke(
        REGISTRY_CLAIMS_2026, "--batch", "next-batch", "--mesh-descriptors", str(descriptors)
    )
    assert new_batch.exit_code == 0, new_batch.output
    assert json.loads(new_batch.output)["actions"] == []


def test_draft_refuses_unknown_sets_and_archived_duplicates(
    session: Session, invoke, tmp_path: Path
):
    refused = invoke("unknown-set", "--batch", "invalid")
    assert refused.exit_code == 1 and REGISTRY_CLAIMS_2026 in refused.output
    descriptors = eligible_set(session, tmp_path)
    archived = add_registry_claim(
        session,
        slug="archived-claim",
        vertical="cancer",
        intervention="Alpha XR + Beta",
        indication="Example Neoplasm",
        trial_ids=["NCT00000001"],
    )
    archived.archived_at = datetime.now(UTC)
    archived.archive_reason = "Fixture."
    session.flush()
    preview = invoke(
        REGISTRY_CLAIMS_2026, "--batch", "archive", "--mesh-descriptors", str(descriptors)
    )
    assert preview.exit_code == 0, preview.output
    assert json.loads(preview.output)["held_groups_by_reason"]["existing_claim_unavailable"] == 1
