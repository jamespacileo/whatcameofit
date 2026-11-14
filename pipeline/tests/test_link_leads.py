"""Link leads: reading a platform's file and storing one lead per article address.
Scenario names are from openspec link-leads. Every post here is synthetic."""

import io
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as parquet
import pytest
import zstandard
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backfill_support import NOW, same_session
from thenwhat.backfill.link_load import LoadReport, load_links
from thenwhat.backfill.link_readers import (
    HACKER_NEWS,
    REDDIT,
    NoCommunities,
    SharedLink,
    Skip,
    UnknownPlatform,
    posts_of,
    read_hacker_news,
    reddit_reader,
)
from thenwhat.db.models import LinkLead, LinkShare
from thenwhat.domain import OutletKind
from thenwhat.export.build import build_export

WHEN = datetime(2019, 5, 4, 10, 30, tzinfo=UTC)
ARTICLE = "https://www.theguardian.com/science/2019/may/04/synthetic-trial-report"
AUTHOR = "synthetic_author_name"
POST_ID = "t3syntheticid"
PERMALINK = "/r/science/comments/syntheticid/a_synthetic_post/"
POST_TEXT = "synthetic words a person wrote under a post"


def story(**changes) -> dict:
    row = {
        "id": 20000001,
        "type": 1,
        "url": ARTICLE,
        "title": "A synthetic headline about a trial",
        "time": WHEN,
        "score": 120,
        "dead": 0,
        "deleted": 0,
    }
    return {**row, **changes}


def submission(**changes) -> dict:
    row = {
        "url": ARTICLE,
        "subreddit": "science",
        "created_utc": int(WHEN.timestamp()),
        "score": 4100,
        "title": "A synthetic headline about a trial",
        "is_self": False,
        "removed_by_category": None,
    }
    return {**row, **changes}


def leads(session: Session) -> list[LinkLead]:
    return list(session.scalars(select(LinkLead).order_by(LinkLead.id)))


def shares(session: Session) -> list[LinkShare]:
    return list(session.scalars(select(LinkShare).order_by(LinkShare.id)))


def load(session: Session, platform: str, posts) -> LoadReport:
    return load_links(same_session(session), platform, posts, steps=[])


# --- readers -----------------------------------------------------------------------


def test_a_story_that_links_to_an_address_is_a_shared_link():
    link = read_hacker_news(story())

    assert link == SharedLink(
        url=ARTICLE,
        community=HACKER_NEWS,
        shared_at=WHEN,
        score=120,
        title="A synthetic headline about a trial",
        item_number=20000001,
    )


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"url": ""}, Skip.NO_LINK),
        ({"url": None}, Skip.NO_LINK),
        ({"dead": 1}, Skip.REMOVED),
        ({"deleted": 1}, Skip.REMOVED),
        ({"url": "https://news.ycombinator.com/item?id=1"}, Skip.OWN_PLATFORM),
        ({"title": "  "}, Skip.NO_TITLE),
    ],
)
def test_a_hacker_news_story_that_does_not_count_is_skipped_with_its_reason(changes, reason):
    """Scenarios: A text post, A removed post"""
    assert read_hacker_news(story(**changes)) is reason


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"is_self": True, "url": "https://www.reddit.com/r/science/comments/x/"}, Skip.NO_LINK),
        ({"removed_by_category": "moderator"}, Skip.REMOVED),
        ({"url": "https://i.redd.it/synthetic.png"}, Skip.OWN_PLATFORM),
        ({"url": "https://old.reddit.com/r/science/"}, Skip.OWN_PLATFORM),
        ({"subreddit": "aww"}, Skip.OTHER_COMMUNITY),
        ({"title": ""}, Skip.NO_TITLE),
    ],
)
def test_a_reddit_submission_that_does_not_count_is_skipped_with_its_reason(changes, reason):
    """Scenarios: A text post, A removed post, A post from another community"""
    read = reddit_reader(frozenset({"science"}))

    assert read(submission(**changes)) is reason


def test_a_community_is_matched_whatever_its_letter_case():
    read = reddit_reader(frozenset({"Science"}))

    link = read(submission(subreddit="science"))

    assert isinstance(link, SharedLink) and link.community == "science"
    assert link.item_number is None


# --- storing -----------------------------------------------------------------------


def test_one_article_shared_in_two_places_is_one_lead_with_two_shares(session: Session):
    """Scenarios: One article shared in two places, A tracking parameter"""
    load(session, HACKER_NEWS, [read_hacker_news(story())])
    read = reddit_reader(frozenset({"science"}))
    report = load(session, REDDIT, [read(submission(url=ARTICLE + "?utm_source=share"))])

    [lead] = leads(session)
    assert lead.url_key == "theguardian.com/science/2019/may/04/synthetic-trial-report"
    assert (lead.outlet, lead.outlet_kind) == ("theguardian.com", OutletKind.GENERAL_NEWS)
    assert [(share.platform, share.community) for share in shares(session)] == [
        (HACKER_NEWS, HACKER_NEWS),
        (REDDIT, "science"),
    ]
    assert (report.new_leads, report.added_shares) == (0, 1)


def test_the_same_posts_loaded_twice_add_nothing(session: Session):
    """Scenarios: The same file loaded twice, Stopped part way"""
    posts = [
        read_hacker_news(story(id=number, url=f"https://example.org/{number}"))
        for number in range(5)
    ]

    first = load(session, HACKER_NEWS, posts)
    second = load(session, HACKER_NEWS, posts)

    assert (first.new_leads, second.new_leads, second.already_stored) == (5, 0, 5)
    assert (len(leads(session)), len(shares(session))) == (5, 5)


def test_a_lead_carries_the_title_and_time_of_its_earliest_share(session: Session):
    later = read_hacker_news(story(title="Shared later", time=datetime(2020, 1, 1, tzinfo=UTC)))
    earlier = read_hacker_news(
        story(id=7, title="Shared first", time=datetime(2018, 1, 1, tzinfo=UTC))
    )

    load(session, HACKER_NEWS, [later, earlier])

    [lead] = leads(session)
    assert (lead.title, lead.first_shared_at.year) == ("Shared first", 2018)
    assert len(shares(session)) == 2


def test_an_address_that_cannot_be_an_article_makes_no_lead(session: Session):
    """Scenario: An address that cannot be an article"""
    report = load(session, HACKER_NEWS, [read_hacker_news(story(url="ftp://example.org/file"))])

    assert leads(session) == []
    assert report.skipped[Skip.UNUSABLE] == 1


# --- files -------------------------------------------------------------------------


def hacker_news_file(folder: Path, rows: list[dict]) -> Path:
    """A parquet file shaped like the archive's, with the columns a lead never reads."""
    path = folder / "2019-05.parquet"
    full = [{**row, "by": AUTHOR, "text": POST_TEXT} for row in rows]
    parquet.write_table(pa.Table.from_pylist(full), path)
    return path


def reddit_file(folder: Path, rows: list[dict]) -> Path:
    """A zstandard file shaped like a community's submissions, with what a lead never keeps."""
    path = folder / "science_submissions.zst"
    lines = [
        json.dumps(
            {**row, "author": AUTHOR, "id": POST_ID, "permalink": PERMALINK, "selftext": POST_TEXT}
        )
        for row in rows
    ]
    path.write_bytes(zstandard.ZstdCompressor().compress("\n".join(lines).encode()))
    return path


def test_a_hacker_news_file_gives_its_stories_and_not_its_comments(tmp_path: Path):
    path = hacker_news_file(tmp_path, [story(), story(id=2, type=2, url=None, title=None)])

    posts = list(posts_of(HACKER_NEWS, path, communities=frozenset()))

    assert len(posts) == 1 and isinstance(posts[0], SharedLink)


def everything_stored(session: Session) -> str:
    """Every value in the link lead tables, as one text to search."""
    found = io.StringIO()
    for table in ("link_lead", "link_share", "link_lead_link", "link_lead_label"):
        for row in session.execute(text(f"SELECT * FROM {table}")):  # noqa: S608
            found.write(repr(tuple(row)))
    return found.getvalue()


def test_nothing_about_the_person_who_shared_is_stored_or_logged(
    session: Session, tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    """Scenario: A Reddit submission"""
    caplog.set_level(logging.DEBUG)
    reddit = reddit_file(tmp_path, [submission()])
    hacker_news = hacker_news_file(tmp_path, [story(url="https://example.org/other")])

    load(session, REDDIT, posts_of(REDDIT, reddit, communities=frozenset({"science"})))
    load(session, HACKER_NEWS, posts_of(HACKER_NEWS, hacker_news, communities=frozenset()))

    stored = everything_stored(session)
    assert "synthetic-trial-report" in stored  # the article's address is what is kept
    for private in (AUTHOR, POST_ID, PERMALINK, "syntheticid", POST_TEXT):
        assert private not in stored
        assert private not in caplog.text
    [reddit_share] = [share for share in shares(session) if share.platform == REDDIT]
    assert reddit_share.item_number is None


def test_a_reddit_load_refuses_while_no_community_is_chosen(tmp_path: Path):
    """Scenario: No community configured"""
    path = reddit_file(tmp_path, [submission()])

    with pytest.raises(NoCommunities, match="LINK_LEAD_SUBREDDITS"):
        posts_of(REDDIT, path, communities=frozenset())


def test_a_platform_with_no_reader_is_refused(tmp_path: Path):
    """Scenario: A platform with no reader"""
    with pytest.raises(UnknownPlatform, match="hackernews, reddit"):
        posts_of("bluesky", tmp_path / "posts.jsonl", communities=frozenset())


def test_the_export_is_the_same_before_and_after_a_load(session: Session):
    """Scenario: Export after a load"""
    before = build_export(session, now=NOW).model_dump_json()

    load(session, HACKER_NEWS, [read_hacker_news(story())])

    assert len(leads(session)) == 1
    assert build_export(session, now=NOW).model_dump_json() == before
