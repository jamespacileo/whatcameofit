"""All-or-nothing import of claims and source articles from CSV. Behavior: openspec claims.

One row per source article. Rows that share a slug belong to one claim: the first
of them defines the claim, and the others may leave the claim columns blank.
Row numbers in errors count the header as row 1.
"""

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from thenwhat.claims.entry import EntryError, add_article, add_claim, add_promise

CLAIM_COLUMNS = ("headline", "vertical", "intervention", "indication")
ARTICLE_COLUMNS = ("article_url", "outlet", "article_title", "published_date")
REQUIRED_COLUMNS = ("slug", *CLAIM_COLUMNS, *ARTICLE_COLUMNS)
OPTIONAL_COLUMNS = ("summary", "promise", "promise_date")


@dataclass(frozen=True, slots=True)
class RowError:
    row: int
    message: str


class CsvErrors(EntryError):
    """The file was refused and nothing was imported."""

    def __init__(self, errors: list[RowError]) -> None:
        self.errors = errors
        super().__init__("\n".join(f"row {error.row}: {error.message}" for error in errors))


@dataclass(frozen=True, slots=True)
class ImportResult:
    claims: int
    articles: int
    promises: int


@dataclass(frozen=True, slots=True)
class _Record:
    row: int
    values: dict[str, str]
    published_date: date
    promise_date: date | None


def import_csv(session: Session, lines: Iterable[str]) -> ImportResult:
    """Import every row, or none: any problem refuses the whole file."""
    records = _read(lines)

    claims: set[str] = set()
    articles = promises = 0
    with session.begin_nested():  # rolled back as a whole if any row is refused
        for record in records:
            values = record.values
            try:
                if values["slug"] not in claims:
                    add_claim(
                        session,
                        slug=values["slug"],
                        headline=values["headline"],
                        vertical=values["vertical"],
                        intervention=values["intervention"],
                        indication=values["indication"],
                        summary=values.get("summary", ""),
                    )
                    claims.add(values["slug"])
                add_article(
                    session,
                    values["slug"],
                    url=values["article_url"],
                    outlet=values["outlet"],
                    title=values["article_title"],
                    published_date=record.published_date,
                )
                articles += 1
                if values.get("promise"):
                    add_promise(
                        session,
                        values["slug"],
                        article_url=values["article_url"],
                        description=values["promise"],
                        parsed_date=record.promise_date,
                    )
                    promises += 1
            except EntryError as error:
                raise CsvErrors([RowError(record.row, str(error))]) from error
    return ImportResult(claims=len(claims), articles=articles, promises=promises)


def _read(lines: Iterable[str]) -> list[_Record]:
    """Parse and check every row before anything is written, so all field problems
    are reported together."""
    reader = csv.DictReader(lines)
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing_columns:
        raise CsvErrors([RowError(1, f"missing column(s): {', '.join(missing_columns)}")])

    errors: list[RowError] = []
    records: list[_Record] = []
    first_rows: dict[str, _Record] = {}
    for number, raw in enumerate(reader, start=2):
        values = {key: (value or "").strip() for key, value in raw.items() if key}
        if not any(values.values()):
            continue

        problems = [
            f"{column} is missing" for column in ("slug", *ARTICLE_COLUMNS) if not values[column]
        ]
        published_date = _date(values, "published_date", problems)
        promise_date = _date(values, "promise_date", problems)
        slug = values["slug"]
        first = first_rows.get(slug)
        if slug and first is None:
            problems += [f"{column} is missing" for column in CLAIM_COLUMNS if not values[column]]
        elif first is not None:
            problems += [
                f"{column} differs from row {first.row}, which has the same slug"
                for column in (*CLAIM_COLUMNS, "summary")
                if values.get(column) and values[column] != first.values.get(column, "")
            ]
            values = values | {column: first.values[column] for column in CLAIM_COLUMNS}

        errors += [RowError(number, problem) for problem in problems]
        if not problems and published_date is not None:
            record = _Record(number, values, published_date, promise_date)
            records.append(record)
            first_rows.setdefault(slug, record)
        elif slug and first is None:
            # Remember the row so later rows of the claim are compared, not re-checked.
            first_rows[slug] = _Record(number, values, date.min, None)

    if errors:
        raise CsvErrors(errors)
    return records


def _date(values: dict[str, str], column: str, problems: list[str]) -> date | None:
    text = values.get(column, "")
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        problems.append(f"{column} '{text}' is not a date; use YYYY-MM-DD")
        return None
