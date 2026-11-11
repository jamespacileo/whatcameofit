"""Promise date parsing, tested through `parse_promise_date`."""

from datetime import date

import pytest

from thenwhat.claims.promises import parse_promise_date

PUBLISHED = date(2018, 3, 10)


def test_year_only_promise_means_the_end_of_that_year():
    """Scenario: Year-only promise"""
    assert parse_promise_date("by 2025", PUBLISHED) == date(2025, 12, 31)


def test_relative_promise_counts_from_the_article_date():
    """Scenario: Relative promise"""
    assert parse_promise_date("within five years", PUBLISHED) == date(2023, 3, 10)


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("human trials by the end of 2024", date(2024, 12, 31)),
        ("on the market in 2030", date(2030, 12, 31)),
        ("Within 5 years", date(2023, 3, 10)),
        ("available in the next three years", date(2021, 3, 10)),
        ("trials could begin in a year", date(2019, 3, 10)),
        ("in ten years' time", date(2028, 3, 10)),
    ],
)
def test_common_wordings_are_understood(description: str, expected: date):
    assert parse_promise_date(description, PUBLISHED) == expected


@pytest.mark.parametrize(
    "description",
    [
        "in the near future",
        "soon",
        "between 2024 and 2026",
        "within months",
        "",
    ],
)
def test_wording_without_one_clear_date_gives_no_date(description: str):
    assert parse_promise_date(description, PUBLISHED) is None


def test_relative_promise_from_a_leap_day_lands_on_28_february():
    assert parse_promise_date("within one year", date(2020, 2, 29)) == date(2021, 2, 28)
