"""The tests' own database: where it is, and that the working database is refused."""

import re
from pathlib import Path

import pytest

from conftest import NotATestDatabase, database_for_tests, for_worker

CHECKOUT = Path("/work/d1-export-from-store-b403d7")


def test_default_is_this_checkouts_own_database_on_the_test_server():
    url = database_for_tests({}, CHECKOUT)

    assert (url.host, url.port) == ("127.0.0.1", 5434)
    assert re.fullmatch(r"thenwhat_d1_export_from_store_b40_[0-9a-f]{16}_test", url.database or "")
    assert database_for_tests({}, Path("/work/another")).database != url.database
    assert database_for_tests({"TEST_DB_PORT": "5544"}, CHECKOUT).port == 5544


def test_same_basename_checkouts_are_distinct_and_aliases_are_stable(tmp_path: Path):
    name = "very-long-project-name-" * 4
    left = tmp_path / "a" / name
    right = tmp_path / "b" / name
    left.mkdir(parents=True)
    right.mkdir(parents=True)
    alias = tmp_path / "alias"
    alias.symlink_to(left, target_is_directory=True)

    for worker in ("", "gw0", "gw" + "9" * 55):
        env = {"PYTEST_XDIST_WORKER": worker}
        one = for_worker(database_for_tests({}, left), env).database
        two = for_worker(database_for_tests({}, right), env).database
        assert one and two and one != two
        assert max(len(one.encode()), len(two.encode())) <= 63
        assert one.endswith("_test") and two.endswith("_test")
        assert for_worker(database_for_tests({}, alias), env).database == one


def test_an_explicit_overlong_database_name_is_refused_before_use():
    name = "é" * 30 + "_test"
    with pytest.raises(NotATestDatabase, match="63-byte"):
        database_for_tests({"TEST_DATABASE_URL": f"postgresql://localhost:5434/{name}"}, CHECKOUT)


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


def test_each_worker_of_a_parallel_run_has_a_database_of_its_own():
    url = database_for_tests({}, CHECKOUT)

    first = for_worker(url, {"PYTEST_XDIST_WORKER": "gw0"})
    second = for_worker(url, {"PYTEST_XDIST_WORKER": "gw1"})

    assert url.database is not None
    assert first.database == f"{url.database.removesuffix('_test')}_gw0_test"
    assert second.database == f"{url.database.removesuffix('_test')}_gw1_test"
    assert (first.host, first.port) == (url.host, url.port)
    assert for_worker(url, {}) == url
