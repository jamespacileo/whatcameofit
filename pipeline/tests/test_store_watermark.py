"""A build's watermarks: a hot build reads no bulk table, a rebuild keeps a bulk file whose
sources have not changed, and the same data gives the same build id."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from test_store_records import STORE, _world
from thenwhat.db.models import Claim, LinkShare
from thenwhat.store.build import build
from thenwhat.store.gather import Gathered, stream
from thenwhat.store.tiers import BULK_KINDS, HOT, split_build, tier_path
from thenwhat.store.watermark import (
    BULK_SOURCES,
    HOT_SOURCES,
    build_id,
    bulk_unchanged,
    sql_digest,
    watermarks,
)


def test_a_hot_build_gives_no_bulk_record(session: Session):
    _world(session)
    kinds = {record.kind for record in stream(session, Gathered(records=[]), hot_only=True)}
    assert kinds and not kinds & BULK_KINDS
    assert {"claim", "evidence_event", "decision", "payload"} <= kinds


def test_watermarks_move_with_any_write_and_the_id_with_the_data(session: Session):
    _world(session)
    digest = sql_digest(STORE)
    tables = HOT_SOURCES + BULK_SOURCES
    first = watermarks(session, tables)
    assert watermarks(session, tables) == first
    assert build_id(first, digest, "both") == build_id(watermarks(session, tables), digest, "both")
    assert build_id(first, digest, "both") != build_id(first, digest, "hot")

    # A new share: the bulk tier's sources have moved. (An update moves `xmin` too, but
    # only from another transaction than the one that wrote the row, and a test runs in one.)
    share = session.scalars(select(LinkShare)).first()
    assert share is not None
    session.add(
        LinkShare(
            link_lead_id=share.link_lead_id,
            platform="reddit",
            community="other",
            shared_at=share.shared_at,
            score=1,
        )
    )
    session.flush()
    after_share = watermarks(session, tables)
    assert after_share["link_share"] != first["link_share"]
    assert not bulk_unchanged({"sql": digest, "marks": first}, after_share, digest)

    # A claim's headline changes: its id does not, so the bulk file still stands.
    claim = session.scalars(select(Claim)).first()
    assert claim is not None
    claim.headline = "Another headline"
    session.flush()
    after_claim = watermarks(session, tables)
    assert bulk_unchanged({"sql": digest, "marks": after_share}, after_claim, digest)
    # Other SQL is another build.
    assert not bulk_unchanged({"sql": "other", "marks": after_claim}, after_claim, digest)


def test_a_hot_build_is_moved_into_place_with_its_objects(session: Session, tmp_path: Path):
    world = _world(session)
    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    build(
        session,
        file,
        payloads=payloads,
        store_sql=STORE,
        now=datetime(2026, 11, 17, tzinfo=UTC),
        hot_only=True,
        build_id="0123456789abcdef",
    )
    (written,) = split_build(file, payloads, HOT, hot_only=True)
    assert written == tier_path(file, HOT) and not file.exists()
    from thenwhat.store.form import payload_of

    big = payload_of(world["big_payload"])
    assert (payloads / HOT / big.r2_key).is_file() and not (payloads / "payload").exists()


def test_the_build_digest_moves_with_the_code_that_forms_records(tmp_path: Path, monkeypatch):
    import shutil

    from thenwhat.store import watermark

    before = sql_digest(STORE)
    copy = tmp_path / "package"
    for name in watermark.RECORD_CODE:
        (copy / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(watermark.PACKAGE / name, copy / name)
    monkeypatch.setattr(watermark, "PACKAGE", copy)
    assert sql_digest(STORE) == before
    people = copy / "sources" / "people.py"
    people.write_text(people.read_text() + "\n# a change to what is stripped\n")
    assert sql_digest(STORE) != before


def test_paper_only_change_is_in_the_normal_and_fresh_build(
    session: Session, tmp_path: Path, monkeypatch
):
    import sqlite3
    from contextlib import nullcontext

    from typer.testing import CliRunner

    from thenwhat.cli import app
    from thenwhat.db.models import RegistryTrial, TrialPaper
    from thenwhat.store.tiers import BULK

    _world(session)
    monkeypatch.setattr("thenwhat.cli.store.reading_session", lambda: nullcontext(session))
    file = tmp_path / "store.sqlite"
    args = [
        "store",
        "build",
        str(file),
        "--payloads",
        str(tmp_path / "objects"),
        "--store-sql",
        str(STORE),
    ]

    def run(*flags):
        result = CliRunner().invoke(app, [*args, *flags])
        assert result.exit_code == 0, result.output

    def papers():
        with sqlite3.connect(tier_path(file, BULK)) as db:
            return db.execute(
                "SELECT pubmed_id, payload_sha256 FROM trial_paper ORDER BY pubmed_id"
            ).fetchall()

    run()
    before = papers()
    trial = session.scalars(select(RegistryTrial).order_by(RegistryTrial.id)).first()
    assert trial is not None
    session.add(
        TrialPaper(
            registry_trial_id=trial.id,
            source_name="pubmed",
            pubmed_id="123456789",
            raw_payload={"id": "123456789"},
            fetched_at=datetime(2026, 11, 17, tzinfo=UTC),
        )
    )
    session.flush()
    run()
    rebuilt = papers()
    assert len(rebuilt) == len(before) + 1 and any(row[0] == "123456789" for row in rebuilt)
    run("--fresh")
    assert papers() == rebuilt
