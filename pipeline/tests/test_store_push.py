"""The day's changes handed to the ingest service, against a stand-in for the service."""

import hashlib
import json
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from thenwhat.cli import app
from thenwhat.store import push as push_module
from thenwhat.store.form import INLINE_PAYLOAD_LIMIT, Record, payload_of, payload_record
from thenwhat.store.push import PushFailed, increment, push, run_checksum, state_of

CLAIM = Record("claim", "drug-x", {"slug": "drug-x", "headline": "A"})
DECISION = Record("decision", "7", {"seq": 7, "step": "entity_match"})
ACTION = Record("action", "publish|drug-x", {"action": "publish", "slug": "drug-x"})
BIG = {"text": "x" * (INLINE_PAYLOAD_LIMIT + 10)}


def test_only_what_changed_is_handed_over():
    state = state_of([CLAIM, DECISION])
    changed = Record("claim", "drug-x", {"slug": "drug-x", "headline": "B"})
    redone = Record("decision", "7", {"seq": 7, "step": "entity_match", "confidence": 1})
    new = Record("claim", "drug-y", {"slug": "drug-y", "headline": "C"})
    chosen = increment([changed, redone, new, ACTION, DECISION], state, actions=False)
    assert chosen.records == [changed, new]
    assert sum(chosen.left_out.values()) == 2
    assert increment([ACTION], state, actions=True).records == [ACTION]


class Service:
    """Answers as the ingest service does, and keeps what it was sent."""

    def __init__(self, status: str = "merged") -> None:
        self.status = status
        self.calls: list[tuple[str, str]] = []
        self.chunks: list[bytes] = []
        self.registered: dict[str, Any] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        path = request.url.path
        if request.method == "PUT" and path.startswith("/payloads/"):
            assert hashlib.sha256(request.content).hexdigest() == path.rsplit("/", 1)[1]
            return httpx.Response(201, json={})
        if path == "/runs":
            self.registered, self.chunks = json.loads(request.content), []
            return httpx.Response(201, json={})
        if path.endswith("/records"):
            assert (
                hashlib.sha256(request.content).hexdigest() == request.headers["x-content-sha256"]
            )
            self.chunks.append(request.content)
            return httpx.Response(200, json={})
        if path.endswith("/merge"):
            sums = sorted(hashlib.sha256(chunk).hexdigest() for chunk in self.chunks)
            assert (
                self.registered["checksum"] == hashlib.sha256("\n".join(sums).encode()).hexdigest()
            )
            report = {"claim": {"resolved": 1, "added": 1}}
            return httpx.Response(200, json={"status": self.status, "report": report})
        return httpx.Response(200, json={})


def test_a_push_puts_large_payloads_stages_chunks_merges_and_keeps_its_state(monkeypatch):
    monkeypatch.setattr(push_module, "CHUNK_RECORDS", 2)
    big = payload_of(BIG)
    records = [payload_record(BIG), CLAIM, Record("claim", "drug-y", {"slug": "drug-y"})]
    service = Service()
    saved: list[dict[str, str]] = []
    with httpx.Client(
        base_url="http://store.test", transport=httpx.MockTransport(service)
    ) as client:
        report = push(
            client,
            records,
            {},
            writer="daily",
            commit="abc1234",
            payload_text={big.sha256: big.text}.get,
            on_merged=lambda state: saved.append(dict(state)),
        )
    # Registered first, then its large payload put, before any chunk is staged.
    assert service.calls[:2] == [("POST", "/runs"), ("PUT", f"/payloads/{big.sha256}")]
    assert len(service.chunks) == 2
    assert service.registered["counts"] == {"payload": 1, "claim": 2}
    assert report.runs == 1 and report.payloads_put == 1 and report.added["claim"] == 1
    assert saved == [state_of(records)]


def test_a_run_not_merged_stops_the_push_and_keeps_the_state():
    service = Service(status="undone")
    state: dict[str, str] = {}
    with (
        httpx.Client(
            base_url="http://store.test", transport=httpx.MockTransport(service)
        ) as client,
        pytest.raises(PushFailed, match="not merged"),
    ):
        push(client, [CLAIM], state, writer="daily", commit="abc1234", payload_text=dict().get)
    assert state == {}
    assert service.calls[-1][0] == "DELETE"


def test_run_checksum_is_of_the_chunks_sorted():
    a, b = push_module.Chunk(b"a", "b" * 64), push_module.Chunk(b"b", "a" * 64)
    assert run_checksum([a, b]) == run_checksum([b, a])


def test_backfill_push_refuses_without_a_token(monkeypatch, tmp_path):
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    result = CliRunner().invoke(
        app,
        ["backfill", "push", "--state", str(tmp_path / "s.json"), "--url", "http://store.test"],
    )
    assert result.exit_code == 1 and "INGEST_TOKEN" in result.output


class StopsAt(Service):
    """Merges the first run and refuses the ones after it."""

    def __init__(self, merged: int) -> None:
        super().__init__()
        self.merges, self.merged = 0, merged

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/merge"):
            self.merges += 1
            self.status = "merged" if self.merges <= self.merged else "undone"
        return super().__call__(request)


def test_a_push_twice_hands_over_nothing_the_second_time():
    state: dict[str, str] = {}
    for times in range(2):
        service = Service()
        with httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(service)) as c:
            report = push(c, [CLAIM], state, writer="daily", commit="abc1234", payload_text={}.get)
        assert report.runs == (1 if times == 0 else 0)
    assert service.calls == []


def test_a_push_stopped_between_two_runs_finishes_with_the_rest(monkeypatch):
    monkeypatch.setattr(push_module, "RUN_RECORDS", 1)
    other = Record("claim", "drug-y", {"slug": "drug-y"})
    state: dict[str, str] = {}
    stops = StopsAt(merged=1)
    with (
        httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(stops)) as c,
        pytest.raises(PushFailed),
    ):
        push(c, [CLAIM, other], state, writer="daily", commit="abc1234", payload_text={}.get)
    assert state == state_of([CLAIM])
    again = Service()
    with httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(again)) as c:
        report = push(
            c, [CLAIM, other], state, writer="daily", commit="abc1234", payload_text={}.get
        )
    assert report.handed == {"claim": 1} and state == state_of([CLAIM, other])


def test_report_only_applies_nothing_and_keeps_the_state():
    service, state = Service(), {}
    with httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(service)) as c:
        report = push(
            c,
            [CLAIM],
            state,
            writer="daily",
            commit="abc1234",
            payload_text={}.get,
            report_only=True,
        )
    assert report.runs == 1 and state == {}
    assert service.calls[-1] == ("POST", f"/runs/{service.registered['id']}/preview")


def test_backfill_push_refuses_without_an_ingest_address(monkeypatch, tmp_path):
    monkeypatch.delenv("INGEST_URL", raising=False)
    result = CliRunner().invoke(app, ["backfill", "push", "--state", str(tmp_path / "s.json")])
    assert result.exit_code == 1 and "ingest address" in result.output


def test_a_push_resent_after_a_lost_answer_is_the_same_run():
    class LosesTheAnswer(Service):
        def __init__(self) -> None:
            super().__init__()
            self.ids: list[str] = []
            self.lost = False

        def __call__(self, request: httpx.Request) -> httpx.Response:
            if request.url.path == "/runs":
                self.ids.append(json.loads(request.content)["id"])
            if request.url.path.endswith("/merge") and not self.lost:
                self.lost = True
                return httpx.Response(504, json={})
            return super().__call__(request)

    service, state = LosesTheAnswer(), {}
    with httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(service)) as c:
        with pytest.raises(PushFailed):
            push(c, [CLAIM], state, writer="daily", commit="abc1234", payload_text={}.get)
        assert state == {}
        push(c, [CLAIM], state, writer="daily", commit="abc1234", payload_text={}.get)
    assert len(service.ids) == 2 and service.ids[0] == service.ids[1]
    assert service.ids[0].startswith("daily-") and len(service.ids[0]) <= 64


def test_a_push_whose_merge_answer_was_lost_finishes_without_sending_again():
    class MergesThenLoses(Service):
        """Merges the first time and loses the answer; then answers as the service does
        for a merged run: registering again says merged, staging is refused."""

        def __init__(self) -> None:
            super().__init__()
            self.merged: set[str] = set()
            self.staged_after_merge = 0

        def __call__(self, request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/runs":
                run = json.loads(request.content)["id"]
                status = "merged" if run in self.merged else "registered"
                return httpx.Response(200, json={"id": run, "status": status, "again": True})
            run = path.split("/")[2] if path.startswith("/runs/") else ""
            if path.endswith("/records") and run in self.merged:
                self.staged_after_merge += 1
                return httpx.Response(409, json={"error": "run_closed"})
            if path.endswith("/merge"):
                self.merged.add(run)
                return httpx.Response(504, json={})
            if request.method == "GET" and path.startswith("/runs/"):
                report = {"claim": {"resolved": 1, "added": 1}}
                return httpx.Response(200, json={"run": run, "status": "merged", "report": report})
            return httpx.Response(200, json={})

    service, state = MergesThenLoses(), {}
    saved: list[dict[str, str]] = []
    with httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(service)) as c:
        with pytest.raises(PushFailed):
            push(c, [CLAIM], state, writer="daily", commit="abc1234", payload_text={}.get)
        report = push(
            c,
            [CLAIM],
            state,
            writer="daily",
            commit="abc1234",
            payload_text={}.get,
            on_merged=lambda now: saved.append(dict(now)),
        )
    assert service.staged_after_merge == 0
    assert report.runs == 1 and report.added["claim"] == 1
    assert state == state_of([CLAIM]) and saved == [state_of([CLAIM])]


def test_a_lost_answer_then_new_records_send_each_record_once(tmp_path):
    """Monday's merge answer is lost; Tuesday's push carries Monday's records and its own.
    Monday's run is settled by its id first, so each decision reaches the store once."""
    from thenwhat.store.push import pending_path

    class Store(Service):
        def __init__(self) -> None:
            super().__init__()
            self.runs: dict[str, list[dict]] = {}
            self.merged: list[str] = []
            self.lose_next = True

        def __call__(self, request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/runs":
                run = json.loads(request.content)["id"]
                status = "merged" if run in self.merged else "registered"
                self.runs.setdefault(run, [])
                return httpx.Response(200, json={"id": run, "status": status})
            run = path.split("/")[2] if path.startswith("/runs/") else ""
            if path.endswith("/records"):
                if run in self.merged:
                    return httpx.Response(409, json={"error": "run_closed"})
                self.runs[run] += json.loads(request.content)
                return httpx.Response(200, json={})
            if path.endswith("/merge"):
                self.merged.append(run)
                if self.lose_next:
                    self.lose_next = False
                    return httpx.Response(504, json={})
                return httpx.Response(200, json={"status": "merged", "report": {}})
            if request.method == "GET":
                return httpx.Response(200, json={"status": "merged", "report": {}})
            return httpx.Response(200, json={})

    monday = Record("decision", "1", {"seq": 1, "step": "entity_match"})
    tuesday = Record("decision", "2", {"seq": 2, "step": "entity_match"})
    store, state = Store(), {}
    pending = pending_path(tmp_path / "state.json")
    with httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(store)) as c:
        with pytest.raises(PushFailed):
            push(
                c,
                [monday],
                state,
                writer="daily",
                commit="abc1234",
                payload_text={}.get,
                pending=pending,
            )
        assert pending.is_file() and state == {}
        push(
            c,
            [monday, tuesday],
            state,
            writer="daily",
            commit="abc1234",
            payload_text={}.get,
            pending=pending,
        )
    staged = [record["key"] for run in store.merged for record in store.runs[run]]
    assert sorted(staged) == ["1", "2"] and len(store.merged) == 2
    assert state == state_of([monday, tuesday]) and not pending.exists()


def test_a_refused_run_stops_the_push_and_says_what_to_do(tmp_path):
    from thenwhat.store.push import RunRefused, pending_path

    class Refuses(Service):
        def __call__(self, request: httpx.Request) -> httpx.Response:
            if request.url.path == "/runs":
                return httpx.Response(200, json={"status": "refused", "refusal": "step_version"})
            return super().__call__(request)

    pending = pending_path(tmp_path / "state.json")
    transport = httpx.MockTransport(Refuses())
    with (
        httpx.Client(base_url="http://s.test", transport=transport) as c,
        pytest.raises(RunRefused, match="pending.json"),
    ):
        push(
            c,
            [CLAIM],
            {},
            writer="daily",
            commit="abc1234",
            payload_text={}.get,
            pending=pending,
        )
    assert pending.is_file()


def test_a_run_pending_for_another_build_is_refused_and_a_build_removes_it(tmp_path):
    from thenwhat.cli.store import remove_pending, state_path
    from thenwhat.store.push import PendingStale, pending_path, write_pending

    pending = pending_path(state_path(tmp_path / "store.sqlite"))
    write_pending(pending, "daily-old", [CLAIM], {"build": "aaaa", "target": "http://s.test"})
    service = Service()
    with (
        httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(service)) as c,
        pytest.raises(PendingStale, match="delete the file"),
    ):
        push(
            c,
            [CLAIM],
            {},
            writer="daily",
            commit="abc1234",
            payload_text={}.get,
            pending=pending,
            belongs={"build": "bbbb", "target": "http://s.test"},
        )
    assert service.calls == [], "nothing is sent for a stale run"
    # The build that made the new files removes what was pending for the old ones.
    assert remove_pending(tmp_path / "store.sqlite", bulk_too=False) == [pending]
    assert not pending.exists()


def test_a_merged_pending_run_settles_without_its_large_payloads(tmp_path):
    from thenwhat.store.form import payload_record
    from thenwhat.store.push import pending_path, write_pending

    big = payload_record({"x": "y" * (INLINE_PAYLOAD_LIMIT + 10)})
    assert "r2_key" in big.body
    pending = pending_path(tmp_path / "state.json")
    belongs = {"build": "b", "target": "http://s.test"}
    run = "daily-merged-before"
    write_pending(pending, run, [big], belongs)

    class Merged(Service):
        def __call__(self, request: httpx.Request) -> httpx.Response:
            self.calls.append((request.method, request.url.path))
            if request.url.path == "/runs":
                return httpx.Response(200, json={"status": "merged"})
            return httpx.Response(200, json={"status": "merged", "report": {}})

    service, state = Merged(), {}
    with httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(service)) as c:
        push(
            c,
            [],
            state,
            writer="daily",
            commit="abc1234",
            payload_text={}.get,
            pending=pending,
            belongs=belongs,
        )
    assert ("PUT", f"/payloads/{big.key}") not in service.calls
    # The state names the store it was pushed to, and holds the run's records.
    assert state == {**state_of([big]), "\ttarget": "s.test"} and not pending.exists()


def test_a_busy_service_is_waited_for_and_asked_again():
    from thenwhat.store.push import RetryOnBusy

    answers = [httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json={})]
    asked: list[str] = []

    def service(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.path)
        return answers.pop(0)

    waited: list[float] = []
    transport = RetryOnBusy(httpx.MockTransport(service), sleep=waited.append)
    with httpx.Client(base_url="http://s.test", transport=transport) as client:
        assert client.post("/runs/x/merge").status_code == 200
    assert asked == ["/runs/x/merge", "/runs/x/merge"] and waited == [7.0]


def test_the_inline_payload_limit_is_the_schema_s_own():
    import re
    from pathlib import Path

    from thenwhat.store.form import INLINE_PAYLOAD_LIMIT, schema_inline_limit

    schema = (Path(__file__).resolve().parents[2] / "store" / "schema.sql").read_text()
    stated = re.search(r"body IS NULL OR [^)]*\)?\)\s*<=\s*(\d+)", schema)
    assert stated is not None and int(stated.group(1)) == INLINE_PAYLOAD_LIMIT
    assert payload_of({"x": "y" * (INLINE_PAYLOAD_LIMIT - 20)}).inline
    assert not payload_of({"x": "y" * INLINE_PAYLOAD_LIMIT}).inline
    assert schema_inline_limit(Path("/no/such/schema.sql")) == 16384


def test_backfill_push_refuses_a_store_of_another_build_or_database(monkeypatch, tmp_path):
    from thenwhat.store.push import read_state, write_state

    progress = {"build_id": "another", "database_since": "2026-11-17 13:05:22"}
    asked: list[str] = []

    def service(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.path)
        return httpx.Response(200, json=progress)

    real = httpx.Client

    def client(**given):
        given["transport"] = httpx.MockTransport(service)
        return real(**given)

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setenv("INGEST_TOKEN", "t")
    state = tmp_path / "s.json"
    write_state(state, {"\tbuild": "0123456789abcdef", "\tdatabase since": "2026-11-16 08:00:00"})
    args = ["backfill", "push", "--state", str(state), "--url", "http://store.test"]
    refused = CliRunner().invoke(app, args)
    assert refused.exit_code == 1 and "build another" in refused.output
    progress["build_id"] = "0123456789abcdef"
    refused = CliRunner().invoke(app, args)
    assert refused.exit_code == 1 and "created again" in refused.output
    assert set(asked) == {"/progress"}
    assert read_state(state)["\tdatabase since"] == "2026-11-16 08:00:00"


def test_a_run_undone_for_a_constraint_is_marked_and_set_aside_only_then(monkeypatch, tmp_path):
    from thenwhat.store.push import RunUndone, pending_path, read_pending, write_state

    class Undoes(Service):
        def __init__(self) -> None:
            super().__init__(status="undone")
            self.held: str | None = None

        def __call__(self, request: httpx.Request) -> httpx.Response:
            if request.method == "GET" and request.url.path.startswith("/runs/"):
                if self.held is None:
                    return httpx.Response(404, json={"error": "no_such_run"})
                return httpx.Response(200, json={"status": self.held})
            if request.url.path.endswith("/merge"):
                super().__call__(request)
                return httpx.Response(
                    409,
                    json={
                        "status": "undone",
                        "reason": "constraint",
                        "detail": "NOT NULL constraint failed: trial_slice.with_results",
                    },
                )
            return super().__call__(request)

    state_file = tmp_path / "s.pushed.json"
    write_state(state_file, {})
    pending = pending_path(state_file)
    service = Undoes()
    with (
        httpx.Client(base_url="http://s.test", transport=httpx.MockTransport(service)) as c,
        pytest.raises(RunUndone, match=r"never merge.*drop-pending --state"),
    ):
        push(
            c,
            [CLAIM],
            {},
            writer="daily",
            commit="abc1234",
            payload_text={}.get,
            pending=pending,
        )
    assert read_pending(pending) is not None

    real = httpx.Client

    def client(**given):
        given["transport"] = httpx.MockTransport(service)
        return real(**given)

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setenv("INGEST_TOKEN", "t")
    args = ["store", "drop-pending", "--state", str(state_file), "--url", "http://s.test"]
    service.held = "merged"
    refused = CliRunner().invoke(app, args)
    assert refused.exit_code == 1 and "merged" in refused.output and pending.is_file()
    service.held = None
    dropped = CliRunner().invoke(app, args)
    assert dropped.exit_code == 0, dropped.output
    assert not pending.exists() and list(tmp_path.glob("s.pushed.json.pending.json.set-aside-*"))
    # A pending run no constraint undid is not set aside: a push settles it.
    write_state(state_file, {})
    from thenwhat.store.push import write_pending

    write_pending(pending, "daily-x", [CLAIM])
    kept = CliRunner().invoke(app, args)
    assert kept.exit_code == 1 and "push again" in kept.output and pending.is_file()
