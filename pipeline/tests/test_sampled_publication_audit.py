"""The writer draws and releases publication audits, backed by real database rows."""

import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from backfill_support import add_trials
from store_support import STORE_SQL, assert_same_export, store_of
from test_export import add_event, add_match
from thenwhat.claims.audit import (
    AuditOpinion,
    judge_claim,
    register_audit_batch,
    release_batch,
    sample_batch,
)
from thenwhat.claims.entry import AuditRefused, add_registry_claim
from thenwhat.cli import app
from thenwhat.db.models import AuditJudgement, AuditSample, Claim
from thenwhat.domain import Decider, ReviewState
from thenwhat.review.decisions import record_decision
from thenwhat.store.build import merge_into
from thenwhat.store.records import claim_actions

NOW = datetime(2026, 11, 18, tzinfo=UTC)
BATCH = "registry-audit-fixture"


def held_batch(session: Session, size: int) -> dict[str, Claim]:
    register_audit_batch(session, BATCH)
    claims = {}
    trials = add_trials(session, size, registry="clinicaltrials.gov")
    for index, trial in enumerate(trials, 1):
        trial.external_id = f"NCT{index:08d}"
        session.flush()
        slug = f"fixture-{index}"
        claim = add_registry_claim(
            session,
            slug=slug,
            intervention=f"Example gel {index}",
            indication="enamel loss",
            vertical="mouth-and-teeth",
            trial_ids=[trial.external_id],
            audit_batch=BATCH,
        )
        record_decision(claim, ReviewState.APPROVED, by=Decider.RULE, now=NOW)
        claim.awaiting_audit_at = NOW
        claims[slug] = claim
    session.flush()
    return claims


@pytest.fixture
def invoke(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.delenv("AUDIT_MAX_WRONG_SHARE", raising=False)
    runner = CliRunner()
    return lambda *args: runner.invoke(app, ["audit", *args])


def test_completed_partial_sample_releases_at_the_limit_and_transfers_the_hold(
    session: Session, invoke, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    claims = held_batch(session, 6)
    evidence = []
    for claim in claims.values():
        (trial_id,) = claim.drafting_trial_ids
        evidence.append(add_match(session, claim, trial_id, 0.99, ReviewState.APPROVED))
        evidence.append(
            add_event(
                session,
                claim.slug,
                external_id=trial_id,
                source_url=f"https://clinicaltrials.gov/study/{trial_id}",
            )
        )
    decisions = [(row.review_state, row.reviewed_by, row.reviewed_at) for row in evidence]
    store, _ = store_of(session, tmp_path / "store", NOW)
    store.close()
    monkeypatch.setenv("AUDIT_SAMPLE_SIZE", "4")
    first = invoke("sample", "--batch", BATCH)
    assert first.exit_code == 0, first.output
    receipt = json.loads(first.output)
    assert receipt["population"] == 6 and len(receipt["claims"]) == 4 and receipt["seed"]
    monkeypatch.setenv("AUDIT_SAMPLE_SIZE", "2")
    assert json.loads(invoke("sample", "--batch", BATCH).output) == receipt
    sample_id = str(receipt["sample"])
    wrong, *right = receipt["claims"]

    legacy = invoke("clear", wrong)
    assert legacy.exit_code == 1 and "--batch" in legacy.output
    incomplete = invoke("clear", "--batch", BATCH)
    assert incomplete.exit_code == 1 and "4 sampled claims" in incomplete.output

    rejected = invoke(
        "judge",
        sample_id,
        wrong,
        "--wrong",
        "--reviewer",
        "fixture-person",
        "--category",
        "indication",
        "--detail",
        "Trial tests a different indication.",
    )
    assert rejected.exit_code == 0, rejected.output
    for slug in right:
        verdict = invoke("judge", sample_id, slug, "--right", "--reviewer", "fixture-person")
        assert verdict.exit_code == 0, verdict.output

    unset = invoke("clear", "--batch", BATCH)
    assert unset.exit_code == 1 and "AUDIT_MAX_WRONG_SHARE" in unset.output
    monkeypatch.setenv("AUDIT_MAX_WRONG_SHARE", "0.2499")
    above = invoke("clear", "--batch", BATCH)
    assert above.exit_code == 1 and "1 of 4" in above.output and "indication: 1" in above.output
    assert all(claim.awaiting_audit_at is not None for claim in claims.values())
    fresh = invoke("sample", "--batch", BATCH, "--fresh")
    assert fresh.exit_code == 1 and "Correct or archive" in fresh.output

    monkeypatch.setenv("AUDIT_MAX_WRONG_SHARE", "0.25")
    clear = invoke("clear", "--batch", BATCH)
    assert clear.exit_code == 0 and "Cleared 5 claims" in clear.output
    wrong_claim = claims[wrong]
    assert wrong_claim.archived_at is not None and wrong_claim.awaiting_audit_at is not None
    for claim in claims.values():
        assert (claim.review_state, claim.reviewed_by, claim.reviewed_at) == (
            ReviewState.APPROVED,
            Decider.RULE,
            NOW,
        )
        if claim.slug != wrong:
            assert claim.awaiting_audit_at is None
    sample = session.get(AuditSample, receipt["sample"])
    assert sample is not None and sample.released_at is not None
    assert sample.max_wrong_share == Decimal("0.25")
    assert decisions == [(row.review_state, row.reviewed_by, row.reviewed_at) for row in evidence]

    actions = [
        action
        for claim in claims.values()
        for action in claim_actions(claim, [], {})
        if action.body["action"] == "audit_clear"
    ]
    assert len(actions) == 5
    store_path = tmp_path / "store" / "store.db"
    merge_into(
        store_path, [("clear-fixture", actions)], store_sql=STORE_SQL, now=NOW + timedelta(1)
    )
    with sqlite3.connect(store_path) as db:
        assert db.execute(
            "SELECT slug FROM claim WHERE awaiting_audit_at IS NOT NULL"
        ).fetchall() == [(wrong,)]
        assert db.execute(
            "SELECT count(*) FROM claim_action WHERE action = 'audit_clear' AND decided_by = 'rule'"
        ).fetchone() == (5,)

    export = assert_same_export(session, tmp_path / "release-export", NOW + timedelta(1))
    assert {row["slug"] for row in export["claims"]} == set(claims) - {wrong}
    assert all(row["checked_by_person"] is False for row in export["claims"])


def test_small_batch_uses_every_claim_and_counts_operator_disagreements(
    session: Session, invoke, monkeypatch: pytest.MonkeyPatch
):
    claims = held_batch(session, 2)
    monkeypatch.setenv("AUDIT_SAMPLE_SIZE", "100")
    sample = json.loads(invoke("sample", "--batch", BATCH).output)
    assert sample["population"] == 2 and len(sample["claims"]) == 2
    first, second = sample["claims"]
    identifier = str(sample["sample"])
    for claim, right in ((first, True), (second, False)):
        arguments = [
            "judge",
            identifier,
            claim,
            "--reviewer",
            "fixture-assistant",
            "--as-assistant",
        ]
        arguments += (
            ["--right"] if right else ["--wrong", "--category", "vertical", "--detail", "Fixture."]
        )
        assert invoke(*arguments).exit_code == 0
    before = invoke("clear", "--batch", BATCH)
    assert before.exit_code == 1 and "operator spot-check" in before.output
    offered = json.loads(invoke("spot-check", "--batch", BATCH, "--size", "2").output)
    assert offered["claims"] == list(claims) and offered["checked"] == offered["differed"] == 0
    assert (
        invoke(
            "judge",
            identifier,
            first,
            "--wrong",
            "--reviewer",
            "fixture-person",
            "--category",
            "duplicate",
            "--detail",
            "Fixture.",
        ).exit_code
        == 0
    )
    pending = invoke("clear", "--batch", BATCH)
    assert pending.exit_code == 1 and "1 spot-check" in pending.output
    assert (
        invoke("judge", identifier, second, "--right", "--reviewer", "fixture-person").exit_code
        == 0
    )
    checked = json.loads(invoke("spot-check", "--batch", BATCH).output)
    assert checked["checked"] == checked["differed"] == 2
    assert checked["seed"] == offered["seed"]
    for role in (Decider.HUMAN, Decider.ASSISTANT):
        assert session.get(AuditJudgement, (sample["sample"], claims[second].id, role))
    clear = invoke("clear", "--batch", BATCH)
    assert clear.exit_code == 0 and "Cleared 1 claim" in clear.output
    assert claims[first].awaiting_audit_at is not None and claims[first].archived_at is not None
    assert claims[second].awaiting_audit_at is None and claims[second].archived_at is None


def test_a_changed_claim_requires_a_fresh_audit_sample(session: Session):
    claims = held_batch(session, 2)
    first = sample_batch(session, BATCH, size=None, whole=True, fresh=False, now=NOW)
    opinion = AuditOpinion(True, Decider.HUMAN, "fixture-person", None, None)
    for slug in claims:
        judge_claim(session, first.id, slug, opinion, now=NOW)
    changed = claims["fixture-1"]
    changed.indication = "a different condition"
    session.flush()
    with pytest.raises(AuditRefused, match="changed since judgement"):
        release_batch(session, BATCH, max_wrong_share=None, now=NOW)
    fresh = sample_batch(session, BATCH, size=None, whole=True, fresh=True, now=NOW)
    assert fresh.id != first.id and fresh.seed != first.seed
    assert all(claim.awaiting_audit_at for claim in claims.values())
