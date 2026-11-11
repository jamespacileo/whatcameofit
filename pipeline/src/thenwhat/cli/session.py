"""Database session for one CLI command: committed on success, rolled back on failure."""

from collections.abc import Generator
from contextlib import contextmanager

import typer
from pydantic import ValidationError
from sqlalchemy.orm import Session

from thenwhat.cli.console import err
from thenwhat.config import Settings, load_settings
from thenwhat.db.session import make_engine


def settings_or_exit() -> Settings:
    try:
        return load_settings()
    except ValidationError:
        err.print("DATABASE_URL is not set.")
        raise typer.Exit(code=1) from None


@contextmanager
def open_session() -> Generator[Session]:
    engine = make_engine(settings_or_exit().database_url)
    with Session(engine) as session, session.begin():
        yield session
