"""The tests' own database: where it is, and that the working database is refused."""

from pathlib import Path

import pytest

from conftest import NotATestDatabase, database_for_tests

CHECKOUT = Path("/work/d1-export-from-store-b403d7")


def test_default_is_this_checkouts_own_database_on_the_test_server():
    url = database_for_tests({}, CHECKOUT)

    assert (url.host, url.port) == ("127.0.0.1", 5434)
    assert url.database == "thenwhat_d1_export_from_store_b403d7_test"
    assert database_for_tests({}, Path("/work/another")).database != url.database
    assert database_for_tests({"TEST_DB_PORT": "5544"}, CHECKOUT).port == 5544


def test_a_named_test_database_on_another_server_is_used():
    url = database_for_tests(
        {"TEST_DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:5434/mine_test"}, CHECKOUT
    )

    assert url.database == "mine_test"


@pytest.mark.parametrize(
    "environ",
    [
        # The working database's port on this machine, under any name.
        {"TEST_DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:5433/thenwhat_test"},
        {"TEST_DATABASE_URL": "postgresql+psycopg://u:p@localhost:5433/mine_test"},
        # A working database moved to another port, or on another host.
        {
            "TEST_DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1:6000/mine_test",
            "DB_PORT": "6000",
        },
        {
            "TEST_DATABASE_URL": "postgresql+psycopg://u:p@db.internal:5432/mine_test",
            "DATABASE_URL": "postgresql+psycopg://u:p@db.internal:5432/thenwhat",
        },
        {"TEST_DB_PORT": "5433"},
    ],
)
def test_the_working_databases_server_is_refused(environ: dict[str, str]):
    with pytest.raises(NotATestDatabase, match="not run on the working database's server"):
        database_for_tests(environ, CHECKOUT)


@pytest.mark.parametrize("name", ["thenwhat", "mine", "thenwhat_tests"])
def test_a_database_not_named_as_a_test_database_is_refused(name: str):
    with pytest.raises(NotATestDatabase, match="must end in _test"):
        database_for_tests(
            {"TEST_DATABASE_URL": f"postgresql+psycopg://u:p@127.0.0.1:5434/{name}"}, CHECKOUT
        )
