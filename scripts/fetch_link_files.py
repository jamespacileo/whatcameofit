"""Fetches the bulk files `thenwhat backfill load-links` reads, for a range of months.

    cd pipeline
    uv run python ../scripts/fetch_link_files.py hackernews 2025-01 2026-11
    uv run python ../scripts/fetch_link_files.py reddit 2025-01 2026-11 science longevity

Files land in data/link-files/, which is not committed. A file already there is kept,
so a stopped run is simply started again. Sources, terms and limits: docs/sources.md,
"Link datasets for the social-link backfill".

Only what a link lead keeps is written: for Hacker News the eight columns the reader
takes, for Reddit the seven fields. Hacker News authors and text are never requested.
Reddit's interface cannot be asked for two of the seven fields alone, so it answers
with whole submissions: each is reduced to the seven fields at once, and the author,
the text and the post's id (used only to tell one page from the next) reach no file.
"""

import io
import json
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import zstandard

ROOT = Path(__file__).resolve().parent.parent / "data" / "link-files"
CLIENT_NAME = "link-backfill/1.0"

ARCHIVE = "https://huggingface.co/datasets/open-index/hacker-news"
ARCHIVE_LISTING = "https://huggingface.co/api/datasets/open-index/hacker-news/tree/main/data"
CLICKHOUSE = "https://sql-clickhouse.clickhouse.com/?user=demo"
ARCTIC_SHIFT = "https://arctic-shift.photon-reddit.com/api/posts/search"

HACKER_NEWS_SCHEMA = pa.schema(
    [
        ("id", pa.uint32()),
        ("type", pa.int8()),
        ("url", pa.string()),
        ("title", pa.string()),
        ("time", pa.timestamp("us", tz="UTC")),
        ("score", pa.int32()),
        ("dead", pa.uint8()),
        ("deleted", pa.uint8()),
    ]
)
REDDIT_FIELDS = (
    "url",
    "subreddit",
    "created_utc",
    "score",
    "title",
    "is_self",
    "removed_by_category",
)
SECONDS_BETWEEN_REQUESTS = 1.0
CLICKHOUSE_PAGE = 10_000


def months(first: str, last: str) -> list[str]:
    year, month = (int(part) for part in first.split("-"))
    out = []
    while f"{year:04d}-{month:02d}" <= last:
        out.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return out


def next_month(month: str) -> str:
    year, number = (int(part) for part in month.split("-"))
    return f"{year + 1:04d}-01" if number == 12 else f"{year:04d}-{number + 1:02d}"


def say(text: str) -> None:
    print(f"{datetime.now(UTC):%H:%M:%S} {text}", flush=True)


def archive_months(client: httpx.Client) -> dict[str, int]:
    """The months the archive holds in full, with each file's size. The newest month
    listed is left out: the archive rewrites it daily and may have stopped part way."""
    sizes: dict[str, int] = {}
    for year in sorted({m[:4] for m in months("2006-10", f"{date.today():%Y-%m}")}):
        answer = client.get(f"{ARCHIVE_LISTING}/{year}")
        if answer.status_code == 404:
            continue
        answer.raise_for_status()
        for entry in answer.json():
            sizes[Path(entry["path"]).stem] = entry["size"]
    sizes.pop(max(sizes), None)
    return sizes


def hacker_news_from_archive(client: httpx.Client, month: str, size: int, target: Path) -> None:
    partial = target.with_suffix(".partial")
    with client.stream(
        "GET", f"{ARCHIVE}/resolve/main/data/{month[:4]}/{month}.parquet", follow_redirects=True
    ) as answer:
        answer.raise_for_status()
        with partial.open("wb") as out:
            for chunk in answer.iter_bytes(1 << 20):
                out.write(chunk)
    if partial.stat().st_size != size:
        raise SystemExit(f"{month}: got {partial.stat().st_size} bytes, the archive lists {size}")
    partial.rename(target)
    say(f"hackernews {month}: archive file, {size / 1e6:.0f} MB")


def hacker_news_from_clickhouse(client: httpx.Client, month: str, target: Path) -> None:
    """One month of stories that link somewhere, from the public copy the archive itself
    is built from. It refuses an answer of more than 10,000 rows and allows twenty
    queries of one shape an hour, so a month is asked for in pages by item number and
    a refusal for the hour's quota is waited out."""
    rows: list[dict] = []
    after = 0
    while True:
        query = (
            "SELECT id, toInt8(type) AS kind, url, title, toUnixTimestamp(time) AS at, score, "
            "dead, deleted FROM hackernews.hackernews "
            f"WHERE type = 'story' AND url != '' AND id > {after} "
            f"AND time >= '{month}-01 00:00:00' AND time < '{next_month(month)}-01 00:00:00' "
            f"ORDER BY id LIMIT {CLICKHOUSE_PAGE} FORMAT JSONEachRow"
        )
        answer = client.post(CLICKHOUSE, content=query)
        if "QUOTA_EXCEEDED" in answer.text[:400]:
            say("hackernews: the hour's quota at ClickHouse is used, waiting ten minutes")
            time.sleep(600)
            continue
        if answer.status_code != 200:
            raise SystemExit(
                f"hackernews {month}: status {answer.status_code}: {answer.text[:300]}"
            )
        page = [json.loads(line) for line in answer.text.splitlines() if line]
        for row in page:
            row["type"] = row.pop("kind")
            row["time"] = datetime.fromtimestamp(row.pop("at"), tz=UTC)
        rows.extend(page)
        if len(page) < CLICKHOUSE_PAGE:
            break
        after = page[-1]["id"]
        time.sleep(SECONDS_BETWEEN_REQUESTS)
    partial = target.with_suffix(".partial")
    pq.write_table(
        pa.Table.from_pylist(rows, schema=HACKER_NEWS_SCHEMA), partial, compression="zstd"
    )
    partial.rename(target)
    say(f"hackernews {month}: {len(rows)} stories with a link, from ClickHouse")


def fetch_hacker_news(first: str, last: str) -> None:
    folder = ROOT / "hackernews"
    folder.mkdir(parents=True, exist_ok=True)
    this_month = f"{date.today():%Y-%m}"
    with httpx.Client(headers={"User-Agent": CLIENT_NAME}, timeout=120) as client:
        listed = archive_months(client)
        for month in months(first, min(last, this_month)):
            target = folder / f"{month}.parquet"
            # The running month is fetched again each time: it is not complete yet.
            if target.exists() and month != this_month:
                continue
            if month in listed:
                hacker_news_from_archive(client, month, listed[month], target)
            else:
                hacker_news_from_clickhouse(client, month, target)
            time.sleep(SECONDS_BETWEEN_REQUESTS)


def reddit_page(client: httpx.Client, community: str, after: int, before: int) -> list[dict]:
    params = {
        "subreddit": community,
        "after": after,
        "before": before,
        "sort": "asc",
        "limit": "auto",
    }
    wait = 5.0
    for _ in range(12):
        answer = client.get(ARCTIC_SHIFT, params=params)
        if answer.status_code == 200:
            return answer.json()["data"] or []
        if answer.status_code == 429:
            wait = float(answer.headers.get("X-RateLimit-Reset", wait)) + 1
        elif answer.status_code not in (422, 500, 502, 503, 504):
            raise SystemExit(f"r/{community}: status {answer.status_code}: {answer.text[:200]}")
        say(f"r/{community}: status {answer.status_code}, waiting {wait:.0f}s")
        time.sleep(wait)
        wait = min(wait * 2, 300)
    raise SystemExit(f"r/{community}: no answer after 12 tries; run again to continue")


def fetch_reddit(first: str, last: str, communities: list[str]) -> None:
    folder = ROOT / "reddit"
    folder.mkdir(parents=True, exist_ok=True)
    start = int(datetime.fromisoformat(f"{first}-01").replace(tzinfo=UTC).timestamp())
    end = int(datetime.fromisoformat(f"{next_month(last)}-01").replace(tzinfo=UTC).timestamp())
    end = min(end, int(time.time()))
    with httpx.Client(headers={"User-Agent": CLIENT_NAME}, timeout=90) as client:
        for community in communities:
            target = folder / f"{community}_submissions.zst"
            if target.exists():
                continue
            partial = target.with_suffix(".partial")
            posts = links = 0
            seen: set[str] = set()
            after = start - 1
            with partial.open("wb") as raw:
                writer = zstandard.ZstdCompressor(level=10).stream_writer(raw)
                out = io.TextIOWrapper(writer, encoding="utf-8")
                while True:
                    page = reddit_page(client, community, after, end)
                    fresh = [post for post in page if post["id"] not in seen]
                    if not fresh:
                        break
                    for post in fresh:
                        seen.add(post["id"])
                        out.write(json.dumps({f: post.get(f) for f in REDDIT_FIELDS}) + "\n")
                        posts += 1
                        links += not post.get("is_self")
                    # Ask again from the last second seen, so posts sharing it are not
                    # missed; the ids already seen are dropped above.
                    after = int(page[-1]["created_utc"]) - 1
                    time.sleep(SECONDS_BETWEEN_REQUESTS)
                out.flush()
                writer.close()
            partial.rename(target)
            say(f"r/{community}: {posts} submissions, {links} of them links")


def main() -> None:
    if len(sys.argv) < 4 or sys.argv[1] not in ("hackernews", "reddit"):
        raise SystemExit(__doc__)
    platform, first, last, *communities = sys.argv[1:]
    if platform == "hackernews":
        fetch_hacker_news(first, last)
    elif not communities:
        raise SystemExit("Name the communities to fetch after the two months.")
    else:
        fetch_reddit(first, last, communities)


if __name__ == "__main__":
    main()
