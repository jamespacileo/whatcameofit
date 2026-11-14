"""Research Organization Registry (ROR) v2. Terms and limits: docs/sources.md."""

from dataclasses import dataclass
from typing import Any

from thenwhat.sources.base import Source, SourceRecord

API = "https://api.ror.org/v2/organizations"
RECORD_PREFIX = "https://ror.org/"


@dataclass(frozen=True, slots=True)
class Organisation:
    name: str
    country: str
    website: str | None
    # ROR's own measure of how well the name matched, from 0 to 1.
    name_match: float


def describe(record: SourceRecord) -> Organisation:
    """The details of a ROR affiliation match that the pipeline uses."""
    organisation = record.payload.get("organization") or {}
    names = organisation.get("names") or []
    shown = next(
        (name for name in names if "ror_display" in (name.get("types") or [])),
        names[0] if names else {},
    )
    locations = organisation.get("locations") or [{}]
    website = next(
        (
            link.get("value")
            for link in organisation.get("links") or []
            if link.get("type") == "website"
        ),
        None,
    )
    score = record.payload.get("score")
    return Organisation(
        name=str(shown.get("value") or ""),
        country=str((locations[0].get("geonames_details") or {}).get("country_name") or ""),
        website=str(website) if website else None,
        name_match=min(1.0, max(0.0, float(score))) if isinstance(score, int | float) else 0.0,
    )


class Ror(Source):
    name = "ror"
    default_rate_per_second = 2.0

    def organisations(self, name: str) -> list[SourceRecord]:
        """The organisation ROR matches to this name: the one it marks as chosen, or
        none. ROR also lists near misses; they are not matches and are not returned."""
        fetched = self._get(API, {"affiliation": name})
        if fetched is None:
            return []
        records: list[SourceRecord] = []
        for item in fetched.payload.get("items") or []:
            address = str((item.get("organization") or {}).get("id") or "")
            if item.get("chosen") is True and address.startswith(RECORD_PREFIX):
                records.append(self._record(item, address, fetched))
        return records

    def _record(self, item: dict[str, Any], address: str, fetched: Any) -> SourceRecord:
        return SourceRecord(
            source_name=self.name,
            external_id=address.removeprefix(RECORD_PREFIX),
            url=address,
            payload=item,
            fetched_at=fetched.fetched_at,
        )
