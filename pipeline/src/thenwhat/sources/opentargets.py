"""Open Targets Platform: human genes by symbol, and a gene's record. Terms and limits:
docs/sources.md. Behavior: openspec source-clients, "A gene is looked up by symbol".

Only targets are read. Drugs and their mechanisms are drawn from ChEMBL under a
share-alike licence and are not asked for (openspec knowledge-cards, task 6.1).
"""

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from thenwhat.sources.base import Source, SourceRecord, record_url

API = "https://api.platform.opentargets.org/api/v4/graphql"
# An Ensembl gene identifier, which is how the platform names a target.
IDENTIFIER = re.compile(r"^ENSG\d{11}$")
# The platform asks not to be queried one entity after another, so a word that was
# answered is not searched for again for this long.
SEARCH_KEPT = timedelta(days=90)
MAX_HITS = 10
_FIELDS = (
    "id approvedSymbol approvedName biotype symbolSynonyms { label source }"
    " functionDescriptions proteinIds { id source }"
)
SEARCH_QUERY = (
    "query TargetsNamed($word: String!) { search(queryString: $word, entityNames:"
    f' ["target"], page: {{index: 0, size: {MAX_HITS}}}) {{ hits {{ id entity object {{'
    f" ... on Target {{ {_FIELDS} }} }} }} }} }}"
)
TARGET_QUERY = f"query Target($id: String!) {{ target(ensemblId: $id) {{ {_FIELDS} }} }}"

SYMBOL = "symbol"
SYNONYM = "synonym"


@dataclass(frozen=True, slots=True)
class NamedTarget:
    """A gene whose approved symbol, or a listed synonym of it, equals a word."""

    identifier: str
    symbol: str
    name: str
    # Which was equal: the approved symbol, or a listed synonym of it.
    equal: str
    # For a synonym, each source the platform says gives it, in the order listed.
    synonym_sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Target:
    identifier: str
    symbol: str
    # The gene's approved name, which is its protein's for a protein-coding gene.
    name: str
    # The first function description, word for word, or None when there is none.
    definition: str | None
    # Every function description, in the order given.
    descriptions: tuple[str, ...]
    biotype: str | None


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _read(target: dict[str, Any]) -> Target:
    described = target.get("functionDescriptions")
    descriptions = tuple(
        text for text in (described if isinstance(described, list) else []) if _text(text)
    )
    return Target(
        identifier=_text(target.get("id")),
        symbol=_text(target.get("approvedSymbol")),
        name=_text(target.get("approvedName")),
        definition=descriptions[0] if descriptions else None,
        descriptions=descriptions,
        biotype=_text(target.get("biotype")) or None,
    )


def describe(record: SourceRecord) -> Target:
    """The parts of a stored target record that the pipeline uses. The description is
    the first the source gives, exactly as given."""
    return _read(record.payload)


class OpenTargets(Source):
    name = "opentargets"
    default_rate_per_second = 2.0

    def targets_named(self, word: str) -> list[NamedTarget]:
        """The genes whose approved symbol, or a listed synonym of it, equals the word,
        whatever its case. The platform's search also answers genes whose symbol only
        starts with the word or resembles it; those are never returned."""
        word = word.strip()
        if not word:
            return []
        fetched = self._post(
            API, {"query": SEARCH_QUERY, "variables": {"word": word}}, ttl=SEARCH_KEPT
        )
        found: list[NamedTarget] = []
        for hit in _hits(fetched.payload if fetched is not None else None):
            target = hit.get("object")
            if hit.get("entity") != "target" or not isinstance(target, dict):
                continue
            read = _read(target)
            if not IDENTIFIER.match(read.identifier) or not read.symbol:
                continue
            if read.symbol.casefold() == word.casefold():
                found.append(NamedTarget(read.identifier, read.symbol, read.name, SYMBOL))
                continue
            sources: list[str] = []
            synonyms = target.get("symbolSynonyms")
            for synonym in synonyms if isinstance(synonyms, list) else []:
                if not isinstance(synonym, dict):
                    continue
                if _text(synonym.get("label")).casefold() != word.casefold():
                    continue
                source = _text(synonym.get("source"))
                if source and source not in sources:
                    sources.append(source)
            if sources:
                found.append(
                    NamedTarget(read.identifier, read.symbol, read.name, SYNONYM, tuple(sources))
                )
        return found

    def target(self, identifier: str, *, force: bool = False) -> SourceRecord | None:
        """The gene's record. None for an identifier the platform does not hold."""
        if not IDENTIFIER.match(identifier):
            return None
        fetched = self._post(
            API, {"query": TARGET_QUERY, "variables": {"id": identifier}}, force=force
        )
        data = fetched.payload.get("data") if fetched is not None else None
        target = data.get("target") if isinstance(data, dict) else None
        if fetched is None or not isinstance(target, dict) or not target:
            return None
        return SourceRecord(
            source_name=self.name,
            external_id=identifier,
            url=record_url(self.name, identifier) or API,
            payload=target,
            fetched_at=fetched.fetched_at,
        )


def _hits(payload: Any) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else None
    search = data.get("search") if isinstance(data, dict) else None
    hits = search.get("hits") if isinstance(search, dict) else None
    return [hit for hit in hits if isinstance(hit, dict)] if isinstance(hits, list) else []
