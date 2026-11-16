"""Spans kept as files: one line a span, one file a day and a kind.
Behavior: openspec processing-metrics.

Single-step measurements are kept where they were made for a set number of days and
then removed; the daily totals made from them are what is kept for good. A reader's
lookup has its own, shorter, number of days.
"""

import json
import threading
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

from thenwhat.measure.spans import Span, span_from

# The writer a reader's lookup is measured under. Its files are kept a shorter time.
LOOKUP = "lookup"
WORK = "work"
_PREFIX = "spans"


def _kind(writer: str) -> str:
    return LOOKUP if writer == LOOKUP else WORK


def path_for(folder: Path, day: date, writer: str) -> Path:
    return folder / f"{_PREFIX}-{_kind(writer)}-{day.isoformat()}.jsonl"


class FileSink:
    """Appends each finished span to the file of its day. One line is written in one
    call, so two processes writing the same file do not mix their lines."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder
        self._lock = threading.Lock()

    def __call__(self, span: Span) -> None:
        line = json.dumps(span.as_record(), separators=(",", ":")) + "\n"
        path = path_for(self._folder, span.started_at.date(), span.writer)
        with self._lock:
            self._folder.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as out:
                out.write(line)


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


def read_day(folder: Path, day: date) -> Iterator[Span]:
    for kind in (WORK, LOOKUP):
        path = folder / f"{_PREFIX}-{kind}-{day.isoformat()}.jsonl"
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as lines:
            for line in lines:
                if line.strip():
                    yield span_from(json.loads(line))


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
