"""NLM's Medical Subject Headings (MeSH), read from MeSH RDF. Terms and limits:
docs/sources.md. Behavior: openspec source-clients, "A subject term is looked up by
identifier and by label".

NLM asks that the version of MeSH be stated. A record does not hold it, so every request
names the year's vocabulary in its address and the version is read back from the record.
"""

import re
from dataclasses import dataclass
from typing import Any

from thenwhat.sources.base import Source, SourceRecord, SourceUnavailable

BASE = "https://id.nlm.nih.gov/mesh"
# Where a record says it lives. NLM writes these with http.
RESOURCE = re.compile(r"^https?://id\.nlm\.nih\.gov/mesh/(?:(\d{4})/)?([A-Z]\d+)$")
# A descriptor (D) or a supplementary record (C), as the trial registry gives them.
IDENTIFIER = re.compile(r"^[DC]\d{6,9}$")
# A supplementary record. Its definition is its own note, not its concept's.
SUPPLEMENTARY = re.compile(r"^C\d+$")
MAX_LABELLED = 10
# The record each entry term belongs to: from the term to the concept that lists it to
# the descriptor or supplementary record that lists that concept (docs/sources.md).
OWNERS_QUERY = (
    "PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>"
    " PREFIX mesh: <http://id.nlm.nih.gov/mesh/>"
    " PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"
    " SELECT ?term ?record ?label ?type WHERE {{"
    " VALUES ?term {{ {terms} }}"
    " ?concept meshv:term|meshv:preferredTerm ?term ."
    " ?record meshv:concept|meshv:preferredConcept ?concept ."
    " ?record rdfs:label ?label ."
    " ?record a ?type ."
    " }} ORDER BY ?term ?record"
)


@dataclass(frozen=True, slots=True)
class LabelledTerm:
    identifier: str
    label: str
    # The entry term that equals the name, when the label itself does not.
    entry_term: str | None = None


@dataclass(frozen=True, slots=True)
class _Lookup:
    terms: tuple[LabelledTerm, ...]
    # Entry terms equal to the name whose record the vocabulary did not give.
    unresolved: tuple[str, ...]


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
    """The parts of a stored term record that the pipeline uses. A descriptor's
    definition is its preferred concept's scope note; a supplementary record's is its
    own note. The paper a supplementary record was taken from is not read."""
    term = record.payload.get("term") or {}
    concept = record.payload.get("concept") or {}
    address = RESOURCE.match(str(term.get("@id") or ""))
    return Term(
        identifier=record.external_id,
        label=_text(term.get("label")) or "",
        definition=(
            _text(term.get("note"))
            if SUPPLEMENTARY.match(record.external_id)
            else _text(concept.get("scopeNote"))
        ),
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
        """The terms whose label, or one of whose entry terms, equals the name, whatever
        its case, each once. A term found by its entry term says which one. A label or
        entry term that only contains the name is not equal to it and is never returned,
        and neither is an entry term whose record the vocabulary does not give."""
        return list(self._look_up(name).terms)

    def unresolved_entry_terms(self, name: str) -> list[str]:
        """The entry terms equal to the name whose record could not be found. They make
        no candidate; the caller reports them."""
        return list(self._look_up(name).unresolved)

    def _look_up(self, name: str) -> _Lookup:
        name = " ".join(name.split())
        if not name:
            return _Lookup((), ())
        found = {
            identifier: LabelledTerm(identifier, label)
            for identifier, label in self._equal(name, "descriptor")
        }
        entry_terms = dict(self._equal(name, "term"))
        owners = self._owners(list(entry_terms))
        unresolved: list[str] = []
        for term_id, wording in entry_terms.items():
            if not owners.get(term_id):
                unresolved.append(wording)
            for identifier, label in owners.get(term_id, []):
                # A term found by its label too is a label match only.
                found.setdefault(
                    identifier,
                    LabelledTerm(identifier, label, None if _same(label, name) else wording),
                )
        return _Lookup(tuple(found.values()), tuple(unresolved))

    def _equal(self, name: str, kind: str) -> list[tuple[str, str]]:
        """What the exact lookup of `kind` ("descriptor" or "term") answers for the
        name, as identifier and label, compared here as well."""
        fetched = self._get(
            f"{BASE}/lookup/{kind}",
            {
                "label": name,
                "match": "exact",
                "limit": str(MAX_LABELLED),
                "year": str(self._time.now().year),
            },
        )
        if fetched is None or not isinstance(fetched.payload, list):
            return []
        found: list[tuple[str, str]] = []
        for item in fetched.payload:
            if not isinstance(item, dict):
                continue
            address = RESOURCE.match(str(item.get("resource") or ""))
            label = item.get("label")
            if address is None or not isinstance(label, str) or not _same(label, name):
                continue
            # A descriptor lookup answers descriptors (D), a term lookup terms (T).
            if address.group(2).startswith("T" if kind == "term" else "D"):
                found.append((address.group(2), label))
        return found

    def _owners(self, term_ids: list[str]) -> dict[str, list[tuple[str, str]]]:
        """For each entry term, the descriptors and supplementary records it belongs
        to, as identifier and label, from one query for all of them. A term the answer
        does not mention has none, and so has every term when the service does not
        answer: the next run asks again."""
        if not term_ids:
            return {}
        query = OWNERS_QUERY.format(terms=" ".join(f"mesh:{term_id}" for term_id in term_ids))
        try:
            fetched = self._get(
                f"{BASE}/sparql",
                {
                    "query": query,
                    "format": "JSON",
                    "year": str(self._time.now().year),
                    "inference": "false",
                },
            )
        except SourceUnavailable:
            return {}
        answered = fetched.payload if fetched is not None else None
        results = answered.get("results") if isinstance(answered, dict) else None
        rows = results.get("bindings") if isinstance(results, dict) else None
        owners: dict[str, list[tuple[str, str]]] = {}
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            term, record, label = (_binding(row, name) for name in ("term", "record", "label"))
            term_at = RESOURCE.match(term or "")
            record_at = RESOURCE.match(record or "")
            if term_at is None or record_at is None or not label:
                continue
            identifier = record_at.group(2)
            if IDENTIFIER.match(identifier) and (identifier, label) not in owners.setdefault(
                term_at.group(2), []
            ):
                owners[term_at.group(2)].append((identifier, label))
        return owners


def _binding(row: dict[str, Any], name: str) -> str | None:
    value = row.get(name)
    text = value.get("value") if isinstance(value, dict) else None
    return text if isinstance(text, str) and text else None
