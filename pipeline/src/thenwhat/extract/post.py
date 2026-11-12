"""Reading one social media post by its address: its text and the links in it.

Only on platforms that offer posts to software without signing in; terms and limits are in
docs/sources.md. The text and the links are returned to the caller and kept nowhere, and
who wrote the post is never read out. The same rules as the site's worker/post.mjs.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlsplit

BLUESKY = "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread"
HACKER_NEWS = "https://hacker-news.firebaseio.com/v0/item"
MAX_POST_CHARACTERS = 4000
BLUESKY_POST = re.compile(r"^/profile/([^/]+)/post/([a-z0-9]+)/?$", re.IGNORECASE)
# A post on any Mastodon server has this shape, whatever the server is called.
MASTODON_POST = re.compile(r"^/(?:@[^/]+|users/[^/]+/statuses)/(\d{6,})/?$")
LINE_ENDS = {"p", "br", "div", "li"}


@dataclass(frozen=True, slots=True)
class PostRef:
    """Which post an address is."""

    platform: str
    how: str
    host: str
    id: str
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class Post:
    text: str
    links: tuple[str, ...]


def post_at(url: str) -> PostRef | None:
    """The post at this address, on the platforms whose posts can be read; else None."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower().removeprefix("www.")
    if parts.scheme not in ("http", "https") or not host:
        return None
    if host == "bsky.app":
        post = BLUESKY_POST.match(parts.path)
        return PostRef("Bluesky", "bluesky", host, post[2], unquote(post[1])) if post else None
    if host == "news.ycombinator.com":
        ids = parse_qs(parts.query).get("id", []) if parts.path == "/item" else []
        return (
            PostRef("Hacker News", "hackernews", host, ids[0])
            if ids[:1] and ids[0].isdigit()
            else None
        )
    toot = MASTODON_POST.match(parts.path)
    return (
        PostRef("Mastodon", "mastodon", (parts.hostname or "").lower(), toot[1]) if toot else None
    )


def read_post(
    ref: PostRef,
    *,
    get_json: Callable[[str], Any],
    allowed: Callable[[str], bool],
) -> Post | None:
    """The post's text and links, or None when it is private, deleted, not there, or its
    server does not allow it to be read. `get_json` fetches an address as JSON, or None;
    `allowed` says whether a site's own rules let this client fetch an address."""
    if ref.how == "bluesky":
        read = _bluesky(ref, get_json)
    elif ref.how == "hackernews":
        read = _hacker_news(ref, get_json)
    else:
        read = _mastodon(ref, get_json, allowed)
    if read is None:
        return None
    text, links = read
    text = "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
    kept = tuple(
        dict.fromkeys(link for link in links if link and link.startswith(("http://", "https://")))
    )
    return Post(text[:MAX_POST_CHARACTERS], kept) if text else None


def _bluesky(ref: PostRef, get_json: Callable[[str], Any]) -> tuple[str, list[Any]] | None:
    uri = quote(f"at://{ref.actor}/app.bsky.feed.post/{ref.id}", safe="")
    answered = get_json(f"{BLUESKY}?uri={uri}&depth=0&parentHeight=0") or {}
    found = (answered.get("thread") or {}).get("post") or {}
    record = found.get("record")
    if not record:
        return None
    card = (
        (found.get("embed") or {}).get("external")
        or (record.get("embed") or {}).get("external")
        or {}
    )
    in_text = [
        feature.get("uri")
        for facet in record.get("facets") or []
        for feature in facet.get("features") or []
    ]
    return _with_card(record.get("text") or "", card), [card.get("uri"), *in_text]


def _hacker_news(ref: PostRef, get_json: Callable[[str], Any]) -> tuple[str, list[Any]] | None:
    item = get_json(f"{HACKER_NEWS}/{ref.id}.json")
    if not item or item.get("deleted") or item.get("dead"):
        return None
    text, links = _from_html(item.get("text") or "")
    return "\n".join(part for part in (item.get("title"), text) if part), [item.get("url"), *links]


def _mastodon(
    ref: PostRef, get_json: Callable[[str], Any], allowed: Callable[[str], bool]
) -> tuple[str, list[Any]] | None:
    # Any server can be a Mastodon server, so this one is asked like any site: only if
    # its own rules allow it.
    address = f"https://{ref.host}/api/v1/statuses/{ref.id}"
    if not allowed(address):
        return None
    status = get_json(address)
    if (
        not status
        or status.get("visibility") != "public"
        or not isinstance(status.get("content"), str)
    ):
        return None
    text, links = _from_html(status["content"])
    card = status.get("card") or {}
    return _with_card(text, card), [card.get("url"), *links]


def _with_card(text: str, card: dict[str, Any]) -> str:
    """A post's link card is the linked page's own headline and summary."""
    about = ". ".join(part for part in (card.get("title"), card.get("description")) if part)
    return f"{text}\nThe page it links to: {about}" if about else text


class _PostHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.pieces: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        given = {name: value or "" for name, value in attrs}
        if tag in LINE_ENDS:
            self.pieces.append("\n")
        # A link to a tag or to a person is not a link out.
        elif (
            tag == "a"
            and given.get("href")
            and not re.search(r"\b(mention|hashtag)\b", given.get("class", ""))
        ):
            self.links.append(given["href"])

    def handle_endtag(self, tag: str) -> None:
        if tag in LINE_ENDS:
            self.pieces.append("\n")

    def handle_data(self, data: str) -> None:
        self.pieces.append(data)


def _from_html(html: str) -> tuple[str, list[str]]:
    reader = _PostHtml()
    reader.feed(html)
    reader.close()
    return "".join(reader.pieces), reader.links
