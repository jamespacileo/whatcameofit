"""Migration 0006 refiles stored claims under the revised verticals, or stops."""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text

ROWS = (
    ("back-disc-gel", "pain", "Chronic low back pain from degenerative disc disease"),
    ("gum-membrane", "dental-regeneration", "Periodontitis"),
    ("enamel-gel", "dental-regeneration", "Enamel loss from tooth decay"),
    ("liver-drug", "diabetes-and-metabolism", "Metabolic dysfunction-associated steatohepatitis"),
    ("pig-kidney", "transplants", "End-stage kidney failure"),
)


def _insert(engine: Engine, rows: tuple[tuple[str, str, str], ...]) -> None:
    with engine.begin() as connection:
        for slug, vertical, indication in rows:
            connection.execute(
                text(
                    "INSERT INTO claim (slug, headline, summary, vertical, indication)"
                    " VALUES (:slug, 'h', '', :vertical, :indication)"
                ),
                {"slug": slug, "vertical": vertical, "indication": indication},
            )


@pytest.fixture
def at_0005(engine: Engine, alembic_config: Config) -> Iterator[None]:
    command.downgrade(alembic_config, "0005")
    try:
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM claim"))
        command.upgrade(alembic_config, "head")


@pytest.mark.usefixtures("at_0005")
def test_upgrade_refiles_old_verticals(engine: Engine, alembic_config: Config):
    _insert(engine, ROWS)

    command.upgrade(alembic_config, "0006")

    with engine.connect() as connection:
        rows = dict(
            (slug, (vertical, approach))
            for slug, vertical, approach in connection.execute(
                text("SELECT slug, vertical, approach FROM claim")
            )
        )
    assert rows == {
        "back-disc-gel": ("bones-joints-and-muscles", None),
        "gum-membrane": ("gum-disease", None),
        "enamel-gel": ("mouth-and-teeth", None),
        "liver-drug": ("gut-and-liver", None),
        "pig-kidney": ("kidneys-and-bladder", "transplant"),
    }


@pytest.mark.usefixtures("at_0005")
def test_upgrade_stops_on_a_claim_it_cannot_place(engine: Engine, alembic_config: Config):
    _insert(engine, (("face-transplant", "transplants", "Severe facial injury"),))

    with pytest.raises(RuntimeError, match=r"face-transplant \(transplants\)"):
        command.upgrade(alembic_config, "0006")
