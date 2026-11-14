"""Europe PMC RESTful web service. Terms and limits: docs/sources.md."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from thenwhat.sources.base import Source, SourceRecord

API = "https://www.ebi.ac.uk/europepmc/webservices/rest"
REGISTRY_NUMBER = re.compile(r"NCT\d{8}", re.IGNORECASE)
# A paper that reports a trial gives its number, sometimes two. One that lists more is a
# review of many trials and identifies none.
MAX_TRIALS_OF_ONE_PAPER = 3


@dataclass(frozen=True, slots=True)
class PaperInfo:
    title: str
    authors: tuple[str, ...]
    published_date: date | None
    doi: str | None
    abstract: str


def describe(record: SourceRecord) -> PaperInfo:
    """The details of a paper record that the pipeline uses."""
    paper = record.payload
    authors = tuple(
        author["fullName"]
        for author in paper.get("authorList", {}).get("author", [])
        if author.get("fullName")
    )
    published = paper.get("firstPublicationDate")
    return PaperInfo(
        title=paper.get("title", ""),
        authors=authors,
        published_date=date.fromisoformat(published) if published else None,
        doi=paper.get("doi"),
        abstract=paper.get("abstractText", ""),
    )


class EuropePmc(Source):
    name = "europepmc"
    default_rate_per_second = 2.0

    def paper(self, doi: str, *, force: bool = False) -> SourceRecord | None:
        """The paper with this DOI, or None if Europe PMC does not have it."""
        fetched = self._get(f"{API}/search", self._search(f'DOI:"{doi}"'), force=force)
        results = fetched.payload["resultList"]["result"] if fetched else []
        if not results or fetched is None:
            return None
        return self._record(results[0], fetched.fetched_at)

    def trial_numbers(self, *, doi: str | None = None, pubmed_id: str | None = None) -> list[str]:
        """The ClinicalTrials.gov numbers a paper's abstract gives for its own trial.

        Empty when Europe PMC does not have the paper, when its abstract gives no number,
        or when it gives so many that the paper is a review and not a trial's report.
        """
        if doi:
            query = f'DOI:"{doi.replace(chr(34), "")}"'
        elif pubmed_id and pubmed_id.isdigit():
            query = f"EXT_ID:{pubmed_id} AND SRC:MED"
        else:
            return []
        fetched = self._get(f"{API}/search", self._search(query))
        results = fetched.payload["resultList"]["result"] if fetched else []
        if not results:
            return []
        abstract = str(results[0].get("abstractText") or "")
        numbers = list(dict.fromkeys(n.upper() for n in REGISTRY_NUMBER.findall(abstract)))
        return numbers if len(numbers) <= MAX_TRIALS_OF_ONE_PAPER else []

    def citing_papers(self, paper: SourceRecord, *, page_size: int = 100) -> list[SourceRecord]:
        """Every paper that cites the given one, following the result cursor to its end."""
        query = f"CITES:{paper.payload['id']}_{paper.payload['source']}"
        records: list[SourceRecord] = []
        cursor = "*"
        while True:
            params = self._search(query) | {"pageSize": str(page_size), "cursorMark": cursor}
            fetched = self._get(f"{API}/search", params)
            results = fetched.payload["resultList"]["result"] if fetched else []
            if not results or fetched is None:
                break
            records += [self._record(result, fetched.fetched_at) for result in results]
            next_cursor = fetched.payload.get("nextCursorMark")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        return records

    @staticmethod
    def _search(query: str) -> dict[str, str]:
        return {"query": query, "format": "json", "resultType": "core"}

    def _record(self, result: dict[str, Any], fetched_at: datetime) -> SourceRecord:
        return SourceRecord(
            source_name=self.name,
            external_id=result.get("doi") or f"{result['source']}:{result['id']}",
            url=f"https://europepmc.org/article/{result['source']}/{result['id']}",
            payload=result,
            fetched_at=fetched_at,
        )
