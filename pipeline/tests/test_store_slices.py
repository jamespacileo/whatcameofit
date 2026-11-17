"""The trial target set in slices: the plan, its stages, coverage, and a slice pushed after
the base load sending nothing the load held."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_store_records import STORE, _world
from thenwhat.db.models import RegistryTrial, TrialPaper, WorkEntry
from thenwhat.store.build import build
from thenwhat.store.push import increment
from thenwhat.store.slices import (
    GROUPS,
    Plan,
    SliceRefused,
    coverage,
    group_of,
    plan,
    pubmed_stage,
    record_stage,
    slice_records,
)

NOW = datetime(2026, 11, 18, tzinfo=UTC)
TODAY = NOW.date()
RULE = RegistryTrial.external_id.in_(["NCT01234567", "NCT07654321"])


def test_a_trial_s_group_is_read_from_its_record():
    year, today = 2026, TODAY
    assert group_of("COMPLETED", "2026-03", True, None, year=year, today=today) == GROUPS[0]
    assert group_of("TERMINATED", "2026-01-02", False, None, year=year, today=today) == GROUPS[1]
    assert group_of("RECRUITING", "2027-01", True, None, year=year, today=today) == GROUPS[2]
    assert (
        group_of("RECRUITING", None, False, date(2026, 5, 1), year=year, today=today) == GROUPS[3]
    )
    assert (
        group_of("RECRUITING", None, False, date(2024, 5, 1), year=year, today=today) == GROUPS[4]
    )


def test_a_plan_keeps_its_slices_and_puts_new_trials_after_them(session: Session, tmp_path: Path):
    _world(session)
    first = plan(session, RULE, name="test-set", year=2025, today=TODAY, size=1)
    assert [one.trials for one in first.slices] == [
        ["clinicaltrials.gov|NCT01234567"],
        ["clinicaltrials.gov|NCT07654321"],
    ]
    assert first.slices[0].group == GROUPS[0]  # terminated in 2025, results posted
    path = tmp_path / "plan.json"
    first.write(path)
    session.add(
        RegistryTrial(
            registry_name="clinicaltrials.gov",
            external_id="NCT00000002",
            title="New",
            conditions=[],
            interventions=[],
            phases=[],
            overall_status="RECRUITING",
            raw_payload={"protocolSection": {}},
            fetched_at=NOW,
        )
    )
    session.flush()
    wider = RegistryTrial.external_id.in_(["NCT01234567", "NCT07654321", "NCT00000002"])
    again = plan(
        session, wider, name="test-set", year=2025, today=TODAY, before=Plan.read(path), size=1
    )
    assert [one.number for one in again.slices] == [1, 2, 3]
    assert again.slices[2].trials == ["clinicaltrials.gov|NCT00000002"]


def test_the_record_and_pubmed_stages_say_what_is_held(session: Session):
    _world(session)
    made = plan(session, RULE, name="test-set", year=2025, today=TODAY)
    ended, active = made.slices  # one trial each: ended with results, and under way
    for one in made.slices:
        record_stage(session, one, NOW)
    assert ended.counts == {"trials": 1, "with_results": 1} and "record" in ended.done
    trial = session.scalars(
        select(RegistryTrial).where(RegistryTrial.external_id == "NCT01234567")
    ).one()
    session.add(
        WorkEntry(
            record_kind="registry_trial",
            record_id=trial.id,
            step="pubmed_papers",
            step_version=1,
            outcome="done",
            attempts=1,
            requests_used=1,
            fingerprint="p",
            last_attempt_at=NOW,
        )
    )
    session.add(
        TrialPaper(
            registry_trial_id=trial.id,
            source_name="pubmed",
            pubmed_id="1",
            raw_payload={"pmid": "1"},
            fetched_at=NOW,
        )
    )
    session.flush()
    # PubMed was asked about the first slice's trial, not the second's: that one waits.
    assert pubmed_stage(session, ended, NOW) and "pubmed_papers" in ended.done
    assert ended.due() == "registry_papers"  # the first stage not done, in order
    assert ended.counts["pubmed_asked"] == 1 and ended.counts["pubmed_found"] == 1
    assert not pubmed_stage(session, active, NOW) and "pubmed_papers" not in active.done
    counted = coverage(made).total
    assert counted["trials"] == 2 and counted["trials pubmed_papers"] == 1
    assert counted["trials in_store"] == 0


def test_a_slice_with_a_trial_not_stored_is_refused(session: Session):
    _world(session)
    made = plan(session, RULE, name="test-set", year=2025, today=TODAY)
    made.slices[0].trials.append("clinicaltrials.gov|NCT99999999")
    with pytest.raises(SliceRefused, match="not stored"):
        record_stage(session, made.slices[0], NOW)


def test_a_slice_after_the_base_load_sends_its_trials_and_nothing_the_load_held(
    session: Session, tmp_path: Path
):
    """The base load is the hot file: the push state a build seeds holds the hot tier's
    records only, so a slice sends its trials, their payloads, papers and state, and no
    record the load already put in D1 (a paper's record is hot)."""
    _world(session)
    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    report = build(session, file, payloads=payloads, store_sql=STORE, now=NOW)
    assert "registry_trial\tclinicaltrials.gov|NCT01234567" not in report.hot_state
    assert "registry_trial\tclinicaltrials.gov|NCT01234567" in report.state
    trial = session.scalars(
        select(RegistryTrial).where(RegistryTrial.external_id == "NCT01234567")
    ).one()
    session.add(
        TrialPaper(
            registry_trial_id=trial.id,
            source_name="pubmed",
            pubmed_id="77",
            raw_payload={"pmid": "77", "authorString": "A B.", "abstract": "Text."},
            fetched_at=NOW,
        )
    )
    session.flush()
    one_trial = RegistryTrial.external_id == "NCT01234567"
    made = plan(session, one_trial, name="test-set", year=2025, today=TODAY)
    (one,) = made.slices
    record_stage(session, one, NOW)
    records, _ = slice_records(session, one, rule="test-set", year=2025)
    sent = increment(records, report.hot_state, actions=False).records
    assert {record.kind for record in sent} == {
        "registry_trial",
        "payload",
        "trial_paper",
        "trial_slice",
    }
    # The paper keeps its byline and loses its abstract (docs/adr/0011).
    (paper,) = [record for record in sent if record.kind == "trial_paper"]
    (body,) = [
        r.body for r in sent if r.kind == "payload" and r.key == paper.body["payload_sha256"]
    ]
    assert "abstract" not in body["body"] and "authorString" in body["body"]
    # A store loaded afresh: the slice is taken as not in it, and pushed again.
    one.done["in_store"], one.store = "2026-11-18T00:00:00.000000+00:00", "old-build"
    one.forget_store()
    assert "in_store" not in one.done and one.store == ""


def test_slices_commands_refuse_a_stage_they_do_not_work():
    from typer.testing import CliRunner

    from thenwhat.cli import app

    run = CliRunner().invoke(app, ["backfill", "slices", "run", "--stage", "page"])
    assert run.exit_code == 1 and "--stage is one of" in run.output
    mark = CliRunner().invoke(app, ["backfill", "slices", "mark", "--stage", "record", "1"])
    assert mark.exit_code == 1 and "Only the page stage" in mark.output


def test_a_build_gathers_a_trial_s_papers_without_their_abstracts(session: Session):
    from thenwhat.store.gather import gather

    _world(session)
    trial = session.scalars(
        select(RegistryTrial).where(RegistryTrial.external_id == "NCT01234567")
    ).one()
    session.add(
        TrialPaper(
            registry_trial_id=trial.id,
            source_name="pubmed",
            pubmed_id="88",
            raw_payload={"pmid": "88", "authorString": "A B.", "abstract": "Text."},
            fetched_at=NOW,
        )
    )
    session.flush()
    records = gather(session).records
    (paper,) = [r for r in records if r.kind == "trial_paper"]
    assert paper.key == "clinicaltrials.gov|NCT01234567|pubmed|88"
    (payload,) = [
        r for r in records if r.kind == "payload" and r.key == paper.body["payload_sha256"]
    ]
    assert "abstract" not in payload.body["body"] and "authorString" in payload.body["body"]


class _Store:
    """Answers as the ingest service does; resolves `short` fewer trials than it is sent."""

    def __init__(self, short: int = 0) -> None:
        self.short = short
        self.staged: dict[str, list[dict]] = {}
        self.progress: dict = {}

    def __call__(self, request):
        import json as _json

        import httpx

        path = request.url.path
        if path == "/progress":
            return httpx.Response(200, json=self.progress)
        if path == "/runs":
            run = _json.loads(request.content)["id"]
            self.staged.setdefault(run, [])
            return httpx.Response(200, json={"id": run, "status": "registered"})
        run = path.split("/")[2] if path.startswith("/runs/") else ""
        if path.endswith("/records"):
            self.staged[run] += _json.loads(request.content)
            return httpx.Response(200, json={})
        if path.endswith("/merge"):
            kinds: dict[str, int] = {}
            for record in self.staged[run]:
                kinds[record["kind"]] = kinds.get(record["kind"], 0) + 1
            if "registry_trial" in kinds:
                kinds["registry_trial"] -= self.short
            report = {kind: {"resolved": n, "added": n} for kind, n in kinds.items()}
            return httpx.Response(200, json={"status": "merged", "report": report})
        return httpx.Response(200, json={})

    def kinds_sent(self) -> list[str]:
        return [record["kind"] for run in self.staged.values() for record in run]


def _pushed_slice(session, tmp_path, monkeypatch, store: "_Store"):
    import httpx

    from thenwhat.cli import slices as cli_slices
    from thenwhat.cli.store import base_state_path, state_path
    from thenwhat.store.push import write_state

    real = httpx.Client

    def client(**given):
        given["transport"] = httpx.MockTransport(store)
        return real(**given)

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setattr(cli_slices, "_commit", lambda: "abc1234")
    _world(session)
    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    report = build(session, file, payloads=payloads, store_sql=STORE, now=NOW)
    state = state_path(file)
    write_state(state, {**report.hot_state, "\tbuild": report.build_id})
    write_state(base_state_path(file), {**report.hot_state, "\tbuild": report.build_id})
    made = plan(
        session, RegistryTrial.external_id == "NCT01234567", name="test-set", year=2025, today=TODAY
    )
    (one,) = made.slices
    record_stage(session, one, NOW)
    return cli_slices, made, one, state, file


def test_a_slice_is_in_the_store_only_when_the_store_took_every_trial(
    session: Session, tmp_path: Path, monkeypatch
):
    short = _Store(short=1)
    cli_slices, made, one, state, _ = _pushed_slice(session, tmp_path, monkeypatch, short)
    cli_slices._push_slice(session, one, made, state, "http://prod.test", "t")
    assert "in_store" not in one.done and one.counts["in_store"] == 0
    short.short = 0  # the store takes them all now
    cli_slices._push_slice(session, one, made, state, "http://prod.test", "t")
    assert "in_store" in one.done and one.counts["in_store"] == 1


def test_a_slice_sends_its_trials_every_time_and_everything_again_with_again(
    session: Session, tmp_path: Path, monkeypatch
):
    store = _Store()
    cli_slices, made, one, state, _ = _pushed_slice(session, tmp_path, monkeypatch, store)
    cli_slices._push_slice(session, one, made, state, "http://prod.test", "t")
    assert "in_store" in one.done and one.store.endswith("@prod.test")
    assert {"registry_trial", "payload", "trial_slice"} <= set(store.kinds_sent())
    store.staged.clear()
    # Again, as a slice is after its PubMed stage: its trials go again, so the merge says
    # the store holds them; its payloads, held already, do not.
    cli_slices._push_slice(session, one, made, state, "http://prod.test", "t")
    assert "registry_trial" in store.kinds_sent() and "payload" not in store.kinds_sent()
    store.staged.clear()
    cli_slices._push_slice(session, one, made, state, "http://prod.test", "t", again=True)
    assert {"registry_trial", "payload"} <= set(store.kinds_sent())


def test_a_state_pushed_to_one_store_is_refused_for_another(
    session: Session, tmp_path: Path, monkeypatch
):
    from typer.testing import CliRunner

    from thenwhat.cli import app
    from thenwhat.store.push import StateForOtherStore, read_state

    store = _Store()
    cli_slices, made, one, state, file = _pushed_slice(session, tmp_path, monkeypatch, store)
    cli_slices._push_slice(session, one, made, state, "http://preview.test", "t")
    with pytest.raises(StateForOtherStore, match="fresh-state"):
        cli_slices._push_slice(session, one, made, state, "http://prod.test", "t")
    fresh = tmp_path / "prod.pushed.json"
    made_state = CliRunner().invoke(
        app, ["store", "fresh-state", str(file), "--url", "http://prod.test", "--out", str(fresh)]
    )
    assert made_state.exit_code == 0, made_state.output
    assert read_state(fresh)["\ttarget"] == "prod.test"
    assert "registry_trial\tclinicaltrials.gov|NCT01234567" not in read_state(fresh)
    refused = CliRunner().invoke(
        app, ["store", "fresh-state", str(file), "--url", "http://prod.test", "--out", str(fresh)]
    )
    assert refused.exit_code == 1 and "exists" in refused.output


def test_a_store_loaded_again_or_from_another_build_is_refused_before_a_push(
    session: Session, tmp_path: Path, monkeypatch
):
    from thenwhat.store.push import PushFailed, StoreOfOtherBuild, read_state

    store = _Store()
    cli_slices, made, one, state, file = _pushed_slice(session, tmp_path, monkeypatch, store)
    url = "http://prod.test"
    where = cli_slices.store_of(state, url)
    # A store that gives no build id or slices: nothing to compare, the push goes on.
    cli_slices._check_store(made, state, where, url, "t", again=False)
    cli_slices._push_slice(session, one, made, state, url, "t")
    # The store is loaded again: it holds no slice of the set, the plan says one was sent.
    store.progress = {"sets": [], "build_id": read_state(state)["\tbuild"]}
    with pytest.raises(PushFailed, match="fresh-state .* --again"):
        cli_slices._check_store(made, state, where, url, "t", again=False)
    cli_slices._check_store(made, state, where, url, "t", again=True)
    store.progress = {"sets": [{"rule": made.rule, "year": made.year, "total_slices": 1}]}
    cli_slices._check_store(made, state, where, url, "t", again=False)
    # Loaded from another build.
    store.progress["build_id"] = "another"
    with pytest.raises(StoreOfOtherBuild, match="another"):
        cli_slices._check_store(made, state, where, url, "t", again=True)
    # So is a new state from this build for it.
    from typer.testing import CliRunner

    from thenwhat.cli import app

    monkeypatch.setenv("INGEST_TOKEN", "t")
    args = ["store", "fresh-state", str(file), "--url", url, "--out", str(tmp_path / "n.json")]
    refused = CliRunner().invoke(app, args)
    assert refused.exit_code == 1 and "another" in refused.output
    store.progress["build_id"] = read_state(state)["\tbuild"]
    assert CliRunner().invoke(app, args).exit_code == 0


def test_a_store_whose_database_was_created_again_is_refused(
    session: Session, tmp_path: Path, monkeypatch
):
    from thenwhat.store.push import PushFailed, read_state

    store = _Store()
    cli_slices, made, _, state, _ = _pushed_slice(session, tmp_path, monkeypatch, store)
    url = "http://prod.test"
    where = cli_slices.store_of(state, url)
    store.progress = {"database_since": "2026-11-17 13:05:22"}
    cli_slices._check_store(made, state, where, url, "t", again=False)
    assert read_state(state)["\tdatabase since"] == "2026-11-17 13:05:22"
    cli_slices._check_store(made, state, where, url, "t", again=False)
    store.progress = {"database_since": "2026-11-18 09:00:00"}
    with pytest.raises(PushFailed, match="created again.*fresh-state"):
        cli_slices._check_store(made, state, where, url, "t", again=True)


def test_the_plan_and_a_slice_merge_into_the_real_store_as_run_push_forms_them(
    session: Session, tmp_path: Path
):
    """What `run --push` sends, merged through store/schema.sql and store/merge.sql into
    the hot file the store is loaded from: every planned slice's state before any stage,
    then one slice end to end, with its in_store state after."""
    import sqlite3

    from thenwhat.store.build import merge_into
    from thenwhat.store.slices import registry_papers_stage, state_record
    from thenwhat.store.tiers import HOT, split_build

    _world(session)
    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    build(session, file, payloads=payloads, store_sql=STORE, now=NOW, hot_only=True)
    (hot,) = split_build(file, payloads, HOT, hot_only=True)
    made = plan(session, RULE, name="test-set", year=2025, today=TODAY)
    planned = [state_record(one, rule=made.rule, year=made.year) for one in made.slices]
    merge_into(hot, [("plan", planned)], store_sql=STORE, now=NOW)

    one = made.slices[0]
    record_stage(session, one, NOW)
    registry_papers_stage(session, one, NOW, lambda number: None)
    records, _ = slice_records(session, one, rule=made.rule, year=made.year)
    merge_into(hot, [("slice", records)], store_sql=STORE, now=NOW)
    one.counts["in_store"] = len(one.trials)
    one.done["in_store"] = NOW.isoformat(timespec="microseconds")
    merge_into(
        hot,
        [("state", [state_record(one, rule=made.rule, year=made.year)])],
        store_sql=STORE,
        now=NOW,
    )

    db = sqlite3.connect(hot)
    # Every column the store requires and fills no other way is in a planned slice's record.
    required = {
        name
        for _, name, _, notnull, default, _ in db.execute("PRAGMA table_info(trial_slice)")
        if notnull and default is None
    }
    assert required - {"changed_run"} <= set(planned[0].body)
    rows = db.execute(
        "SELECT number, trials, with_results, in_store, record_at IS NOT NULL,"
        " in_store_at IS NOT NULL FROM trial_slice ORDER BY number"
    ).fetchall()
    held = db.execute("SELECT count(*) FROM registry_trial").fetchone()[0]
    db.close()
    assert len(rows) == len(made.slices)
    first = rows[0]
    assert first[1] == len(one.trials) and first[3] == len(one.trials) and first[4] and first[5]
    assert all(row[2] >= 0 and row[3] == 0 and not row[4] for row in rows[1:])
    assert held >= len(one.trials)


def test_a_slice_the_store_no_longer_shows_in_it_goes_again_whole(
    session: Session, tmp_path: Path, monkeypatch
):
    from thenwhat.store.push import slices_in_store

    store = _Store()
    cli_slices, made, one, state, _ = _pushed_slice(session, tmp_path, monkeypatch, store)
    url = "http://prod.test"
    cli_slices._push_slice(session, one, made, state, url, "t")
    where = cli_slices.store_of(state, url)
    assert one.store == where
    # The store shows it in: nothing is forgotten.
    shown_in = {
        "sets": [
            {
                "rule": made.rule,
                "year": made.year,
                "slices": [{"number": one.number, "in_store_at": "2026-11-18T00:00:00"}],
            }
        ]
    }
    assert slices_in_store(shown_in, made.rule, made.year) == {one.number}
    assert cli_slices.forget_lost(made, where, {one.number}, again=False) == set()
    assert "in_store" in one.done
    # A restore took it back: it is due again and its next push sends everything.
    shown_out = {
        "sets": [
            {
                "rule": made.rule,
                "year": made.year,
                "slices": [{"number": one.number, "in_store_at": None}],
            }
        ]
    }
    shown = slices_in_store(shown_out, made.rule, made.year)
    assert cli_slices.forget_lost(made, where, shown, again=False) == {one.number}
    assert "in_store" not in one.done and one.whole
    store.staged.clear()
    cli_slices._push_slice(session, one, made, state, url, "t")
    assert {"registry_trial", "payload"} <= set(store.kinds_sent()) and not one.whole
