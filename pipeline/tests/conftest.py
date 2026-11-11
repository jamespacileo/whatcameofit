"""Database fixtures. Tests run against a throwaway Postgres database that is
dropped and rebuilt from the migrations at the start of every test session."""

import json
import os
import socket
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

DEFAULT_TEST_URL = "postgresql+psycopg://thenwhat:thenwhat@127.0.0.1:5433/thenwhat_test"
PIPELINE_ROOT = Path(__file__).resolve().parents[1]


def _test_url() -> URL:
    url = make_url(os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_URL))
    if not (url.database or "").endswith("_test"):
        # The session fixture drops this database, so never accept a real one.
        raise RuntimeError("TEST_DATABASE_URL must name a database whose name ends in _test.")
    return url


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    config = Config(PIPELINE_ROOT / "alembic.ini")
    config.attributes["url"] = _test_url().render_as_string(hide_password=False)
    return config


@pytest.fixture(scope="session")
def engine(alembic_config: Config) -> Iterator[Engine]:
    url = _test_url()
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    command.upgrade(alembic_config, "head")
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose work is rolled back after the test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


# --- no internet ---------------------------------------------------------------


class NetworkBlocked(RuntimeError):
    """A test tried to open a network connection."""


@pytest.fixture(autouse=True)
def no_internet(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any test that opens a network connection from Python.

    Loopback is blocked too: a local proxy would otherwise carry requests out.
    The test database is unaffected because its driver connects outside Python's
    socket module.
    """

    def connect(self: socket.socket, address: Any, *args: Any) -> Any:
        raise NetworkBlocked(f"Test tried to connect to {address}. Tests must replay fixtures.")

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect)


# --- registry fixtures and controllable time -------------------------------------

FIXTURES = PIPELINE_ROOT / "tests" / "fixtures"


@pytest.fixture
def fixture_json() -> Callable[[str], dict[str, Any]]:
    """Load a recorded registry response, for example `fixture_json("crossref/work.json")`."""

    def load(relative_path: str) -> dict[str, Any]:
        return json.loads((FIXTURES / relative_path).read_text())

    return load


class FakeTime:
    """Time that only moves when told to, or when something sleeps."""

    def __init__(self) -> None:
        self.wall = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.elapsed = 0.0
        self.slept: list[float] = []

    def now(self) -> datetime:
        return self.wall

    def monotonic(self) -> float:
        return self.elapsed

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.wall += timedelta(seconds=seconds)
        self.elapsed += seconds  # kept as a float: timedelta would round it

    def advance(self, by: timedelta) -> None:
        self.wall += by
        self.elapsed += by.total_seconds()


@pytest.fixture
def fake_time() -> FakeTime:
    return FakeTime()
