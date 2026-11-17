"""The whole tracker built into one store file, as it is filled and restored in bulk."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from test_store_records import STORE, _world
from thenwhat.claims.corrections import moved_addresses
from thenwhat.cli import app
from thenwhat.db.models import RegistryTrial
from thenwhat.export.store_records import StoreRecords
from thenwhat.store import build as build_module
from thenwhat.store import dump as dump_module
from thenwhat.store.build import build
from thenwhat.store.form import payload_of


def test_the_whole_database_builds_into_one_store_file(session: Session, tmp_path: Path):
    world = _world(session)
    # A trial loaded before people's names were removed: its sponsor is a person.
    trial = session.scalars(
        select(RegistryTrial).where(RegistryTrial.external_id == "NCT07654321")
    ).one()
    trial.raw_payload = {
        "protocolSection": {
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": "Dr Jane Doe", "class": "INDIV"},
                "responsibleParty": {
                    "type": "SPONSOR_INVESTIGATOR",
                    "investigatorFullName": "Jane Doe",
                },
            }
        }
    }
    trial.lead_sponsor_name = "Dr Jane Doe"
    session.flush()

    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    report = build(
        session, file, payloads=payloads, store_sql=STORE, now=datetime(2026, 11, 17, tzinfo=UTC)
    )

    assert report.size == file.stat().st_size > 0
    assert report.handed["claim"] == 4 and report.added["claim"] == 4
    big = payload_of(world["big_payload"])
    assert (payloads / big.r2_key).read_text() == big.text
    assert report.payload_objects == 1

    db = sqlite3.connect(file)
    # The renamed claim is known by the slug it had; the merged one is archived and was
    # public.
    assert db.execute(
        "SELECT c.slug FROM claim_alias a JOIN claim c ON c.id = a.claim_id"
        " WHERE a.slug = 'drug-zz-for-melanoma'"
    ).fetchone() == ("drug-z-for-melanoma",)
    gone = db.execute(
        "SELECT merged_into IS NOT NULL, archived_at IS NOT NULL, published_at IS NOT NULL"
        " FROM claim WHERE slug = 'drug-x-tablets-for-melanoma'"
    ).fetchone()
    assert gone == (1, 1, 1)
    # No person is named.
    sponsor, held = db.execute(
        "SELECT t.lead_sponsor_name, p.body FROM registry_trial t"
        " JOIN payload p ON p.sha256 = t.payload_sha256 WHERE t.external_id = 'NCT07654321'"
    ).fetchone()
    assert sponsor is None and "Jane Doe" not in held
    assert json.loads(held)["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"] == {
        "class": "INDIV"
    }
    # Nothing staged is left behind.
    assert db.execute("SELECT count(*) FROM stg").fetchone() == (0,)


def test_the_dump_loads_into_a_database_with_the_schema_and_counts_check(
    session: Session, tmp_path: Path, monkeypatch
):
    _world(session)
    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    build(session, file, payloads=payloads, store_sql=STORE, now=datetime(2026, 11, 17, tzinfo=UTC))
    # Small limits, so that statements and files are cut.
    monkeypatch.setattr(dump_module, "STATEMENT_BYTES", 2_000)
    monkeypatch.setattr(dump_module, "FILE_BYTES", 6_000)
    out = tmp_path / "dump"
    manifest = dump_module.dump(file, out, payloads=payloads)

    names = sorted(p.name for p in out.glob("*.sql"))
    assert names == [entry["name"] for entry in manifest.files]
    assert names[-3:] == [
        f"{len(names) - 2:04d}_claim_fts.sql",
        f"{len(names) - 1:04d}_registry_trial_fts.sql",
        f"{len(names):04d}_link_lead_fts.sql",
    ]
    assert len([n for n in names if n.endswith("_claim.sql")]) >= 1
    for name in names:
        text = (out / name).read_text()
        assert "BEGIN" not in text and "COMMIT" not in text and "CREATE " not in text
        for statement in text.split(";\n"):
            assert len(statement.encode()) <= 2_000

    # Into a database holding only migration 0001, each file as one transaction.
    loaded = sqlite3.connect(tmp_path / "d1.sqlite", isolation_level=None)
    loaded.execute("PRAGMA foreign_keys = ON")
    loaded.executescript((STORE / "ingest" / "migrations" / "0001_store_schema.sql").read_text())
    for name in names:
        loaded.executescript("BEGIN;\n" + (out / name).read_text() + "COMMIT;\n")
    assert loaded.execute("PRAGMA foreign_key_check").fetchall() == []

    expected = json.loads((out / "manifest.json").read_text())
    query = dump_module.count_query(expected)
    row = loaded.execute(query.rstrip(";")).fetchone()
    columns = list(expected["tables"])
    answer = [{"results": [dict(zip(columns, row, strict=True))], "success": True}]
    assert dump_module.differences(expected, dump_module.counts_of(answer)) == []
    assert dump_module.differences(expected, {**dict(zip(columns, row, strict=True)), "claim": 0})
    # The search indexes answer as the built file's do.
    assert (
        loaded.execute(
            "SELECT count(*) FROM registry_trial_fts WHERE registry_trial_fts MATCH 'trial'"
        ).fetchone()
        == sqlite3.connect(file)
        .execute("SELECT count(*) FROM registry_trial_fts WHERE registry_trial_fts MATCH 'trial'")
        .fetchone()
    )
    assert (
        loaded.execute(
            "SELECT count(*) FROM claim_fts WHERE claim_fts MATCH 'melanoma'"
        ).fetchone()[0]
        > 0
    )


def test_store_check_passes_matching_counts_and_refuses_others(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"tables": {"claim": 2, "entity": 3}}))
    answer = tmp_path / "counts.json"
    answer.write_text(json.dumps([{"results": [{"claim": 2, "entity": 3}], "success": True}]))
    passed = CliRunner().invoke(app, ["store", "check", str(manifest), str(answer)])
    assert passed.exit_code == 0, passed.output
    answer.write_text(json.dumps({"claim": 2, "entity": 1}))
    refused = CliRunner().invoke(app, ["store", "check", str(manifest), str(answer)])
    assert refused.exit_code == 1 and "entity" in refused.output


def test_store_dump_refuses_a_missing_file(tmp_path: Path):
    result = CliRunner().invoke(app, ["store", "dump", str(tmp_path / "none"), str(tmp_path)])
    assert result.exit_code == 1 and "No store file" in result.output


def test_an_icon_too_large_for_a_statement_is_left_out_and_counted(tmp_path: Path, monkeypatch):
    db = sqlite3.connect(tmp_path / "store.sqlite")
    db.executescript((STORE / "schema.sql").read_text())
    db.execute(
        "INSERT INTO run (id, writer, device, commit_sha, registered_at)"
        " VALUES ('r', 'migration', 'd', 'abc1234', '2026-11-17T00:00:00.000000+00:00')"
    )
    db.execute(
        "INSERT INTO outlet_icon VALUES ('big.example', 'https://big.example/i.png',"
        " 'image/png', ?, '2026-11-17T00:00:00.000000+00:00', 'r')",
        (b"\x00" * 3_000,),
    )
    db.commit()
    db.close()
    monkeypatch.setattr(dump_module, "STATEMENT_BYTES", 2_000)
    manifest = dump_module.dump(tmp_path / "store.sqlite", tmp_path / "out")
    assert manifest.left_out == {"outlet_icon": 1}
    assert manifest.tables["outlet_icon"] == 0


def test_a_merged_claims_address_is_public_however_many_runs_the_build_takes(
    session: Session, tmp_path: Path, monkeypatch
):
    """A merge is among the first records after the claims; the store must learn the
    merged claim was public before that run, or the export has no address to move."""
    _world(session)
    session.flush()
    monkeypatch.setattr(build_module, "RUN_RECORDS", 5)
    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"

    report = build(
        session, file, payloads=payloads, store_sql=STORE, now=datetime(2026, 11, 17, tzinfo=UTC)
    )

    assert report.runs > 3
    records = StoreRecords(file, payloads=payloads)
    moved = [(former, kept.slug) for former, kept in records.moved()]
    records.close()
    assert ("drug-x-tablets-for-melanoma", moved_addresses(session)[0][1].slug) in moved
    assert sorted(former for former, _ in moved) == sorted(
        former for former, _ in moved_addresses(session)
    )
