"""Waiting work survives a bulk build, a restore, and a merge into an older snapshot."""

import json
import sqlite3
from contextlib import closing
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from claim_support import NOW, Sources, Targets, entry, new_claim, prepare
from test_store_records import STORE
from thenwhat.db.models import WorkEntry
from thenwhat.domain import WorkOutcome
from thenwhat.store.build import build, merge_into
from thenwhat.store.form import Record, when
from thenwhat.store.gather import gather
from thenwhat.store.place import place


def test_the_store_keeps_waiting_claims_and_their_retry_information(
    session: Session, tmp_path: Path
):
    claim = new_claim(session)
    prepare(session, Sources(targets=Targets(drugs_down=True)))
    papers = entry(session, "claim_papers", claim)
    terms = entry(session, "claim_terms", claim)
    assert (papers.outcome, terms.outcome) == (WorkOutcome.NEEDS_FIX, WorkOutcome.LATER)
    assert terms.reason_values and terms.not_before and terms.first_put_off_at

    file = tmp_path / "store.db"
    build(session, file, payloads=tmp_path / "objects", store_sql=STORE, now=NOW)
    with closing(sqlite3.connect(file)) as db:
        assert db.execute(
            "SELECT outcome, reason, not_before FROM work_entry WHERE step = 'claim_papers'"
        ).fetchone() == ("needs_fix", papers.reason, None)
        details = db.execute(
            "SELECT outcome, reason, reason_values, not_before, first_put_off_at"
            " FROM work_entry WHERE step = 'claim_terms'"
        ).fetchone()
        assert details[:2] == ("later", terms.reason)
        assert json.loads(details[2]) == terms.reason_values
        assert details[3:] == (when(terms.not_before), when(terms.first_put_off_at))

    records = [record for record in gather(session).records if record.kind == "work_entry"]
    session.execute(delete(WorkEntry))
    place(session, records)
    restored = entry(session, "claim_terms", claim)
    assert (
        restored.reason,
        restored.reason_values,
        restored.not_before,
        restored.first_put_off_at,
    ) == (terms.reason, terms.reason_values, terms.not_before, terms.first_put_off_at)
    assert entry(session, "claim_papers", claim).reason == papers.reason


def test_merging_a_waiting_record_upgrades_an_existing_bulk_file(tmp_path: Path):
    file = tmp_path / "legacy.db"
    with closing(sqlite3.connect(file)) as db:
        for migration in sorted((STORE / "ingest/migrations").glob("*.sql")):
            if migration.name.startswith("0008_"):
                break
            db.executescript(migration.read_text())
        db.execute(
            "INSERT INTO run (id, writer, commit_sha, registered_at)"
            " VALUES ('old','device','abc',?)",
            (when(NOW),),
        )
        db.execute(
            "INSERT INTO work_entry"
            " VALUES ('claim','old','search',1,'failed',3,5,'abc',1,'down',?,'old')",
            (when(NOW),),
        )
        db.commit()

    waiting = Record(
        "work_entry",
        "claim|next|search|1",
        {
            "record_kind": "claim",
            "record_key": "next",
            "step": "search",
            "step_version": 1,
            "outcome": "later",
            "attempts": 0,
            "requests_used": 1,
            "fingerprint": "def",
            "last_attempt_at": when(NOW),
            "reason": "source_failed",
            "reason_values": {"status": 503},
            "not_before": when(NOW + timedelta(hours=1)),
            "first_put_off_at": when(NOW),
        },
    )
    merge_into(file, [("retry", [waiting])], store_sql=STORE, now=NOW)
    with closing(sqlite3.connect(file)) as db:
        assert db.execute(
            "SELECT outcome, attempts, requests_used, fingerprint, stale, error, last_attempt_at,"
            " changed_run, reason FROM work_entry WHERE record_key='old'"
        ).fetchone() == ("failed", 3, 5, "abc", 1, "down", when(NOW), "old", None)
        assert db.execute(
            "SELECT reason, json_extract(reason_values,'$.status'), not_before, first_put_off_at"
            " FROM work_entry WHERE record_key='next'"
        ).fetchone() == ("source_failed", 503, when(NOW + timedelta(hours=1)), when(NOW))
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
