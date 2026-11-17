"""Spans kept as files: one line a span or an event, one file a day and a kind.
Behavior: openspec processing-metrics.

Single-step measurements are kept where they were made for a set number of days and
then removed; the daily totals made from them are what is kept for good. A reader's
lookup has its own, shorter, number of days.

`FileWriter` writes them on a thread of its own, so that measuring costs the work
almost nothing: a worker hands a line on and goes on. Lines are written several at a
time, at least once a second, to files held open. When lines are made faster than they
can be written, the worker waits for room rather than a line being dropped, and the
wait is measured under a cause of its own. A write that fails is counted, does not stop
the work, and is written as an event once writing works again; if it never does, the
process says so as it exits.
"""

import atexit
import fcntl
import json
import os
import sys
import threading
import time as system_time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from thenwhat.measure.spans import (
    PROCESS,
    WRITER_WAIT,
    Event,
    Span,
    event_from,
    line_from,
    span_from,
    start_line,
)

# The writer a reader's lookup is measured under. Its files are kept a shorter time.
LOOKUP = "lookup"
WORK = "work"
_PREFIX = "spans"

# Lines that may wait to be written before a worker waits for room: several seconds of
# the fastest step's lines.
CAPACITY = 20_000
# Lines gathered before they are written without waiting out the second.
GATHER = 1_000
# The longest a line waits to be written, in seconds.
EVERY_SECONDS = 1.0
# While a record is in hand, a line says this often that its process is alive, so that
# a reader can tell a record still in hand from one whose process stopped.
BEAT_SECONDS = 30.0

# The kinds of line the writer writes of its own.
BEAT = "beat"
NOT_WRITTEN = "not_written"


def _kind(writer: str) -> str:
    return LOOKUP if writer == LOOKUP else WORK


def path_for(folder: Path, day: date, writer: str) -> Path:
    return folder / f"{_PREFIX}-{_kind(writer)}-{day.isoformat()}.jsonl"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _say_on_stderr(words: str) -> None:
    print(words, file=sys.stderr)


@dataclass(slots=True)
class _Unsaid:
    """Lines that could not be written and have not yet been said in an event."""

    spans: int
    lines: int
    since: datetime
    until: datetime
    error_kind: str


class FileWriter:
    """Writes spans, start lines and events to the files of their day, on a thread of
    its own. Two processes may append to one file: each writes whole lines, several at a
    time, holding a lock on the file, so their lines never mix."""

    def __init__(
        self,
        folder: Path,
        *,
        writer: str,
        capacity: int = CAPACITY,
        gather: int = GATHER,
        every: float = EVERY_SECONDS,
        beat: float = BEAT_SECONDS,
        clock: Callable[[], float] = system_time.monotonic,
        now: Callable[[], datetime] = _utc_now,
        say: Callable[[str], None] = _say_on_stderr,
    ) -> None:
        self._folder = folder
        self._writer = writer
        self._capacity = capacity
        self._gather = gather
        self._every = every
        self._beat = beat
        # Measures a worker's wait for room. The thread keeps its own time.
        self._clock = clock
        self._now = now
        self._say = say
        self._lock = threading.Lock()
        # The thread waits on `_gathered` for lines, workers on `_room` for room, and a
        # flush on `_settled` for what it handed on to be written.
        self._gathered = threading.Condition(self._lock)
        self._room = threading.Condition(self._lock)
        self._settled = threading.Condition(self._lock)
        self._items: list[Span | Event] = []
        self._handed = 0
        self._done = 0
        self._wanted = 0
        self._waiting = 0
        self._in_hand = 0
        self._lost = 0
        self._closed = False
        self._gone = False
        self._thread: threading.Thread | None = None
        # Held while the files are written, by the thread or, once it has gone, by the
        # caller. Only the one holding it touches the files and what is unsaid.
        self._writing = threading.Lock()
        self._files: dict[Path, int] = {}
        self._unsaid: _Unsaid | None = None

    # --- handed on by workers -------------------------------------------------------

    def finished(self, span: Span) -> float:
        return self._put(span, span, -1 if span.id is not None else 0)

    def started(self, span: Span) -> float:
        return self._put(start_line(span), None, 1)

    def event(self, event: Event) -> float:
        return self._put(event, None, 0)

    def _put(self, item: Span | Event, charged: Span | None, in_hand: int) -> float:
        waited = 0.0
        with self._lock:
            self._in_hand += in_hand
            gone = self._gone
            if not gone:
                if self._thread is None:
                    self._start()
                if len(self._items) >= self._capacity:
                    began = self._clock()
                    self._waiting += 1
                    self._gathered.notify()
                    while len(self._items) >= self._capacity and not self._gone:
                        self._room.wait()
                    self._waiting -= 1
                    waited = self._clock() - began
                    if charged is not None and waited > 0:
                        charged.waited[WRITER_WAIT] = charged.waited.get(WRITER_WAIT, 0.0) + waited
                self._items.append(item)
                self._handed += 1
                if len(self._items) == 1 or len(self._items) >= self._gather:
                    self._gathered.notify()
        if gone:
            # The thread has gone: what comes after it is written here and now.
            with self._writing:
                self._write([item])
        return waited

    # --- asked for by the process -----------------------------------------------------

    def flush(self) -> None:
        with self._lock:
            if self._thread is None or self._gone:
                return
            target = self._handed
            self._wanted = max(self._wanted, target)
            self._gathered.notify()
            while self._done < target and not self._gone:
                self._settled.wait()

    def not_written(self) -> int:
        with self._lock:
            return self._lost

    def close(self) -> None:
        """Write everything handed on and stop the thread. Lines that could not be
        written and were never said in an event are said on stderr."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._gathered.notify()
            thread = self._thread
        if thread is not None:
            thread.join()
            atexit.unregister(self.close)
        with self._lock:
            self._gone = True
            self._room.notify_all()
        with self._writing:
            if self._unsaid is not None:
                self._say_unsaid()
            unsaid = self._unsaid
            if unsaid is not None:
                self._say(
                    f"Measurements could not be written to {self._folder} since"
                    f" {unsaid.since:%Y-%m-%d %H:%M:%S} UTC ({unsaid.error_kind}):"
                    f" {unsaid.spans:,} measurement{'' if unsaid.spans == 1 else 's'},"
                    f" {unsaid.lines:,} lines in all."
                )
            for handle in self._files.values():
                os.close(handle)
            self._files.clear()

    # --- the thread -------------------------------------------------------------------

    def _start(self) -> None:
        self._thread = threading.Thread(target=self._work, name="measure-writer", daemon=True)
        self._thread.start()
        atexit.register(self.close)

    def _work(self) -> None:
        next_beat = system_time.monotonic() + self._beat
        while True:
            with self._lock:
                first_seen: float | None = None
                beat = False
                while not (
                    self._closed
                    or self._waiting
                    or self._wanted > self._done
                    or len(self._items) >= self._gather
                ):
                    moment = system_time.monotonic()
                    if self._items:
                        first_seen = first_seen if first_seen is not None else moment
                        left: float | None = first_seen + self._every - moment
                    elif self._in_hand > 0:
                        left = next_beat - moment
                    else:
                        next_beat = moment + self._beat
                        left = None
                    if left is not None and left <= 0:
                        beat = not self._items
                        break
                    self._gathered.wait(left)
                batch, self._items = self._items, []
                handed = len(batch)
                closing = self._closed
                self._room.notify_all()
            if beat:
                batch.append(Event(BEAT, self._now(), self._writer, {"process": PROCESS}))
                next_beat = system_time.monotonic() + self._beat
            with self._writing:
                try:
                    self._write(batch)
                except Exception as failure:  # the work would wait for ever on a dead thread
                    spans = sum(isinstance(item, Span) for item in batch)
                    self._count_lost(spans, len(batch), failure)
            with self._lock:
                self._done += handed
                self._settled.notify_all()
                if closing and not self._items:
                    return

    def _write(self, batch: list[Span | Event]) -> None:
        """Write a batch, file by file, with `_writing` held."""
        by_path: dict[Path, list[str]] = {}
        spans: dict[Path, int] = {}
        for item in batch:
            if isinstance(item, Span):
                path = path_for(self._folder, item.started_at.date(), item.writer)
            else:
                path = path_for(self._folder, item.at.date(), item.writer)
            try:
                line = json.dumps(item.as_record(), separators=(",", ":"))
            except (TypeError, ValueError) as failure:
                self._count_lost(int(isinstance(item, Span)), 1, failure)
                continue
            by_path.setdefault(path, []).append(line + "\n")
            if isinstance(item, Span):
                spans[path] = spans.get(path, 0) + 1
        for path, lines in by_path.items():
            try:
                self._append(path, "".join(lines))
            except OSError as failure:
                self._count_lost(spans.get(path, 0), len(lines), failure)
                continue
            if self._unsaid is not None:
                self._say_unsaid()

    def _count_lost(self, spans: int, lines: int, failure: Exception) -> None:
        now = self._now()
        with self._lock:
            self._lost += spans
        if self._unsaid is None:
            self._unsaid = _Unsaid(spans, lines, now, now, type(failure).__name__)
        else:
            self._unsaid.spans += spans
            self._unsaid.lines += lines
            self._unsaid.until = now
            self._unsaid.error_kind = type(failure).__name__

    def _say_unsaid(self) -> None:
        """Writing works again: say in an event what could not be written."""
        unsaid = self._unsaid
        if unsaid is None:
            return
        notice = Event(
            NOT_WRITTEN,
            self._now(),
            self._writer,
            {
                "not_written": unsaid.spans,
                "lines": unsaid.lines,
                "since": unsaid.since.isoformat(),
                "until": unsaid.until.isoformat(),
                "error_kind": unsaid.error_kind,
            },
        )
        line = json.dumps(notice.as_record(), separators=(",", ":")) + "\n"
        try:
            self._append(path_for(self._folder, notice.at.date(), self._writer), line)
        except OSError:
            return
        self._unsaid = None

    def _append(self, path: Path, text: str) -> None:
        handle = self._files.get(path)
        if handle is not None and os.fstat(handle).st_nlink == 0:
            # The file was removed while it was held open: what is written to it now
            # would be lost.
            os.close(self._files.pop(path))
            handle = None
        if handle is None:
            self._folder.mkdir(parents=True, exist_ok=True)
            # A new file: those of another day are done with.
            for other in [held for held in self._files if held.name[-16:] != path.name[-16:]]:
                os.close(self._files.pop(other))
            handle = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            self._files[path] = handle
        data = memoryview(text.encode())
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            while data:
                data = data[os.write(handle, data) :]
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _day_of(path: Path) -> date | None:
    try:
        return date.fromisoformat(path.stem[-10:])
    except ValueError:
        return None


def days_held(folder: Path) -> list[date]:
    """The days there are span files for, oldest first."""
    if not folder.is_dir():
        return []
    return sorted({day for path in folder.glob(f"{_PREFIX}-*.jsonl") if (day := _day_of(path))})


def files_of(folder: Path, day: date) -> list[Path]:
    return [
        path
        for kind in (WORK, LOOKUP)
        if (path := folder / f"{_PREFIX}-{kind}-{day.isoformat()}.jsonl").is_file()
    ]


def read_day(folder: Path, day: date) -> Iterator[Span]:
    """The day's measurements. Its other lines, start lines and events, are left out."""
    for path in files_of(folder, day):
        with path.open(encoding="utf-8") as lines:
            for line in lines:
                # Only a line that is not a span has a kind, and it comes first.
                if line.strip() and not line.startswith('{"kind"'):
                    yield span_from(json.loads(line))


def read_events(folder: Path, day: date, kinds: Iterable[str]) -> Iterator[Event]:
    """The day's events of these kinds."""
    wanted = tuple(f'{{"kind":"{kind}"' for kind in kinds)
    for path in files_of(folder, day):
        with path.open(encoding="utf-8") as lines:
            for line in lines:
                if line.startswith(wanted):
                    yield event_from(json.loads(line))


def last_event(folder: Path, kind: str, before: date) -> Event | None:
    """The latest event of a kind in the files of the days before `before`: the newest
    day is looked at first, and the first day that has one ends the search."""
    for day in reversed([held for held in days_held(folder) if held < before]):
        found = list(read_events(folder, day, [kind]))
        if found:
            return max(found, key=lambda event: event.at)
    return None


class Follower:
    """Reads the day's files from where it last read, while another process writes
    them. Only whole lines are read: one being written is read once it is whole."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder
        self._read: dict[Path, int] = {}
        # Whole lines that could not be read as a span or an event.
        self.unreadable = 0

    def read(self, days: Iterable[date]) -> list[Span | Event]:
        found: list[Span | Event] = []
        for day in days:
            for path in files_of(self._folder, day):
                found.extend(self._read_on(path))
        return found

    def _read_on(self, path: Path) -> list[Span | Event]:
        start = self._read.get(path, 0)
        with path.open("rb") as file:
            file.seek(start)
            data = file.read()
        whole = data.rfind(b"\n") + 1
        self._read[path] = start + whole
        found: list[Span | Event] = []
        for line in data[:whole].splitlines():
            if not line.strip():
                continue
            try:
                found.append(line_from(json.loads(line)))
            except (ValueError, KeyError, TypeError):
                self.unreadable += 1
        return found


def remove_old(folder: Path, *, today: date, keep_days: int, lookup_keep_days: int) -> list[Path]:
    """Remove span files older than their number of days. Returns what was removed."""
    removed: list[Path] = []
    if not folder.is_dir():
        return removed
    for path in sorted(folder.glob(f"{_PREFIX}-*.jsonl")):
        day = _day_of(path)
        if day is None:
            continue
        keep = lookup_keep_days if f"-{LOOKUP}-" in path.name else keep_days
        if day < today - timedelta(days=keep):
            path.unlink()
            removed.append(path)
    return removed
