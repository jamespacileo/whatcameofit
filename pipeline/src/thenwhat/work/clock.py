"""The clock every call and every wait reads: injected, so that a test moves it and
records what was slept, and nothing waits for real."""

import time as system_time
from datetime import UTC, datetime
from typing import Protocol


class Time(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class SystemTime:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return system_time.monotonic()

    def sleep(self, seconds: float) -> None:
        system_time.sleep(seconds)


def when(moment: datetime) -> str:
    """A time as the operator is told it."""
    return moment.strftime("%Y-%m-%d %H:%M UTC")
