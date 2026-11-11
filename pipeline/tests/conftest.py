"""Database fixtures. Tests run against a throwaway Postgres database that is
dropped and rebuilt from the migrations at the start of every test session."""

import os
from collections.abc import Iterator
from pathlib import Path

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
