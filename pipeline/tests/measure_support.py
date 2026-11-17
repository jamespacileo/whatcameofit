"""Shared pieces for the measurement tests: a recorder's lines kept in lists, and lines
written to a folder the way a run writes them."""

from pathlib import Path

from thenwhat.measure.files import FileWriter
from thenwhat.measure.spans import Event, Span


class Kept:
    """Where a recorder's lines go in a test: kept in lists, in the order handed on."""

    def __init__(self) -> None:
        self.spans: list[Span] = []
        self.starts: list[Span] = []
        self.events: list[Event] = []

    def finished(self, span: Span) -> float:
        self.spans.append(span)
        return 0.0

    def started(self, span: Span) -> float:
        self.starts.append(span)
        return 0.0

    def event(self, event: Event) -> float:
        self.events.append(event)
        return 0.0

    def flush(self) -> None:
        pass

    def not_written(self) -> int:
        return 0

    def close(self) -> None:
        pass


def write(folder: Path, *lines: Span | Event, writer: str = "test") -> None:
    """Write spans and events to the folder's day files through the writer a run uses,
    and wait until they are written."""
    out = FileWriter(folder, writer=writer)
    for line in lines:
        if isinstance(line, Span):
            out.finished(line)
        else:
            out.event(line)
    out.close()
