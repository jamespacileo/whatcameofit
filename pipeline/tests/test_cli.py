from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from thenwhat import __version__
from thenwhat.cli import app
from thenwhat.db.models import HttpCache

runner = CliRunner()


def test_help_lists_commands():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "version" in result.output
    assert "db-check" in result.output


def test_version_prints_package_version():
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.output.strip() == __version__


def test_db_check_names_missing_setting(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    result = runner.invoke(app, ["db-check"])

    assert result.exit_code == 1
    assert "DATABASE_URL" in result.output


def test_cache_prune_says_how_many_it_deleted(session: Session, monkeypatch: pytest.MonkeyPatch):
    now = datetime.now(UTC)
    for key, expires_at in (("old", now - timedelta(days=1)), ("fresh", now + timedelta(days=1))):
        session.add(
            HttpCache(
                request_key=f"demo GET https://demo.test/{key}",
                source_name="demo",
                payload={},
                fetched_at=now - timedelta(days=2),
                expires_at=expires_at,
            )
        )
    session.flush()

    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.session.open_session", test_session)

    result = runner.invoke(app, ["cache-prune"])

    assert result.exit_code == 0
    assert "Deleted 1 expired cached answers." in result.output
    assert session.get(HttpCache, "demo GET https://demo.test/old") is None
    assert session.get(HttpCache, "demo GET https://demo.test/fresh") is not None


def test_cache_prune_names_missing_setting(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    result = runner.invoke(app, ["cache-prune"])

    assert result.exit_code == 1
    assert "DATABASE_URL" in result.output
