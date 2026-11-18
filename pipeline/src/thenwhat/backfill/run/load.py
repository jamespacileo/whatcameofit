"""The load stage of a run: reads each bulk file through the platform's reader, keys each
address, and keeps a share only when its outlet is listed. Every other link is counted
by domain in the tally and goes no further. Behavior: openspec link-leads (change
file-based-backfill).

What the stage writes:

- `links.parquet`: one row a share on a listed outlet.
- `tally.csv`: unlisted domain, platform, link posts, posts whose title names a topic
  word. No title, no address beyond the domain.
- `quarantine.csv`: file, position and kind of error of a row that could not be read.
  Nothing of the row.

Each file is written under a temporary name and renamed, so a load that is stopped
leaves none of them and is simply run again. A dry run writes the tally alone.
"""

import csv
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from thenwhat.backfill.address import article_key
from thenwhat.backfill.link_load import outlet_of_key
from thenwhat.backfill.link_readers import (
    HACKER_NEWS,
    HACKER_NEWS_COLUMNS,
    HACKER_NEWS_STORY,
    REDDIT,
    SharedLink,
    Skip,
    read_hacker_news,
    reddit_lines,
    reddit_reader,
    reddit_submission,
)
from thenwhat.backfill.outlet_kinds import kind_of
from thenwhat.backfill.run.folder import RunRecord, RunRefused, check_inputs, write_atomically
from thenwhat.backfill.topics import names_one, terms_of
from thenwhat.domain import OutletKind

LINKS = "links.parquet"
TALLY = "tally.csv"
QUARANTINE = "quarantine.csv"

# Why a post read from a file made no share, beyond the reader's own reasons.
NOT_LISTED = "outlet not listed"
ALREADY_IN_RUN = "share already in the run"

# The fields a Reddit line must carry for the reader to make a share of it.
REDDIT_REQUIRED = ("url", "subreddit", "created_utc", "title")
# How many lines are looked at for one that shows a Reddit file's fields.
REDDIT_LINES_CHECKED = 100

LINK_SCHEMA = {
    "address": pl.String,
    "address_key": pl.String,
    "outlet": pl.String,
    "kind": pl.String,
    "title": pl.String,
    "platform": pl.String,
    "community": pl.String,
    "shared_at": pl.Datetime("us", "UTC"),
    "score": pl.Int64,
    "item_number": pl.Int64,
}

Row = dict[str, Any]


class FieldsMissing(RunRefused):
    """A bulk file lacks fields its reader takes."""


class OverBudget(RunRefused):
    """More of a file's rows failed to read than LOAD_ERROR_BUDGET allows."""


class CountsDisagree(RunRefused):
    """The posts read do not equal the shares written plus the posts left out."""


@dataclass(slots=True)
class LoadReport:
    read: int = 0
    shares: int = 0
    addresses: int = 0
    quarantined: int = 0
    skipped: Counter[str] = field(default_factory=Counter)

    def as_json(self) -> dict[str, Any]:
        return {**asdict(self), "skipped": dict(sorted(self.skipped.items()))}


@dataclass(frozen=True, slots=True)
class Quarantined:
    file: str
    position: int
    error: str


def check_fields(platform: str, path: Path) -> None:
    """Refuse a file that lacks a field its reader takes, naming the fields."""
    if platform == HACKER_NEWS:
        import pyarrow.parquet as parquet

        names = set(parquet.read_schema(path).names)
        missing = [name for name in HACKER_NEWS_COLUMNS if name not in names]
    else:
        missing = list(REDDIT_REQUIRED)
        for count, (_number, line) in enumerate(reddit_lines(path), start=1):
            try:
                row = reddit_submission(line)
            except (ValueError, TypeError):
                row = None
            if row is not None:
                missing = [name for name in REDDIT_REQUIRED if row.get(name) is None]
                break
            if count >= REDDIT_LINES_CHECKED:
                break
    if missing:
        raise FieldsMissing(
            f"{path.name} has no {', '.join(missing)}, which the {platform} reader takes. "
            "Nothing was written."
        )


def positioned_rows(platform: str, path: Path) -> Iterator[tuple[int, Row | Exception]]:
    """Each post of a file with its position (row or line, from 1), or the error that
    kept it from being read. For Reddit, each line is reduced to the reader's fields at
    once."""
    if platform == HACKER_NEWS:
        import pyarrow.parquet as parquet

        position = 0
        file = parquet.ParquetFile(path)
        for batch in file.iter_batches(batch_size=5000, columns=HACKER_NEWS_COLUMNS):
            for row in batch.to_pylist():
                position += 1
                if row.get("type") == HACKER_NEWS_STORY:
                    yield position, row
        return
    for number, line in reddit_lines(path):
        try:
            yield number, reddit_submission(line)
        except (ValueError, TypeError) as error:
            yield number, error


def reader_for(record: RunRecord) -> Callable[[Row], SharedLink | Skip]:
    if record.platform == REDDIT:
        return reddit_reader(frozenset(record.communities))
    return read_hacker_news


def load(
    folder: Path,
    record: RunRecord,
    *,
    error_budget: float | None,
    dry_run: bool = False,
) -> LoadReport:
    """Load the run's input files into its folder, and return the report. Refused before
    anything is read while LOAD_ERROR_BUDGET is empty, an input changed since the run
    started, or a file lacks its reader's fields."""
    if error_budget is None:
        raise RunRefused(
            "LOAD_ERROR_BUDGET is not set. Give the share of a file's rows that may fail "
            "to read, for example 0.001."
        )
    check_inputs(record)
    paths = [Path(item.path) for item in record.inputs]
    for path in paths:
        check_fields(record.platform, path)

    read = reader_for(record)
    terms = terms_of()
    report = LoadReport()
    columns: dict[str, list[Any]] = {name: [] for name in LINK_SCHEMA}
    seen: set[tuple[str, str, datetime]] = set()
    keys: set[str] = set()
    tally_posts: Counter[str] = Counter()
    tally_topic: Counter[str] = Counter()
    quarantine: list[Quarantined] = []
    try:
        for path in paths:
            file_read = file_failed = 0
            for position, row in positioned_rows(record.platform, path):
                report.read += 1
                file_read += 1
                if isinstance(row, Exception):
                    post: SharedLink | Skip | Exception = row
                else:
                    try:
                        post = read(row)
                    except (KeyError, ValueError, TypeError, OverflowError) as error:
                        post = error
                if isinstance(post, Exception):
                    quarantine.append(Quarantined(path.name, position, type(post).__name__))
                    report.quarantined += 1
                    file_failed += 1
                    continue
                if isinstance(post, Skip):
                    report.skipped[post.value] += 1
                    continue
                key = article_key(post.url)
                if key is None:
                    report.skipped[Skip.UNUSABLE.value] += 1
                    continue
                outlet = outlet_of_key(key)
                kind = kind_of(outlet)
                if kind == OutletKind.UNKNOWN:
                    report.skipped[NOT_LISTED] += 1
                    tally_posts[outlet] += 1
                    tally_topic[outlet] += names_one(post.title, terms)
                    continue
                place = (key, post.community, post.shared_at)
                if place in seen:
                    report.skipped[ALREADY_IN_RUN] += 1
                    continue
                seen.add(place)
                keys.add(key)
                for name, value in (
                    ("address", post.url),
                    ("address_key", key),
                    ("outlet", outlet),
                    ("kind", kind.value),
                    ("title", post.title),
                    ("platform", record.platform),
                    ("community", post.community),
                    ("shared_at", post.shared_at),
                    ("score", post.score),
                    ("item_number", post.item_number),
                ):
                    columns[name].append(value)
            if file_failed > error_budget * file_read:
                raise OverBudget(
                    f"{file_failed:,} of {file_read:,} rows of {path.name} could not be read, "
                    f"more than LOAD_ERROR_BUDGET ({error_budget:g}) allows. The load stopped; "
                    f"the rows are listed in {QUARANTINE}."
                )
    finally:
        # The quarantine holds no content, so it is written even when the load stops,
        # to show what failed.
        if quarantine and not dry_run:
            write_quarantine(folder / QUARANTINE, quarantine)

    report.shares = len(columns["address"])
    report.addresses = len(keys)
    reconcile(report)
    write_tally(folder / TALLY, record.platform, tally_posts, tally_topic)
    if not dry_run:
        frame = pl.DataFrame(columns, schema=LINK_SCHEMA)
        write_atomically(folder / LINKS, lambda partial: frame.write_parquet(partial))
    return report


def reconcile(report: LoadReport) -> None:
    left_out = sum(report.skipped.values())
    if report.read != report.shares + left_out + report.quarantined:
        raise CountsDisagree(
            f"The load's counts do not add up: {report.read:,} posts read, "
            f"{report.shares:,} shares written, {left_out:,} left out and "
            f"{report.quarantined:,} quarantined."
        )


def write_tally(path: Path, platform: str, posts: Counter[str], topic: Counter[str]) -> None:
    def write(partial: Path) -> None:
        with partial.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["domain", "platform", "link_posts", "topic_posts"])
            for domain, count in sorted(posts.items(), key=lambda item: (-item[1], item[0])):
                writer.writerow([domain, platform, count, topic[domain]])

    write_atomically(path, write)


def write_quarantine(path: Path, rows: list[Quarantined]) -> None:
    def write(partial: Path) -> None:
        with partial.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["file", "position", "error"])
            for row in rows:
                writer.writerow([row.file, row.position, row.error])

    write_atomically(path, write)


def read_tally(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))
