"""Waiting work survives a bulk build, a restore, and a merge into an older snapshot."""

import json
import sqlite3
from contextlib import closing
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select, true
from sqlalchemy.orm import Session

from claim_support import NOW, Sources, Targets, entry, new_claim, prepare
from test_store_records import STORE, T0, _claim
from thenwhat.claimsteps.evidence import ClaimFetch
from thenwhat.db.models import WorkEntry
from thenwhat.domain import WorkOutcome
from thenwhat.store.build import apply_delta, base_of, build, merge_into, write_delta
from thenwhat.store.form import Record, when
from thenwhat.store.gather import gather
from thenwhat.store.place import place, place_row
from thenwhat.store.records import work_entry_record
from thenwhat.store.rows import work_entry_row
from thenwhat.work.ledger import due_records


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
