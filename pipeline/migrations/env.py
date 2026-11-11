"""Alembic environment. The database URL comes from DATABASE_URL, or from
`config.attributes["url"]` when a caller such as the test suite supplies one."""

from alembic import context
from sqlalchemy import create_engine

from thenwhat.config import load_settings
from thenwhat.db.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations() -> None:
    url = config.attributes.get("url") or load_settings().database_url
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline migrations are not supported; run against a database.")

run_migrations()
