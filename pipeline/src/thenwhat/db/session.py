"""Database engine and connectivity check."""

from sqlalchemy import Engine, create_engine, text


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def ping(engine: Engine) -> None:
    """Raise if the database cannot answer a trivial query."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
