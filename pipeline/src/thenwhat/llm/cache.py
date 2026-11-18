"""Exact model response reuse on one device, shared by its pipeline processes."""

import json
import sqlite3
from collections.abc import Generator, Sequence
from contextlib import ExitStack, closing, contextmanager
from fcntl import LOCK_EX, flock
from hashlib import sha256
from pathlib import Path
from typing import Any


def request_key(kind: str, request: Any) -> str:
    """Hash the request without keeping its prompts, evidence or article body."""
    wire = json.dumps([1, kind, request], ensure_ascii=True, separators=(",", ":"))
    return sha256(wire.encode()).hexdigest()


class ModelCache:
    def __init__(self, path: Path) -> None:
        self._path = path.expanduser() / "model-responses-v1"

    @contextmanager
    def locked(self, keys: Sequence[str]) -> Generator[None, None, None]:
        """Hold locks through the call so concurrent replays share the first answer.

        Sorted lock buckets bound the number of files and keep a batch deadlock-free.
        Locks release when the process exits. SQLite is only open for brief reads and writes.
        """
        self._path.mkdir(mode=0o700, parents=True, exist_ok=True)
        with ExitStack() as locks:
            for bucket in sorted({key[:3] for key in keys}):
                lock = locks.enter_context((self._path / f"{bucket}.lock").open("ab"))
                flock(lock, LOCK_EX)
            yield

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        with closing(sqlite3.connect(self._path / "responses.sqlite3", timeout=30)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS response (key TEXT PRIMARY KEY, answer TEXT NOT NULL)"
            )
            yield db

    def get(self, key: str) -> Any:
        with self._connect() as db:
            row = db.execute("SELECT answer FROM response WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row is not None else None

    def put(self, key: str, answer: Any) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO response VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET answer=excluded.answer",
                (
                    key,
                    json.dumps(answer, ensure_ascii=True, separators=(",", ":"), allow_nan=False),
                ),
            )
