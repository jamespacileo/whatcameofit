"""OpenAlex literature search. Terms, key rules and allowance: docs/sources.md."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.dialects.postgresql import insert

from thenwhat.db.models import HttpCache
from thenwhat.sources.base import AllowanceUsedUp, MissingKey, Source, SourceRecord

API = "https://api.openalex.org"
# What is asked for of each work. The abstract is used to score a paper and to find its
# reasons, in memory and in the HTTP cache only; it is never exported, logged or shown.
FIELDS = (
    "id,doi,title,publication_year,publication_date,type,primary_location,"
    "authorships,abstract_inverted_index,ids"
)
MAX_RESULTS = 20
DOI_PREFIX = "https://doi.org/"
WORK_PREFIX = "https://openalex.org/"
# What a search costs when the source's answer does not say.
SEARCH_COST_USD = 0.001
# The literature changes slowly and every search is charged, so a search's answer is
# kept for a week. A claim resolved again within the week spends nothing.
SEARCH_TTL = timedelta(days=7)
# Where it is kept, for every run and process, that no search may be sent for now.
PAUSE_KEY = "openalex searches paused"

USED_UP = "OpenAlex's free allowance for the day is used up."
NOT_STATED = (
    "OpenAlex did not say what is left of the day's allowance, so no further search is sent today."
)
PAID_CREDIT = (
    "The OpenAlex account holds prepaid credit. The pipeline draws on the free allowance"
    " only, so no further search is sent today. Remove the credit to search again."
)


@dataclass(slots=True)
class Usage:
    """What one run asked of OpenAlex's search, for the operator to see."""

    searches_sent: int = 0
    searches_from_cache: int = 0
    spent_usd: float = 0.0
    # What the source last said is left of the day's free allowance.
    remaining_usd: float | None = None
    # Why no further search is sent, once that is so.
    stopped: str | None = None

    def line(self) -> str:
        """One line for the operator: what was sent, what it cost and what is left."""
        sent = "search" if self.searches_sent == 1 else "searches"
        parts = [f"OpenAlex: {self.searches_sent} {sent} sent (${self.spent_usd:.3f})"]
        if self.searches_from_cache:
            parts.append(f"{self.searches_from_cache} answered from the week's cache")
        if self.remaining_usd is not None:
            parts.append(f"${self.remaining_usd:.3f} of the free allowance left today")
        line = ", ".join(parts) + "."
        return f"{line} {self.stopped}" if self.stopped else line


@dataclass(frozen=True, slots=True)
class Author:
    name: str
    # Each institution on the authorship, as (name, ROR identifier or None).
    institutions: tuple[tuple[str, str | None], ...]


@dataclass(frozen=True, slots=True)
class PaperRecord:
    title: str
    year: int | None
    published_date: date | None
    kind: str
    journal: str
    doi: str | None
    pubmed_id: str | None
    authors: tuple[Author, ...]
    abstract: str


def describe(record: SourceRecord) -> PaperRecord:
    """The details of an OpenAlex work that the pipeline uses."""
    work = record.payload
    published = work.get("publication_date")
    try:
        published_date = date.fromisoformat(published) if published else None
    except ValueError:
        published_date = None
    source = (work.get("primary_location") or {}).get("source") or {}
    pubmed = str((work.get("ids") or {}).get("pmid") or "").rstrip("/").rsplit("/", 1)[-1]
    return PaperRecord(
        title=str(work.get("title") or ""),
        year=work.get("publication_year"),
        published_date=published_date,
        kind=str(work.get("type") or ""),
        journal=str(source.get("display_name") or ""),
        doi=_doi(work),
        pubmed_id=pubmed if pubmed.isdigit() else None,
        authors=tuple(
            Author(
                name=str((authorship.get("author") or {}).get("display_name") or ""),
                institutions=tuple(
                    (str(institution.get("display_name") or ""), _ror(institution.get("ror")))
                    for institution in authorship.get("institutions") or []
                ),
            )
            for authorship in work.get("authorships") or []
        ),
        abstract=_abstract(work.get("abstract_inverted_index")),
    )


def _doi(work: dict[str, Any]) -> str | None:
    doi = str(work.get("doi") or "").removeprefix(DOI_PREFIX).lower()
    return doi if doi.startswith("10.") else None


def _ror(address: Any) -> str | None:
    return str(address).rstrip("/").rsplit("/", 1)[-1] if address else None


def _abstract(index: Any) -> str:
    """The abstract as text. OpenAlex gives it as each word with its positions."""
    if not isinstance(index, dict):
        return ""
    placed = sorted((position, word) for word, positions in index.items() for position in positions)
    return " ".join(word for _, word in placed)


class OpenAlex(Source):
    name = "openalex"
    default_rate_per_second = 2.0

    def __init__(self, *args: Any, api_key: str | None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._key = (api_key or "").strip()
        self.usage = Usage()

    def search_papers(
        self, terms: list[str], condition: str, limit: int = MAX_RESULTS
    ) -> list[SourceRecord]:
        """Papers that name any of the terms together with the condition, most relevant
        first, up to the limit.

        All the terms go into one search, so a claim costs one search however many names
        and phrases its intervention has. Each term and the condition is searched for as
        a phrase. That is the only search: when it finds nothing, nothing is the answer,
        and no looser search is tried in its place. No second page is asked for.
        """
        self._require_key()
        limit = max(1, min(limit, MAX_RESULTS))
        phrases = list(dict.fromkeys(_phrase(term) for term in terms if _phrase(term)))
        about = _phrase(condition)
        if not phrases or not about:
            return []
        return self._search(f"({' OR '.join(phrases)}) AND {about}", limit)

    def _search(self, query: str, limit: int) -> list[SourceRecord]:
        sent = self.usage.searches_sent
        fetched = self._get(
            f"{API}/works",
            {"search": query, "per_page": str(limit), "select": FIELDS},
            ttl=SEARCH_TTL,
        )
        if self.usage.searches_sent == sent:
            self.usage.searches_from_cache += 1
        results = fetched.payload.get("results", []) if fetched else []
        return [
            record
            for work in results[:limit]
            if fetched and (record := self._record(work, fetched.fetched_at))
        ]

    def paper(self, external_id: str) -> SourceRecord | None:
        """The paper a candidate match points to: by its DOI, or by OpenAlex's own
        identifier when it has none. None if OpenAlex does not have it. Looking one
        work up costs nothing, so it is still asked once the day's searches are spent."""
        self._require_key()
        if external_id.startswith("10."):
            known_as = f"doi:{external_id}"
        elif external_id[:1] == "W" and external_id[1:].isdigit():
            known_as = external_id
        else:
            return None
        fetched = self._get(f"{API}/works/{known_as}", {"select": FIELDS})
        return self._record(fetched.payload, fetched.fetched_at) if fetched else None

    def _record(self, work: dict[str, Any], fetched_at: datetime) -> SourceRecord | None:
        own = str(work.get("id") or "").removeprefix(WORK_PREFIX)
        if not own or not work.get("title"):
            return None
        doi = _doi(work)
        return SourceRecord(
            source_name=self.name,
            external_id=doi or own,
            url=f"{DOI_PREFIX}{doi}" if doi else f"{WORK_PREFIX}{own}",
            payload=work,
            fetched_at=fetched_at,
        )

    # --- the key and the allowance ---------------------------------------------------

    def _require_key(self) -> None:
        if not self._key:
            raise MissingKey("OPENALEX_API_KEY is not set, so no request was sent to OpenAlex.")

    def _extra_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}"}

    def _request(self, url: str, params: dict[str, str] | None) -> httpx.Response | None:
        """A search is sent only while none is paused. An answer still in the cache never
        reaches here, and a lookup of one work is free and is always sent."""
        if url == f"{API}/works":
            paused = self._paused()
            if paused:
                self.usage.stopped = paused
                raise AllowanceUsedUp(paused)
        return super()._request(url, params)

    def _heed(self, response: httpx.Response) -> None:
        """Read what the answer says of the allowance. Searches stop, for every run until
        the allowance resets, when it is used up, when it is not stated, or when the
        account holds prepaid credit that a further search could spend."""
        headers = response.headers
        remaining = _amount(headers.get("X-RateLimit-Remaining-USD"))
        cost = _amount(headers.get("X-RateLimit-Cost-USD"))
        prepaid = _amount(headers.get("X-RateLimit-Prepaid-Remaining-USD"))
        reset = _amount(headers.get("X-RateLimit-Reset"))
        nothing_left = remaining is not None and remaining < SEARCH_COST_USD
        if response.status_code == 402 or (
            response.status_code == 429 and (remaining is None or nothing_left)
        ):
            self._pause(USED_UP, reset)
            raise AllowanceUsedUp(USED_UP)
        if not response.is_success or response.request.url.path != "/works":
            return
        self.usage.searches_sent += 1
        self.usage.spent_usd += cost if cost is not None else SEARCH_COST_USD
        self.usage.remaining_usd = remaining
        # This answer is good. Whether the next search may be sent is settled now.
        if prepaid is not None and prepaid > 0:
            self._pause(PAID_CREDIT, reset)
        elif remaining is None or prepaid is None:
            self._pause(NOT_STATED, reset)
        elif nothing_left:
            self._pause(USED_UP, reset)

    def _paused(self) -> str | None:
        """Why no search may be sent now, or None when one may."""
        pause = self._session.get(HttpCache, PAUSE_KEY)
        if pause is None or pause.expires_at <= self._time.now():
            return None
        return str(pause.payload.get("reason") or USED_UP)

    def _pause(self, reason: str, reset_in_seconds: float | None) -> None:
        """Stop searches until the allowance resets: at the time the source gave, or at
        the next midnight UTC. Kept in the database, so every process and later run of the
        day stops too."""
        now = self._time.now()
        if reset_in_seconds is not None and reset_in_seconds > 0:
            until = now + timedelta(seconds=reset_in_seconds)
        else:
            until = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        kept = {
            "source_name": self.name,
            "payload": {"reason": reason},
            "fetched_at": now,
            "expires_at": until,
        }
        self._session.execute(
            insert(HttpCache)
            .values(request_key=PAUSE_KEY, **kept)
            .on_conflict_do_update(index_elements=[HttpCache.request_key], set_=kept)
        )
        held = self._session.get(HttpCache, PAUSE_KEY)
        if held is not None:
            self._session.refresh(held)
        self.usage.stopped = reason


def _words(text: str) -> str:
    """The text with what the search would read as an instruction taken out."""
    return " ".join(text.replace('"', " ").replace("(", " ").replace(")", " ").split())


def _phrase(text: str) -> str:
    """The text as one quoted phrase, or nothing when it has no words."""
    words = _words(text)
    return f'"{words}"' if words else ""


def _amount(header: str | None) -> float | None:
    try:
        return float(header) if header is not None else None
    except ValueError:
        return None
