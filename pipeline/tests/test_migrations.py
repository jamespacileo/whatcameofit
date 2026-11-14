from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

EXPECTED_TABLES = {
    "claim",
    "source_article",
    "promise",
    "entity",
    "entity_match",
    "evidence_event",
    "failure_flag",
    "decision_log",
    "llm_usage",
    "http_cache",
    "outlet_icon",
    "paper_record",
    "claim_term",
    "term_record",
}


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_upgrade_creates_every_table(engine: Engine):
    assert _tables(engine) == EXPECTED_TABLES


def test_downgrade_removes_everything_and_upgrade_restores_it(
    engine: Engine, alembic_config: Config
):
    try:
        command.downgrade(alembic_config, "base")
        assert _tables(engine) == set()
    finally:
        command.upgrade(alembic_config, "head")

    assert _tables(engine) == EXPECTED_TABLES


def test_migrations_match_models(engine: Engine, alembic_config: Config):
    # Raises if the models have changes that no migration covers.
    command.check(alembic_config)
