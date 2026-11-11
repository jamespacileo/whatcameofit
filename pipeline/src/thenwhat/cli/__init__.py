"""Command-line interface for the thenwhat pipeline."""

import typer
from sqlalchemy.exc import OperationalError

from thenwhat import __version__
from thenwhat.cli.console import err, out
from thenwhat.cli.entry import article_app, claim_app, promise_app
from thenwhat.cli.events import event_app, fetch_command
from thenwhat.cli.extract import extract_app
from thenwhat.cli.resolve import entity_app, resolve_command
from thenwhat.cli.session import settings_or_exit
from thenwhat.db.session import make_engine, ping

app = typer.Typer(no_args_is_help=True)
app.add_typer(claim_app, name="claim")
app.add_typer(article_app, name="article")
app.add_typer(promise_app, name="promise")
app.add_typer(extract_app, name="extract")
app.add_typer(entity_app, name="entity")
app.command("resolve")(resolve_command)
app.command("fetch")(fetch_command)
app.add_typer(event_app, name="event")


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
    settings = settings_or_exit()
    try:
        ping(make_engine(settings.database_url))
    except OperationalError:
        err.print("Database is not reachable.")
        raise typer.Exit(code=1) from None
    out.print("Database is reachable.")
