"""FDA and NCATS Global Substance Registration System (GSRS). Terms and limits:
docs/sources.md. Behavior: openspec source-clients, "A substance is looked up by an
exact name".

A report names a drug by its generic or brand name; a trial registry often files the
same drug under a development code. GSRS lists every name of a substance with its kind,
and one kind is a code. Nothing here guesses: a substance is found only under a name
GSRS lists for it, letter for letter, and a code is only a name GSRS marks as a code.
"""

from datetime import timedelta
from typing import Any

from thenwhat.sources.base import Source, SourceRecord

API = "https://gsrs.ncats.nih.gov/api/v1"
# Where a reader can open a substance's record.
PAGE = "https://gsrs.ncats.nih.gov/ginas/app/ui/substances/{}"
# The kind GSRS gives a name that is a code ("cd", shown as "Code").
CODE = "cd"
# A name that more substances than this carry identifies none; no more are read.
MAX_SUBSTANCES = 5
# A substance's names change rarely.
KEPT_FOR = timedelta(days=30)


def _key(name: str) -> str:
    return " ".join(name.split()).casefold()


def names_of(record: SourceRecord) -> list[dict[str, Any]]:
    """The names GSRS lists for the substance, leaving out any it has withdrawn."""
    listed = record.payload.get("names") or []
    return [
        name
        for name in listed
        if isinstance(name, dict)
        and isinstance(name.get("name"), str)
        and not name.get("deprecated")
    ]


def codes_of(record: SourceRecord) -> list[str]:
    """The names GSRS marks as codes for the substance, as it writes them."""
    codes = [
        " ".join(name["name"].split()) for name in names_of(record) if name.get("type") == CODE
    ]
    return list(dict.fromkeys(code for code in codes if code))


def label_of(record: SourceRecord) -> str:
    """What GSRS calls the substance, with its Unique Ingredient Identifier when it has one."""
    substance = record.payload.get("substance") or {}
    name = str(substance.get("_name") or record.external_id)
    unii = substance.get("approvalID")
    return f"{name} (UNII {unii})" if unii else name


class Gsrs(Source):
    name = "gsrs"
    # No limit is stated. One request a second is well under what a person browsing sends.
    default_rate_per_second = 1.0
    # Code enrichment is optional; a stalled source must not occupy minutes of prepare.
    # Keep one transient retry and the shared Retry-After/pacing/refusal behavior.
    default_max_attempts = 2
    request_timeout = 5.0

    def substances_named(self, name: str) -> list[SourceRecord]:
        """Every substance GSRS lists under exactly this name, whatever its case, each
        with all its names. Empty when no substance carries the name.

        GSRS's own exact search sets punctuation aside ("cin 107" finds CIN-107), so each
        substance's names are read and compared here as well. A name that only resembles
        one of them finds nothing.
        """
        wanted = _key(name)
        # A quotation mark or a backslash would end or alter the quoted search.
        quoted = " ".join(name.replace('"', " ").replace("\\", " ").split())
        if not wanted or not quoted:
            return []
        found = self._get(
            f"{API}/substances/search",
            {"q": f'root_names_name:"^{quoted}$"', "top": str(MAX_SUBSTANCES), "fdim": "0"},
            ttl=KEPT_FOR,
        )
        if found is None or not isinstance(found.payload, dict):
            return []
        records: list[SourceRecord] = []
        for substance in found.payload.get("content") or []:
            identifier = substance.get("uuid") if isinstance(substance, dict) else None
            if not isinstance(identifier, str):
                continue
            names = self._get(f"{API}/substances({identifier})/names", ttl=KEPT_FOR)
            if names is None or not isinstance(names.payload, list):
                continue
            record = SourceRecord(
                source_name=self.name,
                external_id=identifier,
                url=PAGE.format(identifier),
                payload={"substance": substance, "names": names.payload},
                fetched_at=names.fetched_at,
            )
            if any(_key(listed["name"]) == wanted for listed in names_of(record)):
                records.append(record)
        return records
