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
    assert service.calls[0] == ("PUT", f"/payloads/{big.sha256}")
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
