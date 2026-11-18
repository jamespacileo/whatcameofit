"""Reading bulk files of posts or article listings into link leads.
Behavior: openspec link-leads.

A reader takes from a post only what a link lead keeps: the address it links to, the
community, the time, the score and the title. Who posted it, the post's text and its
comments are never taken, and for Reddit neither is the post's id or address.
"""

import io
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from thenwhat.work.errors import BackfillError

HACKER_NEWS = "hackernews"
REDDIT = "reddit"
GDELT_GAL = "gdelt-gal"

# The only columns asked of a Hacker News file, so the author's name and the item's
# text are never read from disk.
HACKER_NEWS_COLUMNS = ["id", "type", "url", "title", "time", "score", "dead", "deleted"]
HACKER_NEWS_STORY = 1
# The only fields taken from a Reddit submission's line.
REDDIT_FIELDS = (
    "url",
    "subreddit",
    "created_utc",
    "score",
    "title",
    "is_self",
    "removed_by_category",
)
# Reddit's dumps are compressed with a window this large; the default refuses them.
ZSTD_WINDOW = 2**31

OWN_HOSTS = {
    HACKER_NEWS: ("news.ycombinator.com",),
    REDDIT: ("reddit.com", "redd.it", "redditmedia.com", "redditstatic.com"),
}


class Skip(StrEnum):
    """Why a post made no link lead, in the words the load reports."""

    NO_LINK = "no link"
    REMOVED = "removed or deleted"
    OWN_PLATFORM = "links to the platform itself"
    NO_TITLE = "no title"
    UNUSABLE = "unusable address"
    OTHER_COMMUNITY = "not a chosen community"
    INVALID_LISTING = "invalid article listing"


@dataclass(frozen=True, slots=True)
class SharedLink:
    """One post that links to an address, reduced to what a link lead keeps."""

    url: str
    community: str
    shared_at: datetime
    score: int
    title: str
    # The Hacker News item number; never set for Reddit.
    item_number: int | None = None


class UnknownPlatform(BackfillError):
    """No reader exists for the platform named."""


class NoCommunities(BackfillError):
    """A platform divided into communities was loaded with none chosen."""


def _tidy(text: object) -> str:
    return " ".join(str(text or "").split())


def _on_own_platform(platform: str, url: str) -> bool:
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return False
    return any(host == own or host.endswith("." + own) for own in OWN_HOSTS.get(platform, ()))


def _moment(value: object) -> datetime:
    """A post's time as the file gives it: a timestamp, or seconds since 1970."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromtimestamp(int(float(str(value))), tz=UTC)


def _link(platform: str, url: object, title: object) -> tuple[str, str] | Skip:
    """The address and title of a post that links somewhere, or why it does not count."""
    address = str(url or "").strip()
    if not address:
        return Skip.NO_LINK
    if _on_own_platform(platform, address):
        return Skip.OWN_PLATFORM
    headline = _tidy(title)
    if not headline:
        return Skip.NO_TITLE
    return address, headline


def read_hacker_news(row: dict[str, Any]) -> SharedLink | Skip:
    """One Hacker News story as a shared link."""
    if row.get("dead") or row.get("deleted"):
        return Skip.REMOVED
    link = _link(HACKER_NEWS, row.get("url"), row.get("title"))
    if isinstance(link, Skip):
        return link
    address, title = link
    return SharedLink(
        url=address,
        community=HACKER_NEWS,
        shared_at=_moment(row["time"]),
        score=int(row.get("score") or 0),
        title=title,
        item_number=int(row["id"]),
    )


def reddit_reader(communities: frozenset[str]) -> Callable[[dict[str, Any]], SharedLink | Skip]:
    """A reader of Reddit submissions that takes only the chosen communities."""
    chosen = frozenset(name.lower() for name in communities)

    def read(row: dict[str, Any]) -> SharedLink | Skip:
        community = str(row.get("subreddit") or "")
        if community.lower() not in chosen:
            return Skip.OTHER_COMMUNITY
        if row.get("removed_by_category"):
            return Skip.REMOVED
        if row.get("is_self"):
            return Skip.NO_LINK
        link = _link(REDDIT, row.get("url"), row.get("title"))
        if isinstance(link, Skip):
            return link
        address, title = link
        return SharedLink(
            url=address,
            community=community,
            shared_at=_moment(row["created_utc"]),
            score=int(row.get("score") or 0),
            title=title,
        )

    return read


def hacker_news_rows(path: Path) -> Iterator[dict[str, Any]]:
    """The stories of one monthly parquet file, with the eight columns a lead needs."""
    # Imported here: the parquet library is slow to load and only this command needs it.
    import pyarrow.parquet as parquet

    file = parquet.ParquetFile(path)
    for batch in file.iter_batches(batch_size=5000, columns=HACKER_NEWS_COLUMNS):
        for row in batch.to_pylist():
            if row.get("type") == HACKER_NEWS_STORY:
                yield row


def reddit_lines(path: Path) -> Iterator[tuple[int, str]]:
    """The non-empty lines of one zstandard-compressed file, each with its line number
    counted from 1."""
    import zstandard

    with path.open("rb") as compressed:
        reader = zstandard.ZstdDecompressor(max_window_size=ZSTD_WINDOW).stream_reader(compressed)
        text = io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
        for number, line in enumerate(text, start=1):
            if line.strip():
                yield number, line


def reddit_submission(line: str) -> dict[str, Any]:
    """One line of a Reddit file reduced at once to the fields a lead needs; nothing else
    of it is kept. Raises when the line is not a JSON object."""
    submission = json.loads(line)
    if not isinstance(submission, dict):
        raise TypeError("not an object")
    return {field: submission.get(field) for field in REDDIT_FIELDS}


def reddit_rows(path: Path) -> Iterator[dict[str, Any]]:
    """The submissions of one zstandard-compressed file, one JSON object a line. Each
    line is reduced at once to the fields a lead needs; nothing else of it is kept."""
    for _number, line in reddit_lines(path):
        yield reddit_submission(line)


def gdelt_links(path: Path) -> Iterator[SharedLink | Skip]:
    """Read the staged GDELT GAL metadata file, using its UTC day as the lead date."""
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                yield Skip.INVALID_LISTING
                continue
            if not isinstance(row, dict) or row.get("source") != GDELT_GAL:
                yield Skip.INVALID_LISTING
                continue
            published = row.get("date")
            if not isinstance(published, str):
                yield Skip.INVALID_LISTING
                continue
            try:
                day = date.fromisoformat(published)
            except ValueError:
                yield Skip.INVALID_LISTING
                continue
            address = row.get("url")
            headline = row.get("title")
            if not (isinstance(address, str) and isinstance(headline, str)):
                yield Skip.INVALID_LISTING
                continue
            link = _link(GDELT_GAL, address, headline)
            if isinstance(link, Skip):
                yield link
                continue
            url, title = link
            yield SharedLink(
                url=url,
                community=GDELT_GAL,
                shared_at=datetime.combine(day, time.min, tzinfo=UTC),
                score=0,
                title=title,
            )


def posts_of(
    platform: str, path: Path, *, communities: frozenset[str]
) -> Iterator[SharedLink | Skip]:
    """Every post of a platform's file as a shared link or the reason it is skipped.
    Refuses before reading anything when the platform has no reader or, for a platform
    divided into communities, when none is chosen."""
    if platform == HACKER_NEWS:
        return (read_hacker_news(row) for row in hacker_news_rows(path))
    if platform == GDELT_GAL:
        return gdelt_links(path)
    if platform == REDDIT:
        if not communities:
            raise NoCommunities(
                "No Reddit community is chosen. Name the communities to load in "
                "LINK_LEAD_SUBREDDITS, separated by commas."
            )
        read = reddit_reader(communities)
        return (read(row) for row in reddit_rows(path))
    raise UnknownPlatform(
        f"No reader exists for the platform '{platform}'. "
        f"Platforms: {HACKER_NEWS}, {REDDIT}, {GDELT_GAL}."
    )
