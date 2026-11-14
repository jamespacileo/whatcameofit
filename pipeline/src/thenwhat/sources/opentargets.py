"""Open Targets Platform: human genes by symbol, and a gene's record. Terms and limits:
docs/sources.md. Behavior: openspec source-clients, "A gene is looked up by symbol".

Targets, and a drug by its own name with its kind of molecule and mechanisms. Those drug
facts are drawn from ChEMBL under a share-alike licence, accepted for claim pages and
kept out of the data file (docs/adr/0002). No phase, approval, indication, synonym or
trade name is asked for.
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

# A ChEMBL identifier, which is how the platform names a drug.
DRUG_IDENTIFIER = re.compile(r"^CHEMBL\d+$")
_DRUG_FIELDS = (
    "id name drugType mechanismsOfAction { rows { mechanismOfAction actionType targetName"
    " targets { id approvedSymbol approvedName biotype functionDescriptions } } }"
)
DRUG_SEARCH_QUERY = (
    "query DrugsNamed($name: String!) { search(queryString: $name, entityNames:"
    f' ["drug"], page: {{index: 0, size: {MAX_HITS}}}) {{ hits {{ id entity object {{'
    f" ... on Drug {{ {_DRUG_FIELDS} }} }} }} }} }}"
)
DRUG_QUERY = f"query Drug($id: String!) {{ drug(chemblId: $id) {{ {_DRUG_FIELDS} }} }}"
PROTEIN_CODING = "protein_coding"

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


@dataclass(frozen=True, slots=True)
class Mechanism:
    # What the drug does to its target, as a code: "agonist", "binding_agent".
    action: str
    # The target's name as the source writes it.
    target_name: str
    # The human genes whose products make up the target. Empty when it is not one.
    targets: tuple[Target, ...]


@dataclass(frozen=True, slots=True)
class Drug:
    identifier: str
    # The source's own name for the drug, as it writes it.
    name: str
    # The kind of molecule, as a code: "small_molecule", "protein". None when not given.
    molecule_kind: str | None
    mechanisms: tuple[Mechanism, ...]


def _code(value: Any) -> str:
    """A source's label as a code the site can word: "Small molecule" is
    "small_molecule"."""
    return "_".join(re.findall(r"[a-z0-9]+", _text(value).lower()))


def describe_drug(record: SourceRecord) -> Drug:
    """The parts of a stored drug record that the pipeline uses. Nothing about how far
    the drug has got is read, because nothing about it is stored."""
    drug = record.payload
    listed = drug.get("mechanismsOfAction")
    rows = listed.get("rows") if isinstance(listed, dict) else None
    mechanisms: list[Mechanism] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        action, target_name = _code(row.get("actionType")), _text(row.get("targetName"))
        if not action or not target_name:
            continue
        genes = row.get("targets")
        mechanisms.append(
            Mechanism(
                action,
                target_name,
                tuple(_read(gene) for gene in (genes if isinstance(genes, list) else [])),
            )
        )
    return Drug(
        identifier=record.external_id,
        name=_text(drug.get("name")),
        molecule_kind=_code(drug.get("drugType")) or None,
        mechanisms=tuple(mechanisms),
    )


def single_protein_target(drug: Drug) -> Target | None:
    """The one human protein the drug's record names as its target, or None.

    Every mechanism must name exactly one protein-coding gene, and all of them the same
    one. A drug with two targets, with a target that is a complex of several proteins,
    with a target that is not a human gene product, or with no mechanism has none.
    """
    found: dict[str, Target] = {}
    for mechanism in drug.mechanisms:
        if len(mechanism.targets) != 1 or mechanism.targets[0].biotype != PROTEIN_CODING:
            return None
        found[mechanism.targets[0].identifier] = mechanism.targets[0]
    if len(found) != 1:
        return None
    [target] = found.values()
    return target if IDENTIFIER.match(target.identifier) and target.symbol else None


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

    def drugs_named(self, name: str) -> list[SourceRecord]:
        """The drugs whose own name equals the given name, whatever its case, each with
        its record. The platform's search also answers salts of the drug and other
        drugs of its class; those are never returned, and a drug's other names and
        trade names are not compared."""
        name = " ".join(name.split())
        if not name:
            return []
        fetched = self._post(
            API, {"query": DRUG_SEARCH_QUERY, "variables": {"name": name}}, ttl=SEARCH_KEPT
        )
        if fetched is None:
            return []
        found: list[SourceRecord] = []
        for hit in _hits(fetched.payload):
            drug = hit.get("object")
            if hit.get("entity") != "drug" or not isinstance(drug, dict):
                continue
            identifier, own = _text(drug.get("id")), " ".join(_text(drug.get("name")).split())
            if DRUG_IDENTIFIER.match(identifier) and own.casefold() == name.casefold():
                found.append(self._drug_record(identifier, drug, fetched.fetched_at))
        return found

    def drug(self, identifier: str, *, force: bool = False) -> SourceRecord | None:
        """The drug's record. None for an identifier the platform does not hold."""
        if not DRUG_IDENTIFIER.match(identifier):
            return None
        fetched = self._post(
            API, {"query": DRUG_QUERY, "variables": {"id": identifier}}, force=force
        )
        data = fetched.payload.get("data") if fetched is not None else None
        drug = data.get("drug") if isinstance(data, dict) else None
        if fetched is None or not isinstance(drug, dict) or not drug:
            return None
        return self._drug_record(identifier, drug, fetched.fetched_at)

    def _drug_record(self, identifier: str, drug: dict[str, Any], fetched_at: Any) -> SourceRecord:
        return SourceRecord(
            source_name=self.name,
            external_id=identifier,
            url=record_url(self.name, identifier) or API,
            payload=drug,
            fetched_at=fetched_at,
        )


def _hits(payload: Any) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else None
    search = data.get("search") if isinstance(data, dict) else None
    hits = search.get("hits") if isinstance(search, dict) else None
    return [hit for hit in hits if isinstance(hit, dict)] if isinstance(hits, list) else []
