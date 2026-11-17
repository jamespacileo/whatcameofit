"""The day's changes handed to the ingest service: every record whose body differs from
what was last handed over, in runs the service merges one at a time.

The whole store is filled in bulk (`build`, `dump`); this is for the small increments
after. What was handed over is kept on the device as one state file: each record's kind
and key with the checksum of its body. `thenwhat store build` writes the first one, so a
push after a load hands over only what changed since the build.

What a push leaves out, and why:
- a decision, a spend and a day's or claim's measurement already handed over: the store
  keeps each run's decisions and spend, and adds measurements to the day's totals, so
  each is handed over once, when it is new;
- actions, unless asked for: only the operator's token may stage one.

The wire contract is `store/ingest/README.md`, "How a writer hands over a run".
"""

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from thenwhat.store.form import Record, canonical_json, payload_of

# The service's bounds (store/ingest/src/limits.mjs): 5,000 records or 1.9 MB a chunk,
# 20,000 records a run. Kept a little under.
CHUNK_RECORDS = 4_000
CHUNK_BYTES = 1_800_000
RUN_RECORDS = 20_000
# Handed over once, when new: a run keeps its own, or a merge adds to a total.
ONCE = frozenset({"decision", "usage", "measure_daily", "measure_claim"})
USER_AGENT = "thenwhat-pipeline"


class PushFailed(Exception):
    """The service refused or could not merge a run."""


def body_sha256(record: Record) -> str:
    return hashlib.sha256(canonical_json(record.body).encode()).hexdigest()


def state_of(records: list[Record]) -> dict[str, str]:
    """What a set of records is, as a state file keeps it."""
    return {f"{record.kind}\t{record.key}": body_sha256(record) for record in records}


def read_state(path: Path) -> dict[str, str]:
    return json.loads(path.read_text())


def write_state(path: Path, state: dict[str, str]) -> None:
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")))
    temporary.replace(path)


@dataclass
class Increment:
    records: list[Record]
    left_out: Counter[str] = field(default_factory=Counter)


def increment(records: list[Record], state: dict[str, str], *, actions: bool) -> Increment:
    """The records that are new or changed since `state`, in the order given."""
    chosen: list[Record] = []
    left_out: Counter[str] = Counter()
    for record in records:
        held = state.get(f"{record.kind}\t{record.key}")
        if held == body_sha256(record):
            continue
        if held is not None and record.kind in ONCE:
            left_out[f"{record.kind} changed after it was handed over"] += 1
            continue
        if record.kind == "action" and not actions:
            left_out["action (needs the operator's token and --actions)"] += 1
            continue
        chosen.append(record)
    return Increment(chosen, left_out)


@dataclass(frozen=True)
class Chunk:
    data: bytes
    sha256: str


def chunks_of(records: list[Record]) -> list[Chunk]:
    """A run's records as the chunks it is handed over in, each under the service's
    bounds."""
    found: list[Chunk] = []
    current: list[dict[str, Any]] = []
    size = 2

    def close() -> None:
        data = json.dumps(current, ensure_ascii=False, separators=(",", ":")).encode()
        found.append(Chunk(data, hashlib.sha256(data).hexdigest()))

    for record in records:
        staged = record.staged()
        length = len(json.dumps(staged, ensure_ascii=False, separators=(",", ":")).encode()) + 1
        if current and (len(current) >= CHUNK_RECORDS or size + length > CHUNK_BYTES):
            close()
            current, size = [], 2
        current.append(staged)
        size += length
    if current:
        close()
    return found


def run_checksum(chunks: list[Chunk]) -> str:
    return hashlib.sha256("\n".join(sorted(c.sha256 for c in chunks)).encode()).hexdigest()


def runs_of(records: list[Record]) -> Iterator[list[Record]]:
    for start in range(0, len(records), RUN_RECORDS):
        yield records[start : start + RUN_RECORDS]


@dataclass
class PushReport:
    runs: int = 0
    handed: Counter[str] = field(default_factory=Counter)
    added: Counter[str] = field(default_factory=Counter)
    payloads_put: int = 0
    left_out: Counter[str] = field(default_factory=Counter)


class RunRefused(PushFailed):
    """The service refused a run: an older step version, or a record it will not take."""


def pending_path(state_file: Path) -> Path:
    """Where a push keeps the run it has sent and not yet seen merged."""
    return state_file.with_name(state_file.name + ".pending.json")


def write_pending(path: Path, run: str, records: list[Record]) -> None:
    """The run about to be sent, written whole before anything is sent."""
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(
        json.dumps({"run": run, "records": [r.staged() for r in records]}, ensure_ascii=False)
    )
    temporary.replace(path)


def read_pending(path: Path) -> tuple[str, list[Record]] | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text())
    return value["run"], [Record(**record) for record in value["records"]]


def clear_pending(path: Path) -> None:
    path.unlink(missing_ok=True)


def push(
    client: httpx.Client,
    records: list[Record],
    state: dict[str, str],
    *,
    writer: str,
    commit: str,
    payload_text: Callable[[str], str | None],
    actions: bool = False,
    report_only: bool = False,
    on_merged: Callable[[dict[str, str]], None] = lambda _: None,
    pending: Path | None = None,
) -> PushReport:
    """Hand over what changed since `state`, one run at a time. After each merged run,
    `state` holds its records and `on_merged` is given it, so a push stopped part way
    hands over only the rest next time. `payload_text` gives a large payload's text by
    checksum.

    With `pending`, each run is written there, id and records, before it is sent, and
    cleared once its merge is seen and the state written. A push that finds a run pending
    settles it first, by its id and with the same records: merged at the service, its
    records are taken as handed over; still open, it is sent again, as the same run;
    refused, the push stops. Only then is what is left worked out, so records a lost
    answer left unconfirmed are never sent again under another run."""
    report = PushReport()
    if pending is not None and not report_only:
        held = read_pending(pending)
        if held is not None:
            run, records_of_run = held
            _send(client, run, records_of_run, writer, commit, payload_text, report, False)
            state.update(state_of(records_of_run))
            on_merged(state)
            clear_pending(pending)
    chosen = increment(records, state, actions=actions)
    report.left_out = chosen.left_out
    for records_of_run in runs_of(chosen.records):
        chunks = chunks_of(records_of_run)
        # Named by what it holds: a run sent again after a lost answer is the same run,
        # which the service registers and merges once.
        run = f"{writer}-{run_checksum(chunks)[:40]}"
        if pending is not None and not report_only:
            write_pending(pending, run, records_of_run)
        _send(client, run, records_of_run, writer, commit, payload_text, report, report_only)
        if report_only:
            continue
        state.update(state_of(records_of_run))
        on_merged(state)
        if pending is not None:
            clear_pending(pending)
    return report


def _send(
    client: httpx.Client,
    run: str,
    records_of_run: list[Record],
    writer: str,
    commit: str,
    payload_text: Callable[[str], str | None],
    report: PushReport,
    report_only: bool,
) -> None:
    """Put a run's large payloads, register it, stage it and merge it, or find it merged
    already; raise unless it ends merged (or reported, with `report_only`)."""
    for record in records_of_run:
        if record.kind == "payload" and "r2_key" in record.body:
            text = payload_text(record.key)
            if text is None:
                raise PushFailed(f"The payload {record.key} is not at hand to put.")
            assert payload_of(json.loads(text)).sha256 == record.key
            answer = client.put(
                f"/payloads/{record.key}",
                content=text.encode(),
                headers={"Content-Type": "application/octet-stream"},
            )
            _ok(answer, f"payload {record.key}")
            report.payloads_put += 1
    chunks = chunks_of(records_of_run)
    counts = Counter(record.kind for record in records_of_run)
    registered = client.post(
        "/runs",
        json={
            "id": run,
            "writer": writer,
            "commit": commit,
            "steps": {},
            "counts": dict(counts),
            "checksum": run_checksum(chunks),
        },
    )
    _ok(registered, f"run {run}")
    status = _json(registered).get("status")
    if status == "merged" and not report_only:
        # Merged before, and the answer was lost: take its report, send nothing again.
        _count(report, _json(client.get(f"/runs/{run}")), counts)
        return
    if status == "refused":
        raise RunRefused(
            f"Run {run} was refused by the service: {json.dumps(_json(registered))[:300]}."
            " Nothing more is pushed until it is settled: read why with GET /runs/<id>,"
            " fix what it names (an older step version: update this checkout), then delete"
            f" {PENDING_HINT} and push again."
        )
    if status not in (None, "registered"):
        raise PushFailed(f"Run {run} is {status} at the service.")
    for chunk in chunks:
        _ok(
            client.post(
                f"/runs/{run}/records",
                content=chunk.data,
                headers={"Content-Type": "application/json", "X-Content-SHA256": chunk.sha256},
            ),
            f"a chunk of run {run}",
        )
    answer = client.post(f"/runs/{run}/{'preview' if report_only else 'merge'}")
    result = _json(answer)
    if report_only:
        _ok(answer, f"the report of run {run}")
        _count(report, result, counts)
        return
    if result.get("status") == "refused":
        raise RunRefused(
            f"Run {run} was refused by the service: {json.dumps(result)[:300]}. Fix what"
            f" it names (an older step version: update this checkout), delete {PENDING_HINT}"
            " and push again."
        )
    if result.get("status") != "merged":
        if result.get("status") in ("undone", "not_merged"):
            client.delete(f"/runs/{run}")
        raise PushFailed(f"Run {run} was not merged: {json.dumps(result)[:500]}")
    _count(report, result, counts)


PENDING_HINT = "the state file's .pending.json"


def _count(report: PushReport, result: dict[str, Any], counts: Counter[str]) -> None:
    for kind, numbers in (result.get("report") or {}).items():
        if isinstance(numbers, dict):
            report.added[kind] += int(numbers.get("added", 0))
    report.handed.update(counts)
    report.runs += 1


def _json(answer: httpx.Response) -> dict[str, Any]:
    try:
        value = answer.json()
    except ValueError:
        return {"status": answer.status_code}
    return value if isinstance(value, dict) else {"answer": value}


def _ok(answer: httpx.Response, what: str) -> None:
    if answer.status_code >= 300:
        raise PushFailed(f"The service refused {what}: {answer.status_code} {answer.text[:300]}")
