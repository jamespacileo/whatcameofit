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
import time
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


class RetryOnBusy(httpx.BaseTransport):
    """A transport that, answered 429, waits as long as the service's `Retry-After` says
    (60 seconds by default) and sends the same request again, up to `attempts` times.
    Every write route of the service is safe to repeat, and a 429 is answered before
    the store is touched (store/ingest/README.md)."""

    def __init__(
        self,
        inner: httpx.BaseTransport | None = None,
        *,
        attempts: int = 10,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.inner = inner or httpx.HTTPTransport()
        self.attempts, self.sleep = attempts, sleep

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        for _ in range(self.attempts - 1):
            response = self.inner.handle_request(request)
            if response.status_code != 429:
                return response
            response.read()
            try:
                wait = float(response.headers.get("Retry-After", "60"))
            except ValueError:
                wait = 60.0
            self.sleep(min(max(wait, 1.0), 300.0))
        return self.inner.handle_request(request)

    def close(self) -> None:
        self.inner.close()


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
    # By kind, the records the store's merge resolved (found their parents and took),
    # added or matched: what the store says it holds of what was sent.
    resolved: Counter[str] = field(default_factory=Counter)


class RunRefused(PushFailed):
    """The service refused a run: an older step version, or a record it will not take."""


def pending_path(state_file: Path) -> Path:
    """Where a push keeps the run it has sent and not yet seen merged."""
    return state_file.with_name(state_file.name + ".pending.json")


# Where a state says which build it holds, and which store it was pushed to: not a
# record's kind and key.
BUILD_KEY = "\tbuild"
TARGET_KEY = "\ttarget"


class StateForOtherStore(PushFailed):
    """A push state was pushed to another store than the one named."""


def target_of(url: str) -> str:
    """The store a push goes to, as a state names it: the service's host."""
    from urllib.parse import urlparse

    found = urlparse(url)
    return (found.netloc or found.path).lower().rstrip("/")


def check_target(state: dict[str, str], url: str, state_file: Path | None = None) -> None:
    """Refuse a state pushed to another store; a state that names none is taken for this
    one (it is the build's own, unpushed)."""
    held = state.get(TARGET_KEY)
    if held and held != target_of(url):
        where = f" {state_file}" if state_file else ""
        raise StateForOtherStore(
            f"The push state{where} is of {held}, not {target_of(url)}: what it says was"
            " sent is in that store, not this one. Start this store's own state from the"
            " build: thenwhat store fresh-state <store file> --url <this store's address>"
            " --out <new state file>, and push with it."
        )
    state[TARGET_KEY] = target_of(url)


class StoreOfOtherBuild(PushFailed):
    """The store was loaded from another build than the one the push state is of."""


def store_build(progress: Any) -> str | None:
    """The build a store was loaded from, as its `GET /progress` gives it (`build_id`);
    None while the service gives none."""
    value = progress.get("build_id") if isinstance(progress, dict) else None
    return value if isinstance(value, str) and value else None


def check_build(state: dict[str, str], held: str | None) -> None:
    """Refuse a push state of another build than the one the store was loaded from: what
    it says was sent is that build's, not what this store holds. Nothing to compare while
    the store gives no build id, or the state names none."""
    build = state.get(BUILD_KEY)
    if held and build and held != build:
        raise StoreOfOtherBuild(
            f"The store was loaded from build {held}; the push state is of build {build}."
            " Push with a state of the build the store holds: thenwhat store fresh-state"
            " <that build's store file> --url <this store's address> --out <new state file>."
        )


AFTER_RELOAD = (
    "After any reload or restore: thenwhat store fresh-state <store file> --url <address>"
    " --out <new state file>, then thenwhat backfill slices run --push --again --state"
    " <new state file>."
)
RELOADED = (
    "The store holds no slice of this set, but this device's push state or plan says some"
    " were sent: the store was loaded again. " + AFTER_RELOAD
)


SINCE_KEY = "\tdatabase since"


def check_since(state: dict[str, str], progress: Any) -> bool:
    """Refuse a store whose database was created again since the push state first saw it
    (its `GET /progress` `database_since` moved): what the state says was sent went to
    the old one. A state that has not seen it takes it; True when it did."""
    since = progress.get("database_since") if isinstance(progress, dict) else None
    if not isinstance(since, str) or not since:
        return False
    held = state.get(SINCE_KEY)
    if held is None:
        state[SINCE_KEY] = since
        return True
    if held != since:
        raise PushFailed(
            f"The store's database was created again: it dates from {since}, the push state"
            f" from {held}, so what the state says was sent went to the old one. " + AFTER_RELOAD
        )
    return False


def check_store(client: httpx.Client, state: dict[str, str]) -> tuple[Any, bool]:
    """Before a push: the store's `GET /progress`, refusing a store loaded from another
    build than the state's or whose database was created again since the state saw it.
    The answer (None when the service gives none) and whether the state took the store's
    `database_since` and is to be written."""
    answer = client.get("/progress")
    progress = answer.json() if answer.status_code == 200 else None
    check_build(state, store_build(progress))
    return progress, check_since(state, progress)


def slices_held(progress: Any, rule: str, year: int) -> int | None:
    """How many slices of a set the store holds, by its `GET /progress`; None when the
    answer is not one to read that from."""
    if not isinstance(progress, dict) or not isinstance(progress.get("sets"), list):
        return None
    for one in progress["sets"]:
        if isinstance(one, dict) and (one.get("rule"), one.get("year")) == (rule, year):
            return int(one.get("total_slices") or 0)
    return 0


class PendingStale(PushFailed):
    """A run left pending belongs to another build or another store than this one."""


def write_pending(
    path: Path, run: str, records: list[Record], belongs: dict[str, str] | None = None
) -> None:
    """The run about to be sent, written whole before anything is sent, with what it
    belongs to: the build its state holds and the store it is sent to."""
    temporary = path.with_name(path.name + ".part")
    value = {"run": run, "belongs": belongs or {}, "records": [r.staged() for r in records]}
    temporary.write_text(json.dumps(value, ensure_ascii=False))
    temporary.replace(path)


def read_pending(path: Path) -> tuple[str, list[Record], dict[str, str]] | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text())
    records = [Record(**record) for record in value["records"]]
    return value["run"], records, value.get("belongs") or {}


def check_belongs(path: Path, found: dict[str, str], now: dict[str, str]) -> None:
    """Refuse to settle a pending run made for another build or store: settled against a
    store loaded since from a new build, its records would be there twice."""
    differ = {k: (found.get(k), v) for k, v in now.items() if found.get(k) != v}
    if differ:
        said = "; ".join(f"{k}: the run's {was!r}, now {is_!r}" for k, (was, is_) in differ.items())
        raise PendingStale(
            f"{path} holds a run made for another build or store ({said}). If the store was"
            " rebuilt and loaded since, that build holds the run's records: delete the file"
            " and push again. If not, run with the build and the store the run was made for."
        )


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
    belongs: dict[str, str] | None = None,
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
    target = (belongs or {}).get("target")
    if target:
        check_target(state, target)
    if pending is not None and not report_only:
        held = read_pending(pending)
        if held is not None:
            run, records_of_run, found = held
            check_belongs(pending, found, belongs or {})
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
            write_pending(pending, run, records_of_run, belongs)
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
    # Only a run still open needs its large payloads: one merged already settles without.
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
        raise PushFailed(
            f"Run {run} was not merged: {json.dumps(result)[:400]}. It stays pending: push"
            " again to send it again; if it fails the same way, read why with GET"
            f" /runs/<id>, fix it, delete {PENDING_HINT} and push again."
        )
    _count(report, result, counts)


PENDING_HINT = "the state file's .pending.json"


def _count(report: PushReport, result: dict[str, Any], counts: Counter[str]) -> None:
    for kind, numbers in (result.get("report") or {}).items():
        if isinstance(numbers, dict):
            report.added[kind] += int(numbers.get("added", 0))
            report.resolved[kind] += int(numbers.get("resolved", 0))
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
