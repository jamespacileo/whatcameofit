from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

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
    "measure_daily",
    "measure_claim",
    "measure_rolled_day",
    "http_cache",
    "outlet_icon",
    "paper_record",
    "claim_term",
    "term_record",
    "reported_statement",
    "organisation_record",
    "entity_article",
    "work_entry",
    "source_allowance_use",
    "registry_trial",
    "registry_load",
    "article_lead",
    "entity_substance",
    "trial_read",
    "reading",
    "link_lead",
    "link_share",
    "link_lead_link",
    "link_lead_label",
}

# The migration that records where an entity was named (openspec organisations).
NAMED_BY_REVISION = "0012"


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


def test_unknown_stage_default_migration_preserves_existing_statuses(
    engine: Engine, alembic_config: Config
):
    command.downgrade(alembic_config, "0021")
    try:
        _run(
            engine,
            "INSERT INTO claim (slug, headline, summary, vertical, indication)"
            " VALUES ('before-stage-default', 'h', '', 'pain', 'Pain')",
        )
        command.upgrade(alembic_config, "0022")
        _run(
            engine,
            "INSERT INTO claim (slug, headline, summary, vertical, indication)"
            " VALUES ('after-stage-default', 'h', '', 'pain', 'Pain')",
        )
        with engine.connect() as connection:
            statuses = dict(
                connection.execute(
                    text(
                        "SELECT slug, current_status FROM claim"
                        " WHERE slug IN ('before-stage-default', 'after-stage-default')"
                    )
                ).all()
            )
        assert statuses == {
            "before-stage-default": "preclinical_only",
            "after-stage-default": "no_trial_found",
        }
    finally:
        _run(
            engine,
            "DELETE FROM claim WHERE slug IN ('before-stage-default', 'after-stage-default')",
        )
        command.upgrade(alembic_config, "head")


def _entity_columns(engine: Engine) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("entity")}


def _run(engine: Engine, *statements: str) -> None:
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def test_existing_entities_are_named_by_an_article(engine: Engine, alembic_config: Config):
    """Existing entities are marked as named by an article. An organisation on a claim
    with one article is linked to it; on a claim with two, which one named it is unknown."""
    command.downgrade(alembic_config, f"{NAMED_BY_REVISION}-1")
    try:
        _run(
            engine,
            "INSERT INTO claim (slug, headline, summary, vertical, indication)"
            " VALUES ('one-report', 'h', '', 'pain', 'Pain'),"
            " ('two-reports', 'h', '', 'pain', 'Pain')",
            "INSERT INTO source_article (claim_id, url, outlet, title, published_date)"
            " SELECT id, 'https://example.org/' || slug || '/' || n, 'Example', 't', '2026-01-01'"
            " FROM claim, generate_series(1, CASE WHEN slug = 'one-report' THEN 1 ELSE 2 END) n",
            "INSERT INTO entity (claim_id, type, name)"
            " SELECT id, 'institution', 'University of Nottingham' FROM claim",
        )

        command.upgrade(alembic_config, NAMED_BY_REVISION)
        with engine.connect() as connection:
            named_by = connection.execute(text("SELECT named_by FROM entity")).scalars().all()
            linked = (
                connection.execute(
                    text(
                        "SELECT source_article.url FROM entity_article JOIN source_article"
                        " ON source_article.id = entity_article.source_article_id"
                    )
                )
                .scalars()
                .all()
            )
        assert named_by == [["article"], ["article"]]
        assert linked == ["https://example.org/one-report/1"]

        command.downgrade(alembic_config, f"{NAMED_BY_REVISION}-1")
        assert "named_by" not in _entity_columns(engine)
        assert not {"organisation_record", "entity_article"} & _tables(engine)
    finally:
        _run(engine, "DELETE FROM entity", "DELETE FROM source_article", "DELETE FROM claim")
        command.upgrade(alembic_config, "head")
    assert "named_by" in _entity_columns(engine)
