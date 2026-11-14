"""One small icon per outlet domain, fetched politely. Behavior: openspec site-publishing.

The icon is the one the outlet's own site serves to identify itself. It is asked for
once per domain: robots.txt is honoured on every host touched, the client names itself
with a contact address, requests are spaced out, and nothing over the size cap is kept.
The outlet's home page may be read to find where its icon is; that page is kept nowhere.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.db.models import OutletIcon, SourceArticle
from thenwhat.sources.base import (
    CLIENT_NAME,
    Pacer,
    SystemTime,
    Time,
    require_contact,
    user_agent,
)

MAX_ICON_BYTES = 100_000
MAX_PAGE_BYTES = 2_000_000
MAX_ROBOTS_BYTES = 500_000
MAX_REDIRECTS = 3
# At most this many icons named by a home page are tried after /favicon.ico.
MAX_DECLARED = 2
SECONDS_BETWEEN_REQUESTS = 1.0
# The size the site draws an icon at, doubled for dense screens.
WANTED_PIXELS = 32


def outlet_domain(url: str) -> str:
    """The short domain the site shows for an article: its host without a leading www."""
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")


def image_type(content: bytes) -> str | None:
    """The media type of a raster image, told from its first bytes, or None.

    What a server calls the file is not trusted. SVG is left out on purpose: it is a
    document that can carry script, and the site would serve it from its own address.
    """
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\x00\x00\x01\x00"):
        return "image/x-icon"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def is_blank_icon(content: bytes) -> bool:
    """True for an ICO file whose every image is marked fully transparent.

    Some sites answer /favicon.ico with such a placeholder and name their real icon
    on the home page. Only the plain bitmap images an ICO holds are read; a file
    that holds a PNG, or cannot be read, is not called blank.
    """
    if not content.startswith(b"\x00\x00\x01\x00") or len(content) < 6:
        return False
    count = int.from_bytes(content[4:6], "little")
    if count == 0:
        return False
    for index in range(count):
        entry = content[6 + 16 * index : 22 + 16 * index]
        if len(entry) < 16:
            return False
        size = int.from_bytes(entry[8:12], "little")
        offset = int.from_bytes(entry[12:16], "little")
        image = content[offset : offset + size]
        # A bitmap starts with a 40-byte header; its height counts the colour rows
        # and the transparency mask's rows together.
        if len(image) < 40 or int.from_bytes(image[0:4], "little") != 40:
            return False
        width = int.from_bytes(image[4:8], "little")
        height = int.from_bytes(image[8:12], "little") // 2
        mask_row = (width + 31) // 32 * 4
        mask = image[len(image) - mask_row * height :]
        if width == 0 or height == 0 or len(mask) != mask_row * height:
            return False
        for row in range(height):
            bits = int.from_bytes(mask[row * mask_row : (row + 1) * mask_row], "big")
            if bits >> (mask_row * 8 - width) != (1 << width) - 1:
                return False
    return True


@dataclass(frozen=True, slots=True)
class FetchedIcon:
    """What asking one outlet gave. With no usable icon, only the time is set."""

    fetched_at: datetime
    url: str | None = None
    media_type: str | None = None
    content: bytes | None = None


class IconFetcher:
    def __init__(
        self,
        *,
        contact_email: str | None,
        transport: httpx.BaseTransport | None = None,
        time: Time | None = None,
    ) -> None:
        self._contact = (contact_email or "").strip()
        self._time = time or SystemTime()
        self._client = httpx.Client(transport=transport, timeout=30.0, follow_redirects=False)
        self._robots: dict[str, RobotFileParser | None] = {}
        self._pacer = Pacer()

    def fetch(self, site: str) -> FetchedIcon:
        """The icon of the outlet at `site`, an address such as https://www.example.org.

        /favicon.ico is tried first, then the icons the home page names. A blank
        placeholder is passed over like a file that is not an image.
        """
        require_contact(self._contact)
        for url in self._candidates(site):
            content = self._get(url, MAX_ICON_BYTES)
            media_type = image_type(content) if content else None
            if content and media_type and not is_blank_icon(content):
                return FetchedIcon(self._time.now(), url, media_type, content)
        return FetchedIcon(self._time.now())

    def _candidates(self, site: str) -> Iterator[str]:
        yield urljoin(site, "/favicon.ico")
        page = self._get(urljoin(site, "/"), MAX_PAGE_BYTES)
        if page:
            yield from _declared_icons(page.decode("utf-8", errors="replace"), site)[:MAX_DECLARED]

    def _get(self, url: str, cap: int, *, check_robots: bool = True) -> bytes | None:
        """The body at `url` when it is allowed, answers 200 and fits in `cap` bytes."""
        for _ in range(MAX_REDIRECTS + 1):
            if urlsplit(url).scheme not in ("http", "https"):
                return None
            if check_robots and not self._allowed(url):
                return None
            self._wait_for_turn()
            headers = {"User-Agent": user_agent(self._contact)}
            try:
                with self._client.stream("GET", url, headers=headers) as response:
                    if response.is_redirect and "location" in response.headers:
                        url = urljoin(url, response.headers["location"])
                        continue
                    if response.status_code != 200:
                        return None
                    body = b""
                    for chunk in response.iter_bytes():
                        body += chunk
                        if len(body) > cap:
                            return None
                    return body
            except httpx.TransportError:
                return None
        return None

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._rules(origin)
        rules = self._robots[origin]
        return rules is not None and rules.can_fetch(CLIENT_NAME, url)

    def _rules(self, origin: str) -> RobotFileParser | None:
        """The host's robots.txt. None when its rules could not be learned: do not fetch."""
        self._wait_for_turn()
        headers = {"User-Agent": user_agent(self._contact)}
        rules = RobotFileParser()
        try:
            response = self._client.get(
                f"{origin}/robots.txt", headers=headers, follow_redirects=True
            )
        except httpx.TransportError:
            return None
        if response.status_code >= 500 or response.status_code in (401, 403):
            return None
        if response.status_code >= 400:
            rules.parse([])  # no robots.txt: nothing is disallowed
        elif len(response.content) > MAX_ROBOTS_BYTES:
            return None
        else:
            rules.parse(response.text.splitlines())
        return rules

    def _wait_for_turn(self) -> None:
        self._pacer.wait(self._time, SECONDS_BETWEEN_REQUESTS)


class _IconLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "link":
            return
        values = {name: (value or "") for name, value in attrs}
        rel = values.get("rel", "").lower().split()
        href = values.get("href", "").strip()
        if not href or not ({"icon", "apple-touch-icon"} & set(rel)):
            return
        if "svg" in values.get("type", "").lower() or urlsplit(href).path.lower().endswith(".svg"):
            return
        self.found.append((_rank(values.get("sizes", ""), touch="icon" not in rel), href))


def _rank(sizes: str, *, touch: bool) -> int:
    """Lower is better: the stated size nearest the wanted one, plain icons first."""
    first = sizes.lower().split()[0] if sizes.split() else ""
    width = first.partition("x")[0]
    pixels = int(width) if width.isdigit() else (180 if touch else WANTED_PIXELS)
    return abs(pixels - WANTED_PIXELS) + (1 if touch else 0)


def _declared_icons(html: str, site: str) -> list[str]:
    """Addresses of the raster icons a page names, best first."""
    links = _IconLinks()
    links.feed(html)
    ordered = sorted(links.found, key=lambda entry: entry[0])
    return list(dict.fromkeys(urljoin(urljoin(site, "/"), href) for _, href in ordered))


@dataclass(slots=True)
class IconRun:
    """What one run did, by outlet domain."""

    stored: list[str] = field(default_factory=list)
    none_found: list[str] = field(default_factory=list)
    already_asked: int = 0


def fetch_outlet_icons(
    session: Session, fetcher: IconFetcher, *, retry_missing: bool = False
) -> IconRun:
    """Ask each outlet that has a source article for its icon, once.

    A domain asked before is left alone, whatever the answer was. With `retry_missing`,
    domains that had no usable icon, or whose kept icon is a blank placeholder, are
    asked again.
    """
    sites: dict[str, str] = {}
    for url in session.scalars(select(SourceArticle.url).order_by(SourceArticle.id)):
        parts = urlsplit(url)
        domain = outlet_domain(url)
        if domain and parts.scheme in ("http", "https"):
            sites.setdefault(domain, f"{parts.scheme}://{parts.netloc}")

    run = IconRun()
    for domain, site in sorted(sites.items()):
        row = session.get(OutletIcon, domain)
        usable = row is not None and row.content is not None and not is_blank_icon(row.content)
        if row is not None and (usable or not retry_missing):
            run.already_asked += 1
            continue
        fetched = fetcher.fetch(site)
        row = row or OutletIcon(domain=domain)
        row.icon_url = fetched.url
        row.media_type = fetched.media_type
        row.content = fetched.content
        row.fetched_at = fetched.fetched_at
        session.add(row)
        session.flush()
        (run.stored if fetched.content else run.none_found).append(domain)
    return run
