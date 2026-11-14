"""Migration 0016 lets a subject term link be a drug source's record of the intervention,
and refuses to go back while a row is one."""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

LINK = (
    "INSERT INTO claim_term (claim_id, role, source_name, external_id, label, fit)"
    " VALUES ((SELECT id FROM claim WHERE slug = 'named-drug'), :role, 'opentargets', :id, 'X',"
    " 'exact')"
)
GENE = {"role": "target", "id": "ENSG00000186810"}
DRUG = {"role": "drug", "id": "CHEMBL4297839"}


@pytest.fixture
def at_0015(engine: Engine, alembic_config: Config) -> Iterator[None]:
    """A claim with one named-gene link, stored under the schema before this migration."""
    command.downgrade(alembic_config, "0015")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO claim (slug, headline, summary, vertical, indication)"
                " VALUES ('named-drug', 'h', '', 'hormones-and-metabolism', 'Obesity')"
            )
        )
        connection.execute(text(LINK), GENE)
    try:
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM claim_term"))
            connection.execute(text("DELETE FROM claim"))
        command.upgrade(alembic_config, "head")


@pytest.mark.usefixtures("at_0015")
def test_upgrade_allows_a_drug_link_and_downgrade_refuses_while_one_is_stored(
    engine: Engine, alembic_config: Config
):
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(LINK), DRUG)

    command.upgrade(alembic_config, "0016")
    with engine.begin() as connection:
        connection.execute(text(LINK), DRUG)

    with pytest.raises(RuntimeError, match=r"1 row\(s\) of claim_term hold role drug"):
        command.downgrade(alembic_config, "0015")

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM claim_term WHERE role = 'drug'"))
    command.downgrade(alembic_config, "0015")

    with engine.connect() as connection:
        kept = [role for (role,) in connection.execute(text("SELECT role FROM claim_term"))]
    assert kept == ["target"]
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(LINK), DRUG)
