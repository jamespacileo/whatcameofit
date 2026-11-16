"""RxNorm, the U.S. National Library of Medicine's vocabulary of drug names, read
through its RxNav REST API. Terms and limits: docs/sources.md. Behavior: openspec
source-clients, "A brand is looked up by its exact name".

A report often names a vaccine, a gene therapy or another biologic by its brand, and
the registry of substances (GSRS) does not list every brand. RxNorm files each brand it
knows under the ingredients it is made of. Nothing here guesses: a brand is found only
under a name RxNorm gives a brand concept, letter for letter, and its ingredients are
the ones RxNorm relates to that concept.
"""

from datetime import timedelta
from typing import Any

from thenwhat.sources.base import Source, SourceRecord

API = "https://rxnav.nlm.nih.gov/REST"
# Where a reader can open a concept's record.
PAGE = "https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm={}"
# RxNorm's term types for a brand name and for an ingredient.
BRAND = "BN"
INGREDIENT = "IN"
# A name that more concepts than this carry identifies none, and none is read.
MAX_CONCEPTS = 5
# A brand's ingredients change rarely. NLM recommends keeping answers 12 to 24 hours at
# least; the vocabulary itself is released monthly.
KEPT_FOR = timedelta(days=30)


def _key(name: str) -> str:
    return " ".join(name.split()).casefold()


def _concepts(related: Any) -> list[dict[str, Any]]:
    """The ingredient concepts in an answer to "what is related to this concept"."""
    groups = (related.get("relatedGroup") or {}).get("conceptGroup") or []
    return [
        concept
        for group in groups
        if isinstance(group, dict) and group.get("tty") == INGREDIENT
        for concept in group.get("conceptProperties") or []
        if isinstance(concept, dict)
        and isinstance(concept.get("rxcui"), str)
        and isinstance(concept.get("name"), str)
        and concept["name"].strip()
    ]


def _brand(record: dict[str, Any], asked: str) -> dict[str, Any] | None:
    """The concept's own record, when it is a brand whose name is the name asked."""
    properties = record.get("properties")
    if not isinstance(properties, dict) or properties.get("tty") != BRAND:
        return None
    listed = properties.get("name")
    if not isinstance(listed, str) or _key(listed) != _key(asked):
        return None
    return properties


class RxNorm(Source):
    name = "rxnorm"
    # NLM allows 20 requests a second from one address. Two is ample for a fallback.
    default_rate_per_second = 2.0
    # Optional enrichment, as GSRS is: a stalled source must not occupy minutes of prepare.
    default_max_attempts = 2
    request_timeout = 5.0

    def substances_named(self, name: str) -> list[SourceRecord]:
        """Every ingredient RxNorm lists for the brand of exactly this name, whatever
        its case and spacing. Empty when RxNorm has no brand of that name.

        One record is returned for each ingredient, so a brand of two ingredients is
        two substances and identifies neither. Each record holds the ingredient in the
        short form a substance record has (`substance`, with its name as `_name`), and
        the brand's record and the answer listing its ingredients as fetched.

        Only a brand is resolved. A name RxNorm gives an ingredient, a dose form or a
        pack finds nothing here: an ingredient's own name is the substance registry's
        to answer.

        The answer is whole or it is nothing. A name more than `MAX_CONCEPTS` concepts
        carry finds nothing, and so does a brand when a concept's own record or its
        list of ingredients is missing: part of an answer could show one ingredient
        where the brand has two.
        """
        asked = " ".join(name.split())
        if not asked:
            return []
        found = self._get(f"{API}/rxcui.json", {"name": asked, "search": "0"}, ttl=KEPT_FOR)
        if found is None or not isinstance(found.payload, dict):
            return []
        identifiers = (found.payload.get("idGroup") or {}).get("rxnormId") or []
        if len(identifiers) > MAX_CONCEPTS:
            return []
        records: dict[str, SourceRecord] = {}
        for identifier in identifiers:
            if not isinstance(identifier, str) or not identifier.isdigit():
                return []
            fetched = self._get(f"{API}/rxcui/{identifier}/properties.json", ttl=KEPT_FOR)
            if fetched is None or not isinstance(fetched.payload, dict):
                return []
            brand = _brand(fetched.payload, asked)
            if brand is None:
                continue
            related = self._get(
                f"{API}/rxcui/{identifier}/related.json", {"tty": INGREDIENT}, ttl=KEPT_FOR
            )
            if related is None or not isinstance(related.payload, dict):
                return []
            for ingredient in _concepts(related.payload):
                records.setdefault(
                    ingredient["rxcui"],
                    SourceRecord(
                        source_name=self.name,
                        external_id=ingredient["rxcui"],
                        url=PAGE.format(ingredient["rxcui"]),
                        payload={
                            "substance": ingredient | {"_name": ingredient["name"]},
                            "brand": brand,
                            "ingredients": related.payload,
                        },
                        fetched_at=related.fetched_at,
                    ),
                )
        return list(records.values())
