"""Migration 0013 lets a subject term link be a kind link or a named-gene link, keeps
the links already stored, and refuses to go back while a row holds a new value."""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

LINK = (
    "INSERT INTO claim_term (claim_id, role, source_name, external_id, label, score, fit)"
    " VALUES ((SELECT id FROM claim WHERE slug = 'wrist-device'), :role, :source, :id, :label,"
    " 0.9, :fit)"
)
STORED = {"role": "condition", "source": "mesh", "id": "D005879", "label": "T", "fit": "exact"}
KIND = {"role": "intervention", "source": "mesh", "id": "D004599", "label": "E", "fit": "kind"}
GENE = {"role": "target", "source": "opentargets", "id": "ENSG00000186810", "label": "CXCR3"}


def _links(engine: Engine) -> list[tuple[str, str]]:
    with engine.connect() as connection:
        return [
            (role, fit)
            for role, fit in connection.execute(
                text("SELECT role, fit FROM claim_term ORDER BY id")
            )
        ]


@pytest.fixture
def stored_link(engine: Engine, alembic_config: Config) -> Iterator[None]:
    """A claim with one link, stored under the schema before this migration."""
    command.downgrade(alembic_config, "0012")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO claim (slug, headline, summary, vertical, indication)"
                " VALUES ('wrist-device', 'h', '', 'brain-and-nerves', 'Tourette syndrome')"
            )
        )
        connection.execute(text(LINK), STORED)
    try:
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM claim_term"))
            connection.execute(text("DELETE FROM claim"))
        command.upgrade(alembic_config, "head")


@pytest.mark.usefixtures("stored_link")
def test_upgrade_keeps_stored_links_and_allows_the_new_values(
    engine: Engine, alembic_config: Config
):
    for new in (KIND, GENE | {"fit": "exact"}):
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(text(LINK), new)

    command.upgrade(alembic_config, "0013")

    with engine.begin() as connection:
        connection.execute(text(LINK), KIND)
        connection.execute(text(LINK), GENE | {"fit": "exact"})
    assert _links(engine) == [("condition", "exact"), ("intervention", "kind"), ("target", "exact")]


@pytest.mark.usefixtures("stored_link")
def test_downgrade_refuses_while_a_row_holds_a_new_value_and_reverses_without(
    engine: Engine, alembic_config: Config
):
    command.upgrade(alembic_config, "0013")
    with engine.begin() as connection:
        connection.execute(text(LINK), KIND)

    with pytest.raises(RuntimeError, match=r"1 row\(s\) of claim_term hold fit kind"):
        command.downgrade(alembic_config, "0012")

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM claim_term WHERE fit = 'kind'"))
        connection.execute(text(LINK), GENE | {"fit": None})
    with pytest.raises(RuntimeError, match=r"1 row\(s\) of claim_term hold role target"):
        command.downgrade(alembic_config, "0012")

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM claim_term WHERE role = 'target'"))
    command.downgrade(alembic_config, "0012")

    assert _links(engine) == [("condition", "exact")]
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(LINK), KIND)
