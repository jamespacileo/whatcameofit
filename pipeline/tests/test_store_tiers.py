"""The store in two tiers: the hot one for D1, the bulk one kept as a file."""

import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session
from typer.testing import CliRunner

from test_store_records import STORE, _world
from thenwhat.cli import app
from thenwhat.store.build import build
from thenwhat.store.form import Record, payload_of
from thenwhat.store.tiers import (
    BULK,
    HOT,
    TIER,
    checksums,
    fingerprint_sql,
    hash_of,
    hot_records,
    in_tier,
    references,
    split_build,
    tables,
    tier_of,
    tier_path,
)


def _schema() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.executescript((STORE / "schema.sql").read_text())
    return db


def test_every_table_has_a_tier_and_no_hot_table_references_a_bulk_one():
    db = _schema()
    assert set(tables(db)) == set(TIER)
    for table, column, parent in references(db):
        if in_tier(table, HOT):
            assert in_tier(parent, HOT), f"{table}.{column} references {parent}, a bulk table"


def test_a_build_splits_into_a_hot_and_a_bulk_file(session: Session, tmp_path: Path):
    world = _world(session)
    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    build(session, file, payloads=payloads, store_sql=STORE, now=datetime(2026, 11, 17, tzinfo=UTC))
    hot, bulk = split_build(file, payloads, "both")
    assert (hot, bulk) == (tier_path(file, HOT), tier_path(file, BULK)) and not file.exists()

    hot_db, bulk_db = sqlite3.connect(hot), sqlite3.connect(bulk)
    # Each holds its own tier's rows, the run tables in both.
    for table in tables(hot_db):
        if table.endswith("_fts") or table == "payload":
            continue
        rows_hot = hot_db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        rows_bulk = bulk_db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        if tier_of(table) == HOT:
            assert rows_bulk == 0, table
        elif tier_of(table) == BULK:
            assert rows_hot == 0, table
    assert hot_db.execute("SELECT count(*) FROM claim").fetchone()[0] == 4
    assert bulk_db.execute("SELECT count(*) FROM registry_trial").fetchone()[0] == 2
    assert (
        hot_db.execute("SELECT count(*) FROM run").fetchone()
        == bulk_db.execute("SELECT count(*) FROM run").fetchone()
    )
    # Nothing in the hot file names a row it does not hold.
    assert hot_db.execute("PRAGMA foreign_key_check").fetchall() == []
    # A payload goes with what points at it: the event's to the hot file, the trials' to
    # the bulk one; the large object to the hot tier's folder.
    big = payload_of(world["big_payload"])
    hot_payloads = {sha for (sha,) in hot_db.execute("SELECT sha256 FROM payload")}
    bulk_payloads = {sha for (sha,) in bulk_db.execute("SELECT sha256 FROM payload")}
    assert big.sha256 in hot_payloads and big.sha256 not in bulk_payloads
    trial_payloads = {s for (s,) in bulk_db.execute("SELECT payload_sha256 FROM registry_trial")}
    assert trial_payloads <= bulk_payloads and not trial_payloads & hot_payloads
    assert (payloads / HOT / big.r2_key).read_text() == big.text
    assert not (payloads / "payload").exists()
    # The search over trials answers in the bulk file.
    assert (
        bulk_db.execute(
            "SELECT count(*) FROM registry_trial_fts WHERE registry_trial_fts MATCH 'trial'"
        ).fetchone()[0]
        > 0
    )
    assert hot_db.execute("SELECT count(*) FROM registry_trial_fts").fetchone()[0] == 0


def test_a_checksum_is_the_same_from_the_file_and_from_d1s_answer(tmp_path: Path):
    path = tmp_path / "s.sqlite"
    db = sqlite3.connect(path)
    db.executescript((STORE / "schema.sql").read_text())
    db.execute(
        "INSERT INTO run (id, writer, device, commit_sha, registered_at)"
        " VALUES ('r', 'migration', 'd', 'abc1234', '2026-11-17T00:00:00.000000+00:00')"
    )
    db.execute(
        "INSERT INTO outlet_icon VALUES ('a.example', 'https://a.example/i.png', 'image/png',"
        " X'89504e47', '2026-11-17T00:00:00.000000+00:00', 'r')"
    )
    db.commit()
    (icons,) = [c for c in checksums(path, HOT) if c.table == "outlet_icon"]
    assert icons.rows == 1
    # D1 answers a SELECT as JSON objects keyed by the column names.
    cursor = db.execute(fingerprint_sql(db, "outlet_icon"))
    names = [d[0] for d in cursor.description]
    answer = [{"results": [dict(zip(names, cursor.fetchone(), strict=True))], "success": True}]
    from thenwhat.store.tiers import answer_row

    assert hash_of(answer_row(answer)) == icons.sha256
    # A value changed in length, or at its first character, changes the checksum.
    for change in ("domain = 'b.example'", "media_type = 'image/gif'", "content = X'89504e'"):
        copy = tmp_path / "copy.sqlite"
        shutil.copyfile(path, copy)
        other = sqlite3.connect(copy)
        other.execute(f"UPDATE outlet_icon SET {change}")
        other.commit()
        (changed,) = [c for c in checksums(copy, HOT) if c.table == "outlet_icon"]
        assert changed.sha256 != icons.sha256, change


def test_a_push_to_d1_hands_over_hot_kinds_and_their_payloads():
    event_payload = Record("payload", "e" * 64, {"sha256": "e" * 64})
    event = Record("evidence_event", "x|k", {"payload_sha256": "e" * 64})
    trial_payload = Record("payload", "t" * 64, {"sha256": "t" * 64})
    trial = Record("registry_trial", "ct|1", {"payload_sha256": "t" * 64})
    lead = Record("link_lead", "a.example/x", {})
    claim = Record("claim", "x", {})
    hot, left_out = hot_records([claim, event_payload, event, trial_payload, trial, lead])
    assert hot == [claim, event_payload, event] and left_out == 3


def test_store_checksum_compares_with_d1_and_refuses_a_difference(tmp_path: Path):
    path = tmp_path / "s.sqlite"
    db = sqlite3.connect(path)
    db.executescript((STORE / "schema.sql").read_text())
    db.commit()
    sql_file = tmp_path / "sql.json"
    passed = CliRunner().invoke(
        app, ["store", "checksum", str(path), "--tier", "hot", "--sql", str(sql_file)]
    )
    assert passed.exit_code == 0, passed.output
    statements = json.loads(sql_file.read_text())
    answers = {}
    for table, sql in statements.items():
        cursor = db.execute(sql)
        names = [d[0] for d in cursor.description]
        answers[table] = [{"results": [dict(zip(names, cursor.fetchone(), strict=True))]}]
    (tmp_path / "d1.json").write_text(json.dumps(answers))
    same = CliRunner().invoke(
        app,
        ["store", "checksum", str(path), "--tier", "hot", "--against", str(tmp_path / "d1.json")],
    )
    assert same.exit_code == 0 and "DIFFERS" not in same.output
    answers["claim"][0]["results"][0]["c0"] = 1
    (tmp_path / "d1.json").write_text(json.dumps(answers))
    differs = CliRunner().invoke(
        app,
        ["store", "checksum", str(path), "--tier", "hot", "--against", str(tmp_path / "d1.json")],
    )
    assert differs.exit_code == 1 and "claim" in differs.output
