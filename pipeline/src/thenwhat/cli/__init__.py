"""Command-line interface for the thenwhat pipeline."""

import typer
from pydantic import ValidationError
from rich.console import Console
from sqlalchemy.exc import OperationalError

from thenwhat import __version__
from thenwhat.config import load_settings
from thenwhat.db.session import make_engine, ping

app = typer.Typer(no_args_is_help=True)
out = Console()
err = Console(stderr=True)


@app.callback()
def main() -> None:
    """Track what happened to reported medical breakthroughs."""


@app.command()
def version() -> None:
    """Print the pipeline version."""
    out.print(__version__)


@app.command("db-check")
def db_check() -> None:
    """Check that the database is reachable."""
    try:
        settings = load_settings()
    except ValidationError:
        err.print("DATABASE_URL is not set.")
        raise typer.Exit(code=1) from None
    try:
        ping(make_engine(settings.database_url))
    except OperationalError:
        err.print("Database is not reachable.")
        raise typer.Exit(code=1) from None
    out.print("Database is reachable.")
