"""CSV import, tested through `import_csv` on a real database.

Row numbers count the header as row 1, as a spreadsheet shows them.
"""

import csv
import io
from datetime import date

import pytest
from sqlalchemy.orm import Session

from thenwhat.claims.csv_import import CsvErrors, ImportResult, import_csv
from thenwhat.claims.entry import add_claim, articles_of, claim_count, find_claim, promises_of

COLUMNS = [
    "slug",
    "headline",
    "vertical",
    "intervention",
    "indication",
    "summary",
    "article_url",
    "outlet",
    "article_title",
    "published_date",
    "promise",
    "promise_date",
]


def row(number: int, **overrides: str) -> dict[str, str]:
    """A valid row for its own claim; `number` keeps slugs, names and URLs distinct."""
    values = {
        "slug": f"claim-{number}",
        "headline": f"Headline {number}",
        "vertical": "dental-regeneration",
        "intervention": f"Intervention {number}",
        "indication": "tooth loss",
        "summary": "",
        "article_url": f"https://news.example.org/{number}",
        "outlet": "Example News",
        "article_title": f"Article {number}",
        "published_date": "2018-03-10",
        "promise": "",
        "promise_date": "",
    }
    return values | overrides


def csv_lines(rows: list[dict[str, str]], columns: list[str] = COLUMNS) -> io.StringIO:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    buffer.seek(0)
    return buffer


def refused(session: Session, rows: list[dict[str, str]], columns: list[str] = COLUMNS):
    with pytest.raises(CsvErrors) as raised:
        import_csv(session, csv_lines(rows, columns))
    assert claim_count(session) == 0, "a refused file must import nothing"
    return raised.value.errors


def test_valid_csv_creates_every_claim_and_article(session: Session):
    """Scenario: Valid CSV"""
    rows = [
        row(1, promise="human trials by 2025"),
        row(1, article_url="https://news.example.org/1-update", published_date="2021-04-02"),
        row(2),
    ]

    result = import_csv(session, csv_lines(rows))

    assert result == ImportResult(claims=2, articles=3, promises=1)
    first = find_claim(session, "claim-1")
    assert first is not None and find_claim(session, "claim-2") is not None
    assert [a.url for a in articles_of(session, first)] == [
        "https://news.example.org/1",
        "https://news.example.org/1-update",
    ]
    assert [p.parsed_date for p in promises_of(session, first)] == [date(2025, 12, 31)]
    assert first.first_reported_date == date(2018, 3, 10)


def test_csv_with_an_invalid_row_imports_nothing_and_names_the_row(session: Session):
    """Scenario: CSV with an invalid row"""
    rows = [row(n) for n in range(1, 6)] + [row(6, article_url="")]  # header is row 1

    [error] = refused(session, rows)

    assert error.row == 7
    assert "article_url" in error.message


def test_every_field_problem_is_reported_in_one_pass(session: Session):
    rows = [row(1, outlet=""), row(2), row(3, published_date="10/03/2018")]

    errors = refused(session, rows)

    assert [(e.row, "outlet" in e.message, "published_date" in e.message) for e in errors] == [
        (2, True, False),
        (4, False, True),
    ]


def test_later_rows_of_a_claim_may_leave_its_claim_columns_blank(session: Session):
    rows = [
        row(1),
        row(
            1,
            headline="",
            vertical="",
            intervention="",
            indication="",
            article_url="https://news.example.org/1-update",
        ),
    ]

    assert import_csv(session, csv_lines(rows)) == ImportResult(claims=1, articles=2, promises=0)


def test_rows_that_disagree_about_one_claim_are_refused(session: Session):
    rows = [row(1), row(1, headline="A different headline", article_url="https://x.example/2")]

    [error] = refused(session, rows)

    assert error.row == 3
    assert "headline" in error.message


def test_entry_rule_broken_by_a_later_row_rolls_back_the_earlier_rows(session: Session):
    rows = [row(1), row(2, vertical="hair-regrowth-typo")]

    [error] = refused(session, rows)

    assert error.row == 3
    assert "vertical" in error.message


def test_slug_that_already_exists_is_refused(session: Session):
    add_claim(
        session,
        slug="claim-1",
        headline="Existing",
        vertical="dental-regeneration",
        intervention="Something else",
        indication="enamel loss",
    )

    with pytest.raises(CsvErrors) as raised:
        import_csv(session, csv_lines([row(2), row(1)]))

    assert [error.row for error in raised.value.errors] == [3]
    assert claim_count(session) == 1


def test_missing_column_is_reported_against_the_header_row(session: Session):
    columns = [column for column in COLUMNS if column != "outlet"]

    [error] = refused(session, [row(1)], columns)

    assert error.row == 1
    assert "outlet" in error.message


def test_operator_supplied_promise_date_is_used(session: Session):
    import_csv(session, csv_lines([row(1, promise="soon", promise_date="2026-06-30")]))

    claim = find_claim(session, "claim-1")
    assert claim is not None
    assert [p.parsed_date for p in promises_of(session, claim)] == [date(2026, 6, 30)]


def test_blank_lines_are_skipped(session: Session):
    blank = dict.fromkeys(COLUMNS, "")

    result = import_csv(session, csv_lines([row(1), blank, row(2)]))

    assert result.claims == 2
