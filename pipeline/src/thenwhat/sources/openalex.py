"""OpenAlex literature search. Terms, key rules and allowance: docs/sources.md."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import httpx

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
        self._used_up = False

    def search_papers(self, words: str, limit: int = MAX_RESULTS) -> list[SourceRecord]:
        """Papers about these words, most relevant first, up to the limit. One request:
        no second page is asked for."""
        self._require_key()
        limit = max(1, min(limit, MAX_RESULTS))
        fetched = self._get(
            f"{API}/works", {"search": words, "per_page": str(limit), "select": FIELDS}
        )
        results = fetched.payload.get("results", []) if fetched else []
        return [
            record
            for work in results[:limit]
            if fetched and (record := self._record(work, fetched.fetched_at))
        ]

    def paper(self, external_id: str) -> SourceRecord | None:
        """The paper a candidate match points to: by its DOI, or by OpenAlex's own
        identifier when it has none. None if OpenAlex does not have it."""
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

    def _request(self, url: str, params: dict[str, str] | None) -> httpx.Response | None:
        if self._used_up:
            raise AllowanceUsedUp(_USED_UP)
        return super()._request(url, params)

    def _extra_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}"}

    def _heed(self, response: httpx.Response) -> None:
        remaining = _amount(response.headers.get("X-RateLimit-Remaining-USD"))
        cost = _amount(response.headers.get("X-RateLimit-Cost-USD")) or SEARCH_COST_USD
        nothing_left = remaining is not None and remaining < max(cost, SEARCH_COST_USD)
        if response.status_code == 402 or (
            response.status_code == 429 and (remaining is None or nothing_left)
        ):
            self._used_up = True
            raise AllowanceUsedUp(_USED_UP)
        if nothing_left:
            # This answer is good; the next search would not be, so it is not sent.
            self._used_up = True


_USED_UP = (
    "OpenAlex's allowance for the day is used up. No more papers are searched for in this run."
)


def _amount(header: str | None) -> float | None:
    try:
        return float(header) if header is not None else None
    except ValueError:
        return None
