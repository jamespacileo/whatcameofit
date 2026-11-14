"""NLM's Medical Subject Headings (MeSH), read from MeSH RDF. Terms and limits:
docs/sources.md. Behavior: openspec source-clients, "A subject term is looked up by
identifier and by label".

NLM asks that the version of MeSH be stated. A record does not hold it, so every request
names the year's vocabulary in its address and the version is read back from the record.
"""

import re
from dataclasses import dataclass
from typing import Any

from thenwhat.sources.base import Source, SourceRecord

BASE = "https://id.nlm.nih.gov/mesh"
# Where a record says it lives. NLM writes these with http.
RESOURCE = re.compile(r"^https?://id\.nlm\.nih\.gov/mesh/(?:(\d{4})/)?([A-Z]\d+)$")
# A descriptor (D) or a supplementary record (C), as the trial registry gives them.
IDENTIFIER = re.compile(r"^[DC]\d{6,9}$")
MAX_LABELLED = 10


@dataclass(frozen=True, slots=True)
class LabelledTerm:
    identifier: str
    label: str


@dataclass(frozen=True, slots=True)
class Term:
    identifier: str
    label: str
    # The publisher's own words, or None when the term has none.
    definition: str | None
    # The year of the vocabulary the record was read from.
    version: str | None


def _text(value: Any) -> str | None:
    """A JSON-LD text value, which is a string or an object holding one."""
    if isinstance(value, dict):
        value = value.get("@value")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _same(one: str, other: str) -> bool:
    return " ".join(one.split()).casefold() == " ".join(other.split()).casefold()


def describe(record: SourceRecord) -> Term:
    """The parts of a stored term record that the pipeline uses."""
    term = record.payload.get("term") or {}
    concept = record.payload.get("concept") or {}
    address = RESOURCE.match(str(term.get("@id") or ""))
    return Term(
        identifier=record.external_id,
        label=_text(term.get("label")) or "",
        definition=_text(concept.get("scopeNote")),
        version=address.group(1) if address else None,
    )


class Mesh(Source):
    name = "mesh"
    default_rate_per_second = 2.0

    def term(self, identifier: str, *, force: bool = False) -> SourceRecord | None:
        """The term's record with its preferred concept's, which holds the definition.
        None for an identifier the vocabulary does not hold."""
        if not IDENTIFIER.match(identifier):
            return None
        year = self._time.now().year
        fetched = self._get(f"{BASE}/{year}/{identifier}.json", force=force)
        # An unknown identifier answers with an empty object, not with not-found.
        if fetched is None or not isinstance(fetched.payload, dict) or not fetched.payload:
            return None
        concept: dict[str, Any] | None = None
        preferred = RESOURCE.match(str(fetched.payload.get("preferredConcept") or ""))
        if preferred is not None:
            answered = self._get(f"{BASE}/{year}/{preferred.group(2)}.json", force=force)
            if answered is not None and isinstance(answered.payload, dict) and answered.payload:
                concept = answered.payload
        return SourceRecord(
            source_name=self.name,
            external_id=identifier,
            url=f"{BASE}/{identifier}",
            payload={"term": fetched.payload, "concept": concept},
            fetched_at=fetched.fetched_at,
        )

    def terms_labelled(self, name: str) -> list[LabelledTerm]:
        """The terms whose label equals the name, whatever its case. A label that only
        contains the name is not equal to it and is never returned."""
        name = " ".join(name.split())
        if not name:
            return []
        fetched = self._get(
            f"{BASE}/lookup/descriptor",
            {
                "label": name,
                "match": "exact",
                "limit": str(MAX_LABELLED),
                "year": str(self._time.now().year),
            },
        )
        if fetched is None or not isinstance(fetched.payload, list):
            return []
        found: list[LabelledTerm] = []
        for item in fetched.payload:
            if not isinstance(item, dict):
                continue
            address = RESOURCE.match(str(item.get("resource") or ""))
            label = item.get("label")
            if address is not None and isinstance(label, str) and _same(label, name):
                found.append(LabelledTerm(address.group(2), label))
        return found
