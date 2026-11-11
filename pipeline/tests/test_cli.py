from typer.testing import CliRunner

from thenwhat import __version__
from thenwhat.cli import app

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
