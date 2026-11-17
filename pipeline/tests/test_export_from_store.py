"""The export taken from a SQLite file of the truth store's schema, tested by holding it
to the export the database gives for the same records (openspec truth-store, "The export
is assembled once, from either store"). No network: the store file is filled from the
test database through `store/merge.sql`, with a folder standing in for the object store.
"""

import json
import sqlite3
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from store_support import STORE_SQL, assert_same_export, both_exports, store_of
from test_export import (
    ARTICLE,
    CHECKED_IN_SCHEMA,
    EARLIER,
    NOW,
    SLUG,
    add_event,
    add_match,
    add_origin_paper,
    add_registry_events,
    new_claim,
    study,
)
from thenwhat.claims.corrections import merge_claims, rename_intervention
from thenwhat.claims.entry import add_article, archive_claim, clear_audit
from thenwhat.cli import app
from thenwhat.db.models import OutletIcon
from thenwhat.domain import (
    ClaimStatus,
    Decider,
    EventType,
    EvidenceStage,
    RegulatoryOutcome,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.export.build import build_export
from thenwhat.export.compare import canonical_bytes, compare
from thenwhat.export.parallel import compare_with_store
from thenwhat.export.rehearsal import against, problems
from thenwhat.export.store_records import TABLES_READ, StoreFault, StoreRecords
from thenwhat.review.queue import confirm_stage, flag_failure
from thenwhat.seed.load import load_seed

SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "seed" / "tooth-regrowth-usag1.json"


def claim_in(export: dict[str, Any], slug: str = SLUG) -> dict[str, Any]:
    return next(claim for claim in export["claims"] if claim["slug"] == slug)


# --- the cases the cut-over is judged on ---------------------------------------------


def test_seeded_example_is_the_same_from_the_store(session: Session, tmp_path: Path):
    """Scenario: Same records, same export"""
    load_seed(session, json.loads(SEED_FILE.read_text()), now=EARLIER)

    export = assert_same_export(session, tmp_path, NOW)

    [claim] = export["claims"]
    assert claim["slug"] == "tooth-regrowth-usag1"
    assert claim["events"] and claim["trials"] and claim["articles"]
    assert export["outlets"]


def test_archived_claim_is_listed_the_same(session: Session, tmp_path: Path):
    """Scenario: Archived, merged and held claims"""
    new_claim(session)
    new_claim(session, "never-published")
    build_export(session, now=EARLIER)  # publishes both
    archive_claim(session, SLUG, reason="wrong trial", now=NOW)
    new_claim(session, "taken-down-unpublished")
    archive_claim(session, "taken-down-unpublished", reason="never right", now=NOW)

    export = assert_same_export(session, tmp_path, NOW)

    assert export["archived"] == [{"slug": SLUG, "on": "2026-11-20"}]
    assert [claim["slug"] for claim in export["claims"]] == ["never-published"]


def test_merged_claims_address_moves_the_same(session: Session, tmp_path: Path):
    """Scenario: Archived, merged and held claims"""
    new_claim(session)
    new_claim(session, "tooth-regrowth-twin")
    build_export(session, now=EARLIER)
    merge_claims(
        session,
        "tooth-regrowth-twin",
        SLUG,
        reason="one antibody",
        by=Decider.HUMAN,
        now=NOW,
        same_treatment_accepted=True,
    )

    export = assert_same_export(session, tmp_path / "a", NOW)

    assert export["moved"] == [{"slug": "tooth-regrowth-twin", "to": SLUG}]
    assert [claim["slug"] for claim in export["claims"]] == [SLUG]

    # Once the kept claim is taken down too, both addresses answer gone, from either.
    archive_claim(session, SLUG, reason="wrong trial", now=NOW)
    export = assert_same_export(session, tmp_path / "b", NOW)
    assert export["moved"] == []
    assert [entry["slug"] for entry in export["archived"]] == [SLUG, "tooth-regrowth-twin"]


def test_merged_claim_that_was_never_public_moves_from_neither(session: Session, tmp_path: Path):
    """Scenario: Archived, merged and held claims"""
    new_claim(session)
    build_export(session, now=EARLIER)
    # Entered after the last export and merged before the next: its address was never public.
    new_claim(session, "tooth-regrowth-twin")
    merge_claims(
        session,
        "tooth-regrowth-twin",
        SLUG,
        reason="one antibody",
        by=Decider.HUMAN,
        now=NOW,
        same_treatment_accepted=True,
    )

    export = assert_same_export(session, tmp_path, NOW)

    assert export["moved"] == []
    assert [claim["slug"] for claim in export["claims"]] == [SLUG]


def test_renamed_claims_old_address_moves_the_same(session: Session, tmp_path: Path):
    """Scenario: Archived, merged and held claims"""
    new_claim(session)
    add_event(session)
    build_export(session, now=EARLIER)
    rename_intervention(
        session, SLUG, f"EX-1 antibody {SLUG}", "TRG-035", by=Decider.HUMAN, now=NOW, reslug=True
    )

    export = assert_same_export(session, tmp_path, NOW)

    assert export["moved"] == [{"slug": SLUG, "to": "trg-035-tooth-agenesis"}]
    assert claim_in(export, "trg-035-tooth-agenesis")["events"]


def test_claim_awaiting_audit_is_left_out_by_both(session: Session, tmp_path: Path):
    """Scenario: Archived, merged and held claims"""
    held = new_claim(session)
    held.awaiting_audit_at = EARLIER
    new_claim(session, "released")
    session.flush()

    export = assert_same_export(session, tmp_path / "a", NOW)

    assert [claim["slug"] for claim in export["claims"]] == ["released"]
    assert export["archived"] == []

    clear_audit(session, [SLUG])
    export = assert_same_export(session, tmp_path / "b", NOW)
    assert [claim["slug"] for claim in export["claims"]] == ["released", SLUG]


def _started(session: Session, phase: TrialPhase) -> None:
    add_event(session, trial_phases=[phase])
    add_event(
        session,
        type=EventType.TRIAL_STATUS_CHANGE,
        event_date=date(2024, 10, 1),
        summary="Trial started.",
        trial_state=TrialState.STARTED,
        trial_phases=[phase],
    )


def _no_trial(session: Session) -> None:
    pass


def _preclinical(session: Session) -> None:
    confirm_stage(session, SLUG, EvidenceStage.ANIMAL, now=EARLIER)


def _registered(session: Session) -> None:
    add_event(session)


def _approved(session: Session) -> None:
    add_event(session)
    add_event(
        session,
        type=EventType.REGULATORY_DECISION,
        event_date=date(2026, 5, 1),
        summary="Approved by the regulator.",
        source_url="https://regulator.example/decision",
        external_id="decision-1",
        trial_phases=[],
        regulatory_outcome=RegulatoryOutcome.APPROVED,
    )


def _failed(session: Session) -> None:
    add_event(session)
    posted = add_event(
        session,
        type=EventType.TRIAL_RESULTS_POSTED,
        event_date=date(2026, 2, 1),
        summary="Results posted.",
    )
    flag_failure(
        session,
        SLUG,
        trial_id="NCT1",
        event_id=posted.id,
        source_url="https://registry.example/NCT1/results",
        now=EARLIER,
    )


def _terminated(session: Session) -> None:
    add_event(session)
    add_event(
        session,
        type=EventType.TRIAL_STATUS_CHANGE,
        event_date=date(2025, 1, 5),
        summary="Trial terminated.",
        trial_state=TrialState.TERMINATED,
    )


def _retracted(session: Session) -> None:
    add_origin_paper(session, "10.1000/origin")
    add_event(session)
    add_event(
        session,
        type=EventType.RETRACTION,
        event_date=date(2026, 6, 1),
        summary="The paper was retracted.",
        source_url="https://doi.org/10.1000/origin",
        external_id="10.1000/origin",
        trial_phases=[],
    )


@pytest.mark.parametrize(
    ("status", "evidence"),
    [
        (ClaimStatus.NO_TRIAL_FOUND, _no_trial),
        (ClaimStatus.PRECLINICAL_ONLY, _preclinical),
        (ClaimStatus.TRIAL_REGISTERED, _registered),
        (ClaimStatus.PHASE_1, lambda session: _started(session, TrialPhase.PHASE_1)),
        (ClaimStatus.PHASE_2, lambda session: _started(session, TrialPhase.PHASE_2)),
        (ClaimStatus.PHASE_3, lambda session: _started(session, TrialPhase.PHASE_3)),
        (ClaimStatus.APPROVED, _approved),
        (ClaimStatus.FAILED, _failed),
        (ClaimStatus.TERMINATED, _terminated),
        (ClaimStatus.RETRACTED, _retracted),
    ],
    ids=lambda value: value.value if isinstance(value, ClaimStatus) else "",
)
def test_status_from_each_rule_is_the_same(
    session: Session, tmp_path: Path, status: ClaimStatus, evidence: Any
):
    """Scenario: Every status"""
    new_claim(session)
    evidence(session)

    export = assert_same_export(session, tmp_path, NOW)

    held = claim_in(export)["status"]
    assert held["code"] == status.value
    assert held["history"][-1]["code"] == status.value


def test_quiet_claims_overlay_is_derived_the_same_at_the_exports_date(
    session: Session, tmp_path: Path
):
    """Scenario: Every status"""
    new_claim(session)

    export = assert_same_export(session, tmp_path, NOW)

    assert claim_in(export)["status"]["overlay_years"] == 8
    # The store's file holds no overlay for the claim: it was derived while exporting.
    with sqlite3.connect(tmp_path / "store.db") as db:
        assert db.execute("SELECT overlay_years FROM claim").fetchall() == [(None,)]


# --- what the reader does with the store's own shape ----------------------------------


def small_inline_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    """The store keeps a payload of up to 524,288 bytes in its row, larger than any
    recorded study; for a test of a payload kept as an object, a recorded study must be
    one, so the bound the store file is built with is lowered to the old 16,384."""
    from thenwhat.store import form

    monkeypatch.setattr(form, "INLINE_PAYLOAD_LIMIT", 16384)


def test_registry_record_kept_as_an_object_gives_the_same_trial_facts(
    session: Session, tmp_path: Path, fixture_json, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: A payload kept as an object"""
    small_inline_bound(monkeypatch)
    claim = new_claim(session)
    add_registry_events(session, claim, study(fixture_json, "study_NCT03491397_rows"))

    export = assert_same_export(session, tmp_path, NOW)

    [trial] = claim_in(export)["trials"]
    assert trial["facts"]["results"] is not None
    objects = list((tmp_path / "objects" / "payload").iterdir())
    assert objects, "the record is larger than the store keeps in a row"


def test_export_refuses_a_payload_that_is_not_the_one_its_checksum_names(
    session: Session, tmp_path: Path, fixture_json, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: A payload that is missing or altered"""
    small_inline_bound(monkeypatch)
    claim = new_claim(session)
    add_registry_events(session, claim, study(fixture_json, "study_NCT03491397_rows"))
    records, _ = store_of(session, tmp_path, NOW)
    [held] = list((tmp_path / "objects" / "payload").iterdir())

    held.write_bytes(held.read_bytes().replace(b"NCT03491397", b"NCT00000000"))
    with pytest.raises(StoreFault, match="does not have that checksum"):
        build_export(records, now=NOW)

    held.unlink()
    with pytest.raises(StoreFault, match="is not in"):
        build_export(records, now=NOW)
    records.close()


def test_export_from_the_store_writes_nothing_to_it(session: Session, tmp_path: Path):
    """Scenario: Reading only"""
    new_claim(session)
    add_event(session)
    records, _ = store_of(session, tmp_path, NOW)
    before = (tmp_path / "store.db").read_bytes()

    export = build_export(records, now=NOW)
    records.close()

    assert [claim.slug for claim in export.claims] == [SLUG]
    assert (tmp_path / "store.db").read_bytes() == before
    # The claim had no published time; who states the publication is told which.
    assert records.first_published == [SLUG]


def test_file_without_the_stores_schema_is_refused(tmp_path: Path):
    """Scenario: Not a store file"""
    sqlite3.connect(tmp_path / "other.db").execute("CREATE TABLE claim (id INTEGER)").close()

    with pytest.raises(StoreFault, match="does not have the store's schema"):
        StoreRecords(tmp_path / "other.db")
    with pytest.raises(StoreFault, match="No store file"):
        StoreRecords(tmp_path / "absent.db")


def test_matches_scored_and_read_are_the_same_with_their_readings(session: Session, tmp_path: Path):
    """A match's reading is the latest scoring decision about it, which the store files
    under the match's natural key."""
    claim = new_claim(session)
    add_match(session, claim, "NCT1", 0.92, ReviewState.APPROVED)
    for number in range(2, 9):
        add_match(session, claim, f"NCT{number}", 0.1 * number, ReviewState.PENDING)

    export = assert_same_export(session, tmp_path, NOW, match_accept_above=0.8)

    matches = claim_in(export)["matches"]
    assert [match["state"] for match in matches] == ["approved"] + ["candidate"] * 5


# --- the comparison itself ------------------------------------------------------------


def test_comparison_names_the_claim_and_the_place_that_differ(session: Session, tmp_path: Path):
    """Scenario: A difference is named"""
    new_claim(session)
    add_event(session)
    new_claim(session, "second-claim")
    from_database, from_store = both_exports(session, tmp_path, NOW)
    claim_in(from_store)["events"][0]["summary"] = "Something else."
    from_store["archived"].append({"slug": "gone", "on": "2026-01-01"})

    comparison = compare(from_database, from_store)

    assert not comparison.same
    assert [(d.part, d.claim) for d in comparison.differences] == [
        ("archived", False),
        (SLUG, True),
    ]
    assert any("events[0].summary" in place for place in comparison.differences[1].places)
    assert comparison.lines()[0].startswith("The two exports differ: 1 of 2 claims")


def test_comparison_looks_past_row_ids_and_order_among_equals_and_nothing_else(
    session: Session, tmp_path: Path
):
    """Scenario: What the comparison looks past"""
    new_claim(session)
    first = add_event(session)
    add_event(session, external_id="NCT2", source_url="https://registry.example/NCT2")
    add_article(
        session,
        SLUG,
        url=ARTICLE + "-again",
        outlet="Example News",
        title="More mice",
        published_date=date(2018, 3, 10),
    )
    export = json.loads(build_export(session, now=NOW).model_dump_json())

    # Other row ids, the two same-day events and articles the other way round, made later.
    other = json.loads(json.dumps(export))
    [claim] = other["claims"]
    for event in claim["events"]:
        event["id"] += 1000
    claim["status"]["explained_by"] = [number + 1000 for number in claim["status"]["explained_by"]]
    claim["events"].reverse()
    claim["articles"].reverse()
    other["generated_at"] = datetime(2027, 1, 1, tzinfo=UTC).isoformat()
    assert compare(export, other).same
    assert canonical_bytes(export) == canonical_bytes(other)

    # An event out of its date order is not looked past.
    late = json.loads(json.dumps(export))
    next(e for e in late["claims"][0]["events"] if e["id"] == first.id)["event_date"] = "2025-01-01"
    assert not compare(export, late).same


# --- the commands ---------------------------------------------------------------------


@pytest.fixture
def invoke(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        with session.no_autoflush:
            yield session

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setattr("thenwhat.cli.export.reading_session", test_session)
    runner = CliRunner()
    return lambda *arguments: runner.invoke(app, list(arguments))


def test_export_command_reads_a_store_file(session: Session, tmp_path: Path, invoke):
    """Scenario: Same records, same export"""
    new_claim(session)
    add_event(session)
    held = new_claim(session, "held-claim")
    held.awaiting_audit_at = EARLIER
    store_of(session, tmp_path, NOW)[0].close()
    target = tmp_path / "out" / "export.json"

    result = invoke("export", "--store", str(tmp_path / "store.db"), "--out", str(target))

    assert result.exit_code == 0, result.output
    assert "Exported 1 claim from" in result.output
    assert "1 approved claim was left out: awaiting audit." in result.output
    assert "no published time in the store" in result.output
    written = json.loads(target.read_text())
    jsonschema.validate(written, json.loads(CHECKED_IN_SCHEMA.read_text()))
    assert [claim["slug"] for claim in written["claims"]] == [SLUG]


def test_export_command_refuses_a_file_that_is_not_a_store(tmp_path: Path, invoke):
    """Scenario: Not a store file"""
    sqlite3.connect(tmp_path / "other.db").close()

    result = invoke("export", "--store", str(tmp_path / "other.db"), "--out", str(tmp_path / "x"))

    assert result.exit_code == 1
    assert "does not have the store's schema" in result.output
    assert not (tmp_path / "x").exists()


def test_compare_command_says_the_exports_are_the_same_and_stores_nothing(
    session: Session, tmp_path: Path, invoke
):
    """Scenarios: The nightly comparison, Comparing changes neither store"""
    claim = new_claim(session)
    add_event(session)
    session.flush()
    report = tmp_path / "report.json"

    result = invoke("export-compare", "--store-sql", str(STORE_SQL), "--report", str(report))

    assert result.exit_code == 0, result.output
    assert "The two exports are the same: 1 claims, byte for byte." in result.output
    assert json.loads(report.read_text())["same"] is True
    # The database's export gave the claim its published time in memory only.
    session.expire_all()
    assert claim.published_at is None


def test_compare_command_exits_with_1_and_names_what_differs(
    session: Session, tmp_path: Path, invoke
):
    """Scenario: A difference is named"""
    new_claim(session)
    add_event(session)
    store_of(session, tmp_path, NOW)[0].close()
    # The store falls behind: the database gains an event the store file has not.
    add_event(session, external_id="NCT2", source_url="https://registry.example/NCT2")
    session.flush()

    result = invoke("export-compare", "--store", str(tmp_path / "store.db"))

    assert result.exit_code == 1
    assert "The two exports differ: 1 of 1 claims" in result.output
    assert "claim.events: 2 entries in the first, 1 in the second" in result.output


def test_compare_of_every_nth_claim_keeps_both_ends_of_a_merge(session: Session, tmp_path: Path):
    """Scenario: The nightly comparison"""
    kept = new_claim(session)
    twin = new_claim(session, "tooth-regrowth-twin")
    for number in range(6):
        new_claim(session, f"another-{number}")
    build_export(session, now=EARLIER)
    merge_claims(
        session,
        twin.slug,
        SLUG,
        reason="one antibody",
        by=Decider.HUMAN,
        now=NOW,
        same_treatment_accepted=True,
    )
    session.flush()
    every = next(n for n in range(2, 9) if (kept.id % n == 0) != (twin.id % n == 0))

    with session.no_autoflush:
        result = compare_with_store(
            session, now=NOW, work=tmp_path, store_sql=STORE_SQL, every=every
        )

    assert result.comparison.same, "\n".join(result.comparison.lines())
    assert result.comparison.claims_first < 7
    with sqlite3.connect(tmp_path / "store.db") as db:
        slugs = {slug for (slug,) in db.execute("SELECT slug FROM claim")}
    assert {SLUG, twin.slug} <= slugs


def test_a_claim_with_two_articles_at_one_address_key_differs_with_its_cause_named(
    session: Session, tmp_path: Path, invoke, monkeypatch
):
    """Scenario: A difference the comparison can explain"""
    new_claim(session)
    add_event(session)
    add_article(
        session,
        SLUG,
        url=ARTICLE + "?utm_source=newsletter",
        outlet="Example News",
        title="Mice again",
        published_date=date(2018, 3, 10),
    )
    session.flush()

    strict = invoke("export-compare", "--store-sql", str(STORE_SQL))
    allowed = invoke("export-compare", "--store-sql", str(STORE_SQL), "--allow-named")

    assert strict.exit_code == 1, strict.output
    assert "1 have a named cause, 0 do not." in strict.output
    assert "two source articles of this claim at one" in " ".join(strict.output.split())
    assert allowed.exit_code == 0, allowed.output
    assert "The two exports differ: 1 of 1 claims" in allowed.output

    def changed_status(first, second, **kwargs):
        claim_in(first)["status"]["code"] = "phase_3"
        claim_in(second)["status"]["code"] = "approved"
        return compare(first, second, **kwargs)

    monkeypatch.setattr("thenwhat.export.parallel.compare", changed_status)
    wrong = invoke("export-compare", "--store-sql", str(STORE_SQL), "--allow-named")
    assert wrong.exit_code == 1, wrong.output
    assert "1 have a named cause, 1 do not" in wrong.output
    assert "claim.status.code" in wrong.output


def test_names_in_another_order_are_the_merges_and_anything_more_is_unexplained(
    session: Session, tmp_path: Path
):
    """Scenario: A difference the comparison can explain"""
    new_claim(session)
    add_event(session)
    export = json.loads(build_export(session, now=NOW).model_dump_json())
    reordered = json.loads(json.dumps(export))
    claim_in(reordered)["intervention"]["synonyms"] = ["b", "a"]
    claim_in(export)["intervention"]["synonyms"] = ["a", "b"]
    changed = json.loads(json.dumps(reordered))
    claim_in(changed)["headline"] = "Another headline"

    [order_only] = compare(export, reordered).differences
    comparison = compare(export, changed)

    assert order_only.cause is not None and "store/merge.sql" in order_only.cause
    assert [d.cause for d in comparison.differences] == [None]
    assert comparison.unexplained == comparison.differences


def answering_from(path: Path, asked: list[list[str]]):
    """A stand-in for `wrangler`: answers a `d1 execute` from a local store file in the
    form wrangler prints, and copies an object for an `r2 object get`."""

    def wrangler(arguments):
        asked.append(list(arguments))
        if arguments[:2] == ["d1", "execute"]:
            db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            db.row_factory = sqlite3.Row
            rows = [dict(row) for row in db.execute(arguments[arguments.index("--command") + 1])]
            db.close()
            return json.dumps([{"results": rows, "success": True, "meta": {}}])
        if arguments[:3] == ["r2", "object", "get"]:
            key = arguments[3].split("/", 1)[1]
            Path(arguments[arguments.index("--file") + 1]).write_bytes(
                (path.parent / "objects" / key).read_bytes()
            )
            return ""
        raise AssertionError(f"not expected: {arguments}")

    return wrangler


def test_compare_command_reads_the_stores_export_from_the_database_itself(
    session: Session, tmp_path: Path, invoke, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Comparing against the store itself"""
    new_claim(session)
    add_event(session)
    twin = new_claim(session, "second-claim")
    archive_claim(session, twin.slug, reason="entered twice", now=NOW)
    # One icon held and one asked for and not held: an empty BLOB must stay empty.
    session.add_all(
        [
            OutletIcon(
                domain="news.example.org",
                icon_url="https://news.example.org/favicon.ico",
                media_type="image/x-icon",
                content=b"\x00\x01icon",
                fetched_at=NOW,
            ),
            OutletIcon(domain="other.example.org", fetched_at=NOW),
        ]
    )
    held = tmp_path / "held"
    store_of(session, held, NOW)[0].close()
    asked: list[list[str]] = []
    # Pages of at most two rows, so every table with more is read in several.
    monkeypatch.setattr("thenwhat.export.store_fetch.PAGE_ROWS", 1)
    monkeypatch.setattr("thenwhat.export.store_fetch.MOST_ROWS", 2)
    monkeypatch.setattr(
        "thenwhat.cli.export.wrangler_in",
        lambda folder, config: answering_from(held / "store.db", asked),
    )

    result = invoke(
        "export-compare", "--d1", "thenwhat-store-preview", "--store-sql", str(STORE_SQL)
    )

    assert result.exit_code == 0, result.output
    assert "The two exports are the same: 1 claims, byte for byte." in result.output
    assert all("--remote" in arguments and "SELECT" in arguments[-1] for arguments in asked)
    assert not any(word in arguments[-1] for arguments in asked for word in ("INSERT", "UPDATE"))
    assert "  claim: 2 rows in " in result.output and "  outlet_icon: 2 rows in " in result.output
    assert not any(" OFFSET " in arguments[-1] for arguments in asked)
    # Only the tables an export reads are asked for: none of the bulk tier.
    read = {arguments[-1].split(" FROM ")[1].split()[0] for arguments in asked}
    assert read == set(TABLES_READ)

    asked.clear()
    local = invoke("export-compare", "--d1", "STORE", "--d1-local", "--store-sql", str(STORE_SQL))
    assert local.exit_code == 0, local.output
    assert asked and all("--local" in arguments for arguments in asked)


def test_compare_command_refuses_a_store_it_cannot_read(
    session: Session, tmp_path: Path, invoke, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Comparing against the store itself"""
    new_claim(session)
    session.flush()
    ran: list[list[str]] = []

    def failing(command, **_):
        ran.append(command)
        # As wrangler prints a failure with --json: the reason is inside, the last line is "}".
        printed = json.dumps(
            {"error": {"text": "D1_ERROR: response too large", "notes": [{"text": "code 7500"}]}},
            indent=2,
        )
        return subprocess.CompletedProcess(command, 1, stdout=printed, stderr="")

    monkeypatch.setattr("thenwhat.export.store_fetch.subprocess.run", failing)

    result = invoke("export-compare", "--d1", "thenwhat-store-preview")

    assert result.exit_code == 1
    said = " ".join(result.output.split())
    assert "Reading claim after 0 rows, one row a page" in said
    assert "D1_ERROR: response too large code 7500" in said
    # The page was halved down to one row before giving up.
    assert ran[-1][-1].endswith("LIMIT 1")


def test_export_command_reads_the_d1_store_and_fetches_the_objects_it_lacks(
    session: Session, tmp_path: Path, invoke, monkeypatch: pytest.MonkeyPatch, fixture_json
):
    """Scenario: Comparing against the store itself"""
    small_inline_bound(monkeypatch)
    claim = new_claim(session)
    add_registry_events(session, claim, study(fixture_json, "study_NCT03491397_rows"))
    held = tmp_path / "held"
    store_of(session, held, NOW)[0].close()
    asked: list[list[str]] = []
    monkeypatch.setattr(
        "thenwhat.cli.export.wrangler_in",
        lambda folder, config: answering_from(held / "store.db", asked),
    )
    target = tmp_path / "export.json"

    result = invoke(
        "export",
        "--d1",
        "thenwhat-store-preview",
        "--store",
        str(tmp_path / "fetched.db"),
        "--payloads",
        str(tmp_path / "objects"),
        "--r2-bucket",
        "thenwhat-payloads-preview",
        "--out",
        str(target),
    )

    assert result.exit_code == 0, result.output
    assert "(1 payload objects)" in result.output
    assert [claim["slug"] for claim in json.loads(target.read_text())["claims"]] == [SLUG]
    assert sum(arguments[0] == "r2" for arguments in asked) == 1


def test_rehearsal_passes_an_export_from_the_store_and_refuses_one_the_site_cannot_read(
    session: Session, tmp_path: Path
):
    """Scenario: A rehearsal"""
    new_claim(session)
    add_event(session)
    records, _ = store_of(session, tmp_path, NOW)
    export = json.loads(build_export(records, now=NOW).model_dump_json())
    records.close()
    schema = json.loads(CHECKED_IN_SCHEMA.read_text())
    broken = json.loads(json.dumps(export))
    del claim_in(broken)["status"]

    assert problems(export, schema) == []
    assert against(export, {"claims": [{"slug": "another"}]})[0].startswith(
        "1 claims from the store, 1 in the published snapshot, 0 in both."
    )
    assert any("status" in problem for problem in problems(broken, schema))
    assert problems({**export, "claims": []}, schema)[-1] == "The export holds no claim."


def test_a_store_file_of_only_the_tables_an_export_reads_gives_the_same_export(
    session: Session, tmp_path: Path, fixture_json
):
    """Scenario: A store that holds only the hot tier"""
    claim = new_claim(session)
    add_registry_events(session, claim, study(fixture_json, "study_NCT03491397_rows"))
    add_match(session, claim, "NCT09999999", 0.7, ReviewState.PENDING)
    twin = new_claim(session, "second-claim")
    archive_claim(session, twin.slug, reason="entered twice", now=NOW)
    records, _ = store_of(session, tmp_path, NOW)
    whole = json.loads(build_export(records, now=NOW).model_dump_json())
    records.close()
    with sqlite3.connect(tmp_path / "store.db") as db:
        db.execute("PRAGMA foreign_keys = OFF")
        for (view,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'view'").fetchall():
            db.execute(f"DROP VIEW {view}")
        tables = [
            name
            for (name,) in db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        dropped = [table for table in tables if table not in TABLES_READ]
        for table in dropped:
            # A search table takes its shadow tables with it.
            db.execute(f"DROP TABLE IF EXISTS {table}")
    assert {"registry_trial", "link_lead", "work_entry", "llm_usage"} <= set(dropped)

    hot = StoreRecords(tmp_path / "store.db", payloads=tmp_path / "objects")
    export = json.loads(build_export(hot, now=NOW).model_dump_json())
    hot.close()

    assert canonical_bytes(export) == canonical_bytes(whole)
    assert claim_in(export)["trials"]


def test_export_refuses_a_store_missing_a_column_it_reads_and_names_it(
    session: Session, tmp_path: Path
):
    """Scenario: Not a store file"""
    new_claim(session)
    store_of(session, tmp_path, NOW)[0].close()
    with sqlite3.connect(tmp_path / "store.db") as db:
        db.execute("ALTER TABLE promise RENAME COLUMN parsed_date TO parsed")
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("DROP TABLE outlet_icon")

    with pytest.raises(StoreFault) as refused:
        StoreRecords(tmp_path / "store.db")

    assert "it has no table outlet_icon" in str(refused.value)
    assert "it has no column promise.parsed_date" in str(refused.value)
