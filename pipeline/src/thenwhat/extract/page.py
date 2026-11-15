"""What a news page says about itself, beyond its visible text. Behavior: openspec live-lookup.

A page names its headline, summary and date in tags made for other software, often carries
the article as structured data, and links to the paper or the registry record it reports.
All of it is read from the page the site served and kept nowhere, like the text.
"""

import json
import re
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from typing import Any
from urllib.parse import unquote

SKIPPED_ELEMENTS = {"script", "style", "noscript", "template", "svg"}
STRUCTURED_DATA = "application/ld+json"
REGISTRY_NUMBER = re.compile(r"NCT\d{8}", re.IGNORECASE)
DOI = r"10\.\d{4,9}/[^\s?#&\"'<>]+"
# Where a link gives a paper's DOI: the resolver itself, or a publisher's own address.
DOI_LINKS = (
    re.compile(rf"doi\.org/({DOI})", re.IGNORECASE),
    re.compile(rf"/doi/(?:(?:full|abs|pdf|epdf|epub)/)?({DOI})", re.IGNORECASE),
)
# Publishers whose article address holds the DOI's second half.
NATURE = re.compile(r"nature\.com/articles/([a-z0-9][a-z0-9.-]+)", re.IGNORECASE)
ELSEVIER_PII = re.compile(r"(?:thelancet|cell)\.com/[^\s\"']*?/PII(S[0-9X()-]+)", re.IGNORECASE)
PUBMED = re.compile(r"(?:pubmed\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov/pubmed)/(\d{4,9})")
# A body shorter than this is a teaser, not the article.
BODY_FROM = 500
# The most papers and registry numbers one page is taken to report.
MAX_LINKED = 5
HEADLINE_TAGS = ("og:title", "twitter:title")
SUMMARY_TAGS = ("og:description", "description", "twitter:description")
DATE_TAGS = ("article:published_time", "date", "dc.date", "pubdate", "parsely-pub-date")
# Elements, by id, in which an outlet shows its date as words and gives it in no tag.
# sciencedaily.com: seen on four of its pages on 2026-11-14.
DATE_ELEMENT_IDS = ("date_posted",)
ISO_DAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:$|[T\s])")
MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
MONTH = "|".join(f"{month[:3]}[a-z]*" for month in MONTHS)
WORDED_MONTH_FIRST = re.compile(
    rf"\b({MONTH})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I
)
WORDED_DAY_FIRST = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTH})\.?,?\s+(\d{{4}})\b", re.I
)


@dataclass(frozen=True, slots=True)
class Page:
    # The marked main content, or all visible text when no main content is marked.
    text: str
    headline: str | None = None
    summary: str | None = None
    # The publication date as the page gives it.
    published: str | None = None
    # The article as the page's structured data carries it, when it does.
    body: str | None = None
    registry_numbers: tuple[str, ...] = ()
    dois: tuple[str, ...] = ()
    pubmed_ids: tuple[str, ...] = ()

    def as_text(self) -> str:
        """The page for a reader who sees only text: what it is first, then the article."""
        lead = [
            f"{label}: {value}"
            for label, value in (
                ("Headline", self.headline),
                ("Summary", self.summary),
                ("Published", self.published),
            )
            if value
        ]
        body = self.body if self.body and len(self.body) >= BODY_FROM else self.text
        return "\n\n".join(part for part in ("\n".join(lead), body) if part)


def read_page(html: str, main: str | None = None) -> Page:
    """What a page says, from its HTML as drawn. `main` is the page's main content as
    the page reader cut it out: when given, the text is its text, and everything else
    still comes from the whole page (openspec page-reading)."""
    collector = _Collector()
    collector.feed(html)
    collector.close()
    all_text = _tidy(" ".join(collector.pieces))
    text = _tidy(" ".join(collector.main_pieces)) or all_text
    if main is not None:
        content = _Collector()
        content.feed(main)
        content.close()
        text = _tidy(" ".join(content.pieces))
    described = _structured(collector.structured)
    tags = collector.tags
    links = " ".join(collector.links)
    return Page(
        text=text,
        headline=_first(tags, HEADLINE_TAGS) or described.get("headline") or collector.title,
        summary=_first(tags, SUMMARY_TAGS) or described.get("description"),
        published=_first(tags, DATE_TAGS) or described.get("datePublished") or collector.posted,
        body=described.get("articleBody"),
        registry_numbers=_unique(
            number.upper() for number in REGISTRY_NUMBER.findall(f"{all_text} {links}")
        ),
        dois=_unique(_dois(links)),
        pubmed_ids=_unique(PUBMED.findall(links)),
    )


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.pieces: list[str] = []
        self.main_pieces: list[str] = []
        self.links: list[str] = []
        self.tags: dict[str, str] = {}
        self.structured: list[str] = []
        self.title: str | None = None
        # The date as an element known to hold it shows it, when the page has one.
        self.posted: str | None = None
        self._date_element: str | None = None
        self._date_pieces: list[str] = []
        self._skipping = 0
        self._in_title = False
        self._in_structured = False
        self._main_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        given = {name: value or "" for name, value in attrs}
        looking = self.posted is None and self._date_element is None
        if looking and given.get("id", "").lower() in DATE_ELEMENT_IDS:
            self._date_element = tag
        if tag == "main":
            self._main_depth += 1
        if tag == "a" and given.get("href"):
            self.links.append(unquote(given["href"]))
        elif tag == "meta":
            name = (given.get("property") or given.get("name") or "").lower()
            if name and given.get("content"):
                self.tags.setdefault(name, _tidy(given["content"]))
        elif tag == "title":
            self._in_title = True
        elif tag == "script" and given.get("type", "").lower() == STRUCTURED_DATA:
            self._in_structured = True
            self.structured.append("")
        if tag in SKIPPED_ELEMENTS:
            self._skipping += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == self._date_element:
            self.posted = _tidy(" ".join(self._date_pieces)) or None
            self._date_element = None
            self._date_pieces = []
        if tag == "main" and self._main_depth:
            self._main_depth -= 1
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            self._in_structured = False
        if tag in SKIPPED_ELEMENTS and self._skipping:
            self._skipping -= 1

    def handle_data(self, data: str) -> None:
        if self._in_structured:
            self.structured[-1] += data
        elif not self._skipping:
            if self._date_element is not None:
                self._date_pieces.append(data)
            self.pieces.append(data)
            if self._main_depth:
                self.main_pieces.append(data)
            if self._in_title and self.title is None and data.strip():
                self.title = _tidy(data)


def published_day(published: str | None) -> date | None:
    """The day a page says it was published, from the date as the page gives it: a
    timestamp such as 2026-10-22T09:00:00Z, or words such as "April 30, 2021" or
    "30 April 2021". None when the page gives no date or one in another form. The day
    is the one the outlet wrote: a time zone is not applied."""
    text = _tidy(published or "")
    if not text:
        return None
    try:
        stamped = ISO_DAY.match(text)
        if stamped:
            return date(int(stamped[1]), int(stamped[2]), int(stamped[3]))
        worded = WORDED_MONTH_FIRST.search(text)
        if worded:
            return date(int(worded[3]), _month(worded[1]), int(worded[2]))
        worded = WORDED_DAY_FIRST.search(text)
        if worded:
            return date(int(worded[3]), _month(worded[2]), int(worded[1]))
    except ValueError:
        return None  # a day that is not in the calendar
    return None


def _month(word: str) -> int:
    """The number of a month given as its name or the start of it."""
    start = word[:3].lower()
    return next(number for number, month in enumerate(MONTHS, start=1) if month[:3] == start)


def _structured(blocks: list[str]) -> dict[str, str]:
    """The article's own fields, from the first structured-data object that has each."""
    found: dict[str, str] = {}

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for name in ("headline", "description", "datePublished", "articleBody"):
                value = node.get(name)
                if isinstance(value, str) and value.strip():
                    found.setdefault(name, _tidy(value))
            for value in node.values():
                if isinstance(value, dict | list):
                    walk(value)

    for block in blocks:
        try:
            walk(json.loads(block))
        except ValueError:
            continue  # a page's structured data is often malformed; the rest still counts
    return found


def _dois(links: str) -> list[str]:
    found = [doi.rstrip(".,;") for pattern in DOI_LINKS for doi in pattern.findall(links)]
    found += [f"10.1038/{name}" for name in NATURE.findall(links)]
    found += [f"10.1016/{pii}" for pii in ELSEVIER_PII.findall(links)]
    return [doi.lower() for doi in found]


def _first(tags: dict[str, str], names: tuple[str, ...]) -> str | None:
    return next((tags[name] for name in names if tags.get(name)), None)


def _unique(items: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))[:MAX_LINKED]


def _tidy(text: str) -> str:
    return " ".join(text.split())
