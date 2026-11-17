"""Waiting work stays due at the same time after replay onto an older bulk store."""

import json
import sqlite3
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select, true
from sqlalchemy.orm import Session

from test_store_records import STORE, T0, _claim
from thenwhat.claimsteps.evidence import ClaimFetch
from thenwhat.db.models import WorkEntry
from thenwhat.store.build import apply_delta, base_of, write_delta
from thenwhat.store.form import Record
from thenwhat.store.place import place_row
from thenwhat.store.records import work_entry_record
from thenwhat.store.rows import work_entry_row
from thenwhat.work.ledger import due_records


def test_waiting_claims_survive_replay_onto_a_pre_runner_store(session: Session, tmp_path: Path):
    store = tmp_path / "old.sqlite"
    with sqlite3.connect(store) as db:
        for path in sorted((STORE / "ingest/migrations").glob("*.sql")):
            if path.name.startswith("0008_"):
                break
            db.executescript(path.read_text())
        db.execute(
            "INSERT INTO run (id, writer, commit_sha, registered_at)"
            " VALUES ('old', 'migration', 'fixture', '2026-03-01')"
        )
        db.execute(
            "INSERT INTO work_entry VALUES"
            " ('claim','older','claim_fetch',1,'done',1,0,'old',0,NULL,'2026-03-01','old')"
        )

    step = ClaimFetch(
        threshold=0.8, no_signal_years=3, paper_max_age=timedelta(days=1), claims=true()
    )
    retry = T0 + timedelta(hours=2)
    records = []
    for slug, outcome in (("waiting", "later"), ("repair", "needs_fix")):
        claim = _claim(slug)
        session.add(claim)
        session.flush()
        entry = WorkEntry(
            record_kind="claim",
            record_id=claim.id,
            step=step.name,
            step_version=1,
            outcome=outcome,
            attempts=0,
            requests_used=1,
            fingerprint="same",
            reason="source_failed",
            reason_values={"status": 503, "source": "registry"},
            last_attempt_at=T0,
            not_before=retry if outcome == "later" else None,
            first_put_off_at=T0 - timedelta(hours=1),
        )
        session.add(entry)
        session.flush()
        records.append(work_entry_record(entry, record_key=slug))

    def due():
        return [
            [c.slug for c in session.scalars(due_records(step, 3, now=at))]
            for at in (retry - timedelta(microseconds=1), retry, retry + timedelta(hours=2))
        ]

    assert due() == [[], ["waiting"], ["waiting"]]
    runs = [("waiting-claims", records)]
    delta = tmp_path / "work.jsonl.gz"
    write_delta(delta, runs, base=base_of(store, runs))
    assert apply_delta(store, delta, store_sql=STORE, now=T0) == ["waiting-claims-0"]
    assert apply_delta(store, delta, store_sql=STORE, now=T0) == []
    session.execute(delete(WorkEntry))
    with sqlite3.connect(store) as db:
        db.row_factory = sqlite3.Row
        assert tuple(
            db.execute(
                "SELECT outcome,reason,not_before FROM work_entry WHERE record_key='older'"
            ).fetchone()
        ) == ("done", None, None)
        for record in records:
            body = dict(
                db.execute(
                    "SELECT * FROM work_entry WHERE record_key = ?", (record.body["record_key"],)
                ).fetchone()
            )
            body["reason_values"] = json.loads(body["reason_values"])
            placed = place_row(session, work_entry_row(Record("work_entry", record.key, body)))
            assert isinstance(placed, WorkEntry)
            assert work_entry_record(placed, record_key=body["record_key"]) == record
    assert session.scalars(select(WorkEntry)).all()
    assert due() == [[], ["waiting"], ["waiting"]]
