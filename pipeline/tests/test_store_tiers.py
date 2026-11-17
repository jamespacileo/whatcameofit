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
    MAX_COLUMNS,
    REFERENCE,
    TIER,
    checksums,
    fingerprint_parts,
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
        if tier_of(table) == HOT and table not in REFERENCE:
            assert rows_bulk == 0, table
        elif tier_of(table) == BULK:
            assert rows_hot == 0, table
    assert hot_db.execute("SELECT count(*) FROM claim").fetchone()[0] == 4
    assert bulk_db.execute("SELECT count(*) FROM registry_trial").fetchone()[0] == 2
    assert (
        hot_db.execute("SELECT count(*) FROM run").fetchone()
        == bulk_db.execute("SELECT count(*) FROM run").fetchone()
    )
    # Neither file names a row it does not hold.
    assert hot_db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert bulk_db.execute("PRAGMA foreign_key_check").fetchall() == []
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
    (statement,) = fingerprint_parts(db, "outlet_icon")
    cursor = db.execute(statement)
    names = [d[0] for d in cursor.description]
    answer = [{"results": [dict(zip(names, cursor.fetchone(), strict=True))], "success": True}]
    from thenwhat.store.tiers import answer_row

    assert hash_of([answer_row(answer)]) == icons.sha256
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
    for table, parts in statements.items():
        answers[table] = []
        for sql in parts:
            cursor = db.execute(sql)
            names = [d[0] for d in cursor.description]
            answers[table].append([{"results": [dict(zip(names, cursor.fetchone(), strict=True))]}])
    (tmp_path / "d1.json").write_text(json.dumps(answers))
    same = CliRunner().invoke(
        app,
        ["store", "checksum", str(path), "--tier", "hot", "--against", str(tmp_path / "d1.json")],
    )
    assert same.exit_code == 0 and "DIFFERS" not in same.output
    answers["claim"][0][0]["results"][0]["c0"] = 1
    (tmp_path / "d1.json").write_text(json.dumps(answers))
    differs = CliRunner().invoke(
        app,
        ["store", "checksum", str(path), "--tier", "hot", "--against", str(tmp_path / "d1.json")],
    )
    assert differs.exit_code == 1 and "claim" in differs.output


def test_the_day_s_bulk_records_merge_into_the_bulk_file_and_replay_from_the_delta(
    session: Session, tmp_path: Path
):
    from sqlalchemy import select

    from thenwhat.db.models import LinkLead, LinkShare
    from thenwhat.store.build import BUILD_ID_SQL, merge_into, read_delta, write_delta
    from thenwhat.store.gather import Gathered, stream
    from thenwhat.store.push import increment
    from thenwhat.store.tiers import bulk_records, checks

    _world(session)
    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    report = build(
        session, file, payloads=payloads, store_sql=STORE, now=datetime(2026, 11, 17, tzinfo=UTC)
    )
    _, bulk = split_build(file, payloads, "both")
    kept_copy = tmp_path / "downloaded.sqlite"
    shutil.copyfile(bulk, kept_copy)
    # The bulk file holds the claims its leads hang from.
    assert sqlite3.connect(bulk).execute("SELECT count(*) FROM claim").fetchone()[0] == 4
    # The build is named in both files and in D1 by the same query.
    assert sqlite3.connect(bulk).execute(BUILD_ID_SQL).fetchone() == (report.build_id,)
    assert checks(tier_path(file, HOT), HOT)["build"] == report.build_id

    # A day later: a new share of the stored lead.
    lead = session.scalars(select(LinkLead).where(LinkLead.triage_score.is_not(None))).first()
    assert lead is not None
    session.add(
        LinkShare(
            link_lead_id=lead.id,
            platform="reddit",
            community="medicine",
            shared_at=datetime(2026, 11, 18, tzinfo=UTC),
            score=5,
        )
    )
    session.flush()
    records, _ = bulk_records(stream(session, Gathered(records=[])))
    day = increment(records, report.state, actions=True).records
    assert [r.kind for r in day] == ["link_share"]
    merge_into(bulk, day, store_sql=STORE, now=datetime(2026, 11, 18, tzinfo=UTC), name="bulk-1")
    shares = "SELECT count(*) FROM link_share"
    assert sqlite3.connect(bulk).execute(shares).fetchone()[0] == 3

    # The bulk tier's restore: the kept file and the day's delta.
    delta = tmp_path / "delta.jsonl.gz"
    write_delta(delta, day)
    merge_into(
        kept_copy,
        read_delta(delta),
        store_sql=STORE,
        now=datetime(2026, 11, 18, tzinfo=UTC),
        name="bulk-1",
    )
    assert [c.sha256 for c in checksums(kept_copy, BULK) if c.table == "link_share"] == [
        c.sha256 for c in checksums(bulk, BULK) if c.table == "link_share"
    ]


def test_the_checks_file_holds_each_table_s_sql_and_the_row_it_must_give(tmp_path: Path):
    from thenwhat.store.tiers import checks

    path = tmp_path / "s.sqlite"
    db = sqlite3.connect(path)
    db.executescript((STORE / "schema.sql").read_text())
    db.commit()
    found = checks(path, HOT)
    assert found["build"] is None
    for table, check in found["tables"].items():
        for part in check["parts"]:
            cursor = db.execute(part["sql"])
            names = [d[0] for d in cursor.description]
            assert dict(zip(names, cursor.fetchone(), strict=True)) == part["expected"], table
            assert len(part["sql"].encode()) < 100_000
    assert "registry_trial" not in found["tables"] and "claim" in found["tables"]


def test_every_kind_gather_gives_is_of_one_tier():
    from test_store_records import KINDS
    from thenwhat.store.tiers import BULK_KINDS, HOT_KINDS

    assert not HOT_KINDS & BULK_KINDS
    assert set(KINDS) - {"payload"} <= HOT_KINDS | BULK_KINDS


def test_the_inbox_folds_into_the_bulk_file_once_and_is_cleared_after(
    session: Session, tmp_path: Path
):
    import httpx

    from thenwhat.store.inbox import clear, fold

    _world(session)
    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    build(session, file, payloads=payloads, store_sql=STORE, now=datetime(2026, 11, 17, tzinfo=UTC))
    _, bulk = split_build(file, payloads, "both")
    day = "2026-11-18"
    lead = {
        "url_key": "news.example.com/new",
        "url_key_version": 2,
        "url": "https://news.example.com/new",
        "outlet": "news.example.com",
        "outlet_kind": "general_news",
        "title": "New",
        "first_shared_at": f"{day}T00:00:00.000000+00:00",
        "origin": "reader",
        "screen_outcome": "in_scope",
    }
    asked = {"platform": "reader", "community": "reader", "shared_at": day, "score": 0}
    share = {"lead_url_key": "news.example.com/new", **asked}
    old = {"lead_url_key": "news.example.com/drug-x", **asked}
    inbox = [
        {"seq": 1, "run": "r1", "kind": "link_lead", "key": lead["url_key"], "body": lead},
        {
            "seq": 2,
            "run": "r1",
            "kind": "link_share",
            "key": "news.example.com/new|reader",
            "body": share,
        },
        {
            "seq": 3,
            "run": "r2",
            "kind": "link_share",
            "key": "news.example.com/drug-x|reader",
            "body": old,
        },
    ]
    cleared: list[int] = []

    def service(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/inbox":
            after = int(request.url.params["after"])
            records = [r for r in inbox if int(str(r["seq"])) > after]
            return httpx.Response(200, json={"records": records, "through": 3, "more": False})
        cleared.append(json.loads(request.content)["through"])
        return httpx.Response(200, json={"cleared": 3, "rows_removed": 3, "left": 0})

    with httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(service)) as c:
        folded = fold(c, bulk, store_sql=STORE, now=datetime(2026, 11, 19, tzinfo=UTC))
        again = fold(c, bulk, store_sql=STORE, now=datetime(2026, 11, 19, tzinfo=UTC))
        clear(c, folded.through)
    assert (folded.runs, folded.through, len(folded.records)) == (2, 3, 3)
    assert again.runs == 0 and len(again.records) == 3
    db = sqlite3.connect(bulk)
    assert db.execute(
        "SELECT count(*) FROM link_lead WHERE url_key = 'news.example.com/new'"
    ).fetchone() == (1,)
    assert db.execute("SELECT count(*) FROM link_share WHERE platform = 'reader'").fetchone() == (
        2,
    )
    assert cleared == [3]


def test_fold_inbox_refuses_without_the_service(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    monkeypatch.delenv("INGEST_URL", raising=False)
    bulk = tmp_path / "b.sqlite"
    sqlite3.connect(bulk).close()
    result = CliRunner().invoke(
        app, ["store", "fold-inbox", str(bulk), "--delta", str(tmp_path / "d.jsonl.gz")]
    )
    assert result.exit_code == 1 and "INGEST_TOKEN" in result.output


def test_no_check_asks_d1_for_more_columns_than_it_answers():
    db = _schema()
    widest = 0
    for table in tables(db):
        if table.endswith("_fts"):
            continue
        parts = fingerprint_parts(db, table)
        numbers = []
        for sql in parts:
            columns = db.execute(sql).description
            assert len(columns) <= MAX_COLUMNS, table
            numbers += [int(column[0][1:]) for column in columns]
        assert numbers == list(range(len(numbers))), table
        widest = max(widest, len(numbers))
    # The schema has tables wide enough to need more than one statement.
    assert widest > MAX_COLUMNS
