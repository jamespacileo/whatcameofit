"""Database fixtures. Tests run against a throwaway Postgres database, on the test
suite's own server, that is dropped and rebuilt from the migrations at the start of
every test session."""

import hashlib
import json
import os
import re
import socket
from collections.abc import Callable, Iterator, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

PIPELINE_ROOT = Path(__file__).resolve().parents[1]

# Where the working database listens on this machine (compose.yaml, `db`). Tests are
# never run on that server: they drop and recreate a database, and a drop under load
# has brought it down.
WORKING_PORT = 5433
WORKING_DATABASE = "thenwhat"
# The test suite's own server (compose.yaml, `test-db`).
TEST_PORT = 5434


class NotATestDatabase(RuntimeError):
    """The address given for the tests is not one a test may drop a database at."""


def default_test_database(checkout: Path) -> str:
    """A database name of this checkout's own, so that two checkouts running their tests
    at once on the one test server do not drop each other's."""
    checkout = checkout.resolve()
    name = re.sub(r"[^a-z0-9]+", "_", checkout.name.lower()).strip("_")[:24] or "checkout"
    identity = hashlib.sha256(os.fsencode(checkout)).hexdigest()[:16]
    return f"thenwhat_{name}_{identity}_test"


def database_for_tests(environ: Mapping[str, str], checkout: Path = PIPELINE_ROOT.parent) -> URL:
    """The database the tests drop and rebuild: `TEST_DATABASE_URL`, or this checkout's
    own database on the test server. Refused when it could be the working database or
    any database on the working database's server."""
    given = environ.get("TEST_DATABASE_URL")
    if given:
        url = make_url(given)
    else:
        port = int(environ.get("TEST_DB_PORT", TEST_PORT))
        url = make_url(
            f"postgresql+psycopg://thenwhat:thenwhat@127.0.0.1:{port}/"
            + default_test_database(checkout)
        )
    name = url.database or ""
    if not name.endswith("_test") or name == WORKING_DATABASE:
        raise NotATestDatabase(
            f"Tests drop the database they are given, so its name must end in _test: {name!r}"
            " does not. Leave TEST_DATABASE_URL unset to use the test server (make test-db-up)."
        )
    if len(name.encode()) > 63:
        raise NotATestDatabase("The test database name exceeds PostgreSQL's 63-byte limit.")
    working_ports = {WORKING_PORT}
    if environ.get("DB_PORT", "").isdigit():
        working_ports.add(int(environ["DB_PORT"]))
    servers = {(url.host or "", url.port or 5432)}
    working = {("127.0.0.1", port) for port in working_ports} | {
        ("localhost", port) for port in working_ports
    }
    if environ.get("DATABASE_URL"):
        database = make_url(environ["DATABASE_URL"])
        working.add((database.host or "", database.port or 5432))
    if servers & working:
        raise NotATestDatabase(
            f"Tests are not run on the working database's server ({url.host}:{url.port}): a"
            " dropped database there has brought it down. Leave TEST_DATABASE_URL unset, or"
            f" point it at the test server on port {TEST_PORT} (make test-db-up)."
        )
    return url


def for_worker(url: URL, environ: Mapping[str, str]) -> URL:
    """The database of one worker of a parallel run (`pytest -n`): the run's database with
    the worker's name in it, so that each worker drops and rebuilds its own. A run that
    is not parallel has no worker and keeps the database as given."""
    worker = environ.get("PYTEST_XDIST_WORKER")
    if not worker:
        return url
    name = url.database or ""
    derived = f"{name.removesuffix('_test')}_{worker}_test"
    if len(derived.encode()) > 63:
        # Keep the whole checkout and worker identity even when their label cannot fit.
        identity = hashlib.sha256(derived.encode()).hexdigest()[:32]
        derived = f"thenwhat_{identity}_test"
    return url.set(database=derived)


_resolved: URL | None = None


def pytest_configure(config: pytest.Config) -> None:
    """Settle the tests' database before anything runs, from the environment as the run
    was started, and stop the run with the reason when it is not one tests may use."""
    global _resolved
    try:
        _resolved = for_worker(database_for_tests(os.environ), os.environ)
    except NotATestDatabase as refused:
        raise pytest.UsageError(str(refused)) from None


def _test_url() -> URL:
    assert _resolved is not None
    return _resolved


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


# --- the same export from the truth store -----------------------------------------

# Test modules whose every test also holds, when it is over, that the export taken from a
# SQLite file of the truth store's schema is the one the test database gives (openspec
# truth-store, "The export is assembled once, from either store"). They are the modules
# that test the export through `build_export`, so each scenario of theirs is one more
# set of records the two readers must agree on.
EXPORT_MODULES = {
    "test_export",
    "test_organisations",
    "test_outlet_icons",
    "test_record_readings",
    "test_related_research",
    "test_seed",
}
EXPORTED_AT = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def same_export_from_the_store(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[None]:
    swept = request.module.__name__ in EXPORT_MODULES and "session" in request.fixturenames
    # Asked for before the test runs, so that it is still open when the test is over.
    session = request.getfixturevalue("session") if swept else None
    yield
    if session is not None:
        from store_support import assert_same_export

        assert_same_export(session, tmp_path_factory.mktemp("store"), EXPORTED_AT)


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


# --- measurements ----------------------------------------------------------------


@pytest.fixture
def measured_spans() -> Iterator[list[Any]]:
    """Record every span made during a test, in the order they finished."""
    from measure_support import Kept
    from thenwhat.measure import spans as measure

    kept = Kept()
    measure.use(measure.Recorder(out=kept, writer="test"))
    yield kept.spans
    measure.use(None)
