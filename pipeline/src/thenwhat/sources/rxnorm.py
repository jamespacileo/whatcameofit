"""RxNorm, the U.S. National Library of Medicine's vocabulary of drug names, read
through its RxNav REST API. Terms and limits: docs/sources.md. Behavior: openspec
source-clients, "A brand is looked up by its exact name".

A report often names a vaccine, a gene therapy or another biologic by its brand, and
the registry of substances (GSRS) does not list every brand. RxNorm files each brand it
knows under the ingredients it is made of. Nothing here guesses: a brand is found only
under a name RxNorm gives a brand concept, letter for letter, and its ingredients are
the ones RxNorm relates to that concept.

For a vaccine RxNorm's ingredient is the antigen, not the product: Ervebo's is "Zaire
ebolavirus envelope glycoprotein". Another maker's vaccine can be made of the same
antigen, so the antigen is no name for the product. RxNorm marks a vaccine by giving its
branded drugs a code from CDC's vaccine code set (CVX), and that code is read for every
brand of one ingredient. The ingredient is still kept, with the codes, as what the
source said; whoever searches decides not to search a vaccine's antigen.
"""

from datetime import datetime, timedelta
from typing import Any

from thenwhat.sources.base import Source, SourceRecord

API = "https://rxnav.nlm.nih.gov/REST"
# Where a reader can open a concept's record.
PAGE = "https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm={}"
# RxNorm's term types for a brand name and for an ingredient.
BRAND = "BN"
INGREDIENT = "IN"
# The term type of a branded drug: a brand in one strength and form.
BRANDED_DRUG = "SBD"
# The property that holds a branded drug's code in CDC's vaccine code set.
VACCINE_CODE = "CVX"
# How many of a brand's branded drugs are asked for a vaccine code. RxNorm gives the
# code to each of a vaccine's branded drugs, so the first few say it.
MAX_PRODUCTS = 5
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


def _branded_drugs(related: Any) -> list[str]:
    """The identifiers of the branded drugs in an answer to "what is related to this
    concept", lowest first."""
    groups = (related.get("relatedGroup") or {}).get("conceptGroup") or []
    found = {
        concept["rxcui"]
        for group in groups
        if isinstance(group, dict) and group.get("tty") == BRANDED_DRUG
        for concept in group.get("conceptProperties") or []
        if isinstance(concept, dict)
        and isinstance(concept.get("rxcui"), str)
        and concept["rxcui"].isdigit()
    }
    return sorted(found, key=int)


def _codes_in(answer: Any) -> list[str]:
    """The values of a property in an answer to "this concept's property"."""
    concepts = (answer.get("propConceptGroup") or {}).get("propConcept") or []
    return [
        concept["propValue"]
        for concept in concepts
        if isinstance(concept, dict)
        and concept.get("propName") == VACCINE_CODE
        and isinstance(concept.get("propValue"), str)
        and concept["propValue"].strip()
    ]


def vaccine_codes(payload: Any) -> list[str]:
    """The CVX codes RxNorm gives the branded drugs of the brand a record was found
    under: the brand is a vaccine, and its ingredient an antigen, when there are any.
    Empty for a record from another source, or kept before the codes were read."""
    if not isinstance(payload, dict):
        return []
    answers = payload.get("product_codes")
    if not isinstance(answers, dict):
        return []
    found = [
        code
        for answer in answers.values()
        if isinstance(answer, dict)
        for code in _codes_in(answer)
    ]
    return sorted(set(found))


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
            ingredients = _concepts(related.payload)
            # A brand of several ingredients identifies none, so it is asked no more.
            fetched_at = related.fetched_at
            products: dict[str, Any] = {}
            if len(ingredients) == 1:
                asked_more = self._products(identifier)
                if asked_more is None:
                    return []
                products, fetched_at = asked_more
            for ingredient in ingredients:
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
                            **products,
                        },
                        fetched_at=fetched_at,
                    ),
                )
        return list(records.values())

    def _products(self, brand: str) -> tuple[dict[str, Any], datetime] | None:
        """The brand's branded drugs, and the vaccine code each of the first
        `MAX_PRODUCTS` carries, as fetched, with the time of the last answer. None when
        an answer is missing: without them a vaccine could not be told from a drug."""
        drugs = self._get(f"{API}/rxcui/{brand}/related.json", {"tty": BRANDED_DRUG}, ttl=KEPT_FOR)
        if drugs is None or not isinstance(drugs.payload, dict):
            return None
        codes: dict[str, Any] = {}
        fetched_at = drugs.fetched_at
        for drug in _branded_drugs(drugs.payload)[:MAX_PRODUCTS]:
            answer = self._get(
                f"{API}/rxcui/{drug}/property.json", {"propName": VACCINE_CODE}, ttl=KEPT_FOR
            )
            if answer is None or not isinstance(answer.payload, dict):
                return None
            codes[drug], fetched_at = answer.payload, answer.fetched_at
        return {"products": drugs.payload, "product_codes": codes}, fetched_at
