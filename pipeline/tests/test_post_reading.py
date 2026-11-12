"""Reading a social media post by its address, tested through `post_at` and `read_post`
(both pure: the network is passed in) and through the lookup command.

Every post and platform answer here is made up, shaped as each platform answered on
2026-11-12. Scenario names are from openspec live-lookup.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from thenwhat.cli import app
from thenwhat.decide.core import BackendAnswer
from thenwhat.extract.post import Post, post_at, read_post
from thenwhat.extract.retrieve import ArticleRetriever
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.sources.base import SourceRecord

NOW = datetime(2026, 11, 20, tzinfo=UTC)
ARTICLE = "https://news.example.org/health/ex1-regrows-teeth"
BLUESKY_POST = "https://bsky.app/profile/someone.example/post/3kabc123xyz"
BLUESKY_API = (
    "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread"
    "?uri=at%3A%2F%2Fsomeone.example%2Fapp.bsky.feed.post%2F3kabc123xyz&depth=0&parentHeight=0"
)
BLUESKY_ANSWER = {
    "thread": {
        "post": {
            "author": {"handle": "someone.example", "displayName": "Someone Real"},
            "record": {
                "text": "Huge if true: a drug that regrows teeth news.example.org/health/ex1…",
                "facets": [{"features": [{"uri": ARTICLE}]}],
            },
            "embed": {
                "external": {
                    "uri": ARTICLE,
                    "title": "Antibody regrows teeth",
                    "description": "A drug called EX-1 restored missing teeth.",
                }
            },
        }
    }
}
TOOT = "https://scicomm.example/@lab/117593221666993044"
TOOT_API = "https://scicomm.example/api/v1/statuses/117593221666993044"


def reading(answers: dict[str, Any], *, forbidden: tuple[str, ...] = ()):
    asked: list[str] = []

    def get_json(address: str) -> Any:
        asked.append(address)
        return answers.get(address)

    def read(address: str) -> Post | None:
        ref = post_at(address)
        assert ref is not None, address
        return read_post(ref, get_json=get_json, allowed=lambda url: url not in forbidden)

    return read, asked


def test_only_a_post_on_a_platform_that_can_be_read_is_a_post():
    hows = [ref.how for ref in map(post_at, (BLUESKY_POST, TOOT)) if ref is not None]
    assert hows == ["bluesky", "mastodon"]
    story = post_at("https://news.ycombinator.com/item?id=50028027")
    assert story is not None and (story.platform, story.id) == ("Hacker News", "50028027")
    for other in (
        "https://x.com/someone/status/1234567890",
        "https://bsky.app/profile/someone.example",
        "https://news.ycombinator.com/newest",
        "https://medium.com/@someone/a-story-123abc",
        ARTICLE,
    ):
        assert post_at(other) is None, other


def test_a_bluesky_post_gives_its_text_its_card_and_its_links_but_not_its_author():
    """Scenario: Post on Bluesky"""
    read, asked = reading({BLUESKY_API: BLUESKY_ANSWER})

    post = read(BLUESKY_POST)

    assert post == Post(
        "Huge if true: a drug that regrows teeth news.example.org/health/ex1…\n"
        "The page it links to: Antibody regrows teeth. A drug called EX-1 restored missing teeth.",
        (ARTICLE,),
    )
    assert asked == [BLUESKY_API]
    assert "Someone" not in str(post) and "someone.example" not in str(post)


def test_a_hacker_news_story_or_comment_is_read_and_a_deleted_one_is_not():
    """Scenario: Story on Hacker News"""
    item = "https://hacker-news.firebaseio.com/v0/item"
    read, _ = reading(
        {
            f"{item}/1.json": {"type": "story", "title": "Antibody regrows teeth", "url": ARTICLE},
            f"{item}/2.json": {
                "type": "comment",
                "text": 'The paper is <a href="https://doi.org/10.1234/example.2026.0042">here</a>.'
                "<p>Registered as NCT01234567 &amp; ongoing.",
            },
            f"{item}/3.json": {"deleted": True},
        }
    )

    assert read("https://news.ycombinator.com/item?id=1") == Post(
        "Antibody regrows teeth", (ARTICLE,)
    )
    assert read("https://news.ycombinator.com/item?id=2") == Post(
        "The paper is here.\nRegistered as NCT01234567 & ongoing.",
        ("https://doi.org/10.1234/example.2026.0042",),
    )
    assert read("https://news.ycombinator.com/item?id=3") is None
    assert read("https://news.ycombinator.com/item?id=4") is None


def test_a_mastodon_post_is_read_only_when_public_and_when_its_server_allows():
    """Scenario: Post on a Mastodon server"""
    status = {
        "visibility": "public",
        "account": {"display_name": "A Lab"},
        "content": '<p>New trial of EX-1 <a href="https://scicomm.example/tags/teeth"'
        ' class="mention hashtag">#teeth</a>'
        f' <a href="{ARTICLE}"><span>news.example.org</span></a></p>',
        "card": {"url": ARTICLE, "title": "Antibody regrows teeth", "description": ""},
    }
    read, asked = reading({TOOT_API: status})

    assert read(TOOT) == Post(
        "New trial of EX-1 #teeth news.example.org\nThe page it links to: Antibody regrows teeth",
        (ARTICLE,),
    )

    private, _ = reading({TOOT_API: status | {"visibility": "private"}})
    assert private(TOOT) is None
    refused, refused_asked = reading({TOOT_API: status}, forbidden=(TOOT_API,))
    assert refused(TOOT) is None
    assert (asked, refused_asked) == ([TOOT_API], [])


# --- the lookup command ----------------------------------------------------------------

READING = {
    "about_a_treatment": True,
    "gist": "An antibody was reported to regrow missing teeth.",
    "intervention": "EX-1",
    "indication": "tooth agenesis",
}
ARTICLE_PAGE = (
    '<html><head><meta property="og:title" content="Antibody regrows teeth"></head><body><p>'
    + "EX-1 regrew teeth in people born without them. " * 15
    + "</p></body></html>"
)


class Trials:
    def search_trials(self, intervention: str, condition: str | None = None) -> list[SourceRecord]:
        payload = {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT00000001", "briefTitle": "EX-1 in people"}
            }
        }
        url = "https://clinicaltrials.gov/study/NCT00000001"
        return [SourceRecord("clinicaltrials.gov", "NCT00000001", url, payload, NOW)]

    def fetch_trial(self, nct_id: str) -> SourceRecord | None:
        return None

    def named_trials(self, name: str) -> list[SourceRecord]:
        return []


class Papers:
    def trial_numbers(self, *, doi: str | None = None, pubmed_id: str | None = None) -> list[str]:
        return []


class Backend:
    name = "fake"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        rest = 0.2 / (len(options) - 1)
        return BackendAnswer(options[0], {o: 0.8 if o == options[0] else rest for o in options})


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    shown: list[str] = []
    web: dict[str, httpx.Response] = {}

    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    def respond(messages, info) -> ModelResponse:
        shown.append(str(messages))
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, READING)])

    def serve(request: httpx.Request) -> httpx.Response:
        return web.get(str(request.url), httpx.Response(404))

    settings = LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15"))
    llm = Llm(session, settings, model=FunctionModel(respond, model_name="scripted"))
    retriever = ArticleRetriever(
        contact_email="ops@thenwhat.test", transport=httpx.MockTransport(serve)
    )
    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.lookup.make_tools", lambda s: (llm, Backend(), Trials()))
    monkeypatch.setattr("thenwhat.cli.lookup.make_papers", lambda s: Papers())
    monkeypatch.setattr("thenwhat.cli.extract.make_retriever", lambda: retriever)
    runner = CliRunner()

    def invoke(*arguments: str):
        return runner.invoke(app, list(arguments), env={"COLUMNS": "300"})

    return invoke, web, shown


def test_lookup_of_a_post_reads_the_post_and_the_article_it_links_to(run):
    """Scenario: Post that links to an article"""
    invoke, web, shown = run
    web[BLUESKY_API] = httpx.Response(200, json=BLUESKY_ANSWER)
    web[ARTICLE] = httpx.Response(200, text=ARTICLE_PAGE)

    result = invoke("lookup", BLUESKY_POST)

    assert result.exit_code == 0, result.output
    assert f"Read from a post on Bluesky and the article it links to: {ARTICLE}" in result.output
    assert "NCT00000001" in result.output
    # The model is shown the post first, then the article.
    assert "A post on Bluesky says:" in shown[0] and "The article it links to:" in shown[0]
    assert shown[0].index("Huge if true") < shown[0].index("Headline: Antibody regrows teeth")


def test_lookup_of_a_post_that_cannot_be_read_explains_and_exits_1(run):
    """Scenario: Post on a platform that cannot be read"""
    invoke, _, shown = run

    result = invoke("lookup", BLUESKY_POST)

    assert result.exit_code == 1
    assert "post on Bluesky could not be read" in result.output and "--paste" in result.output
    assert shown == []
