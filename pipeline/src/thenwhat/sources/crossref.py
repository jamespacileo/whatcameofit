"""Crossref REST API, including Retraction Watch notices. Terms and limits: docs/sources.md."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

from thenwhat.sources.base import Source, SourceRecord

API = "https://api.crossref.org"


@dataclass(frozen=True, slots=True)
class Notice:
    """A retraction, correction or similar notice attached to a paper."""

    type: str
    notice_date: date
    notice_doi: str
    # As the registry gave it, and when; not part of what makes two notices equal.
    raw: dict[str, Any] = field(default_factory=dict, compare=False)
    fetched_at: datetime | None = field(default=None, compare=False)


class Crossref(Source):
    name = "crossref"
    default_rate_per_second = 2.0

    def work(self, doi: str, *, force: bool = False) -> SourceRecord | None:
        """Metadata for a DOI, or None if Crossref does not know it."""
        fetched = self._get(f"{API}/works/{quote(doi.strip(), safe='/()')}", force=force)
        if fetched is None:
            return None
        work = fetched.payload["message"]
        return SourceRecord(
            source_name=self.name,
            external_id=work["DOI"],
            url=f"https://doi.org/{work['DOI']}",
            payload=work,
            fetched_at=fetched.fetched_at,
        )

    def notices(self, doi: str, *, force: bool = False) -> list[Notice]:
        """Retraction and correction notices for a DOI. They come with the work record,
        so this costs no request beyond `work`."""
        work = self.work(doi, force=force)
        if work is None:
            return []
        notices = []
        for update in work.payload.get("updated-by") or []:
            year, month, day = (*update["updated"]["date-parts"][0], 1, 1)[:3]
            notices.append(
                Notice(
                    update["type"],
                    date(year, month, day),
                    update["DOI"],
                    raw=update,
                    fetched_at=work.fetched_at,
                )
            )
        return notices
