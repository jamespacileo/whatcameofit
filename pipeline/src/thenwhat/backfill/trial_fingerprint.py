"""Search terms derived from one stored trial. Behavior: openspec trial-coverage."""

from collections.abc import Mapping, Set
from dataclasses import dataclass
from typing import Any

from thenwhat.backfill.trial_terms import codes_of, other_names_of, words_of
from thenwhat.sources.people import sponsored_by_a_person

Words = tuple[str, ...]

# Names and ordinary phrases seen as acronyms that the pilot's word lists omit.
AMBIGUOUS_ACRONYMS = frozenset(
    {("cupido",), ("megan",), ("nursingcare",), ("osaka",), ("tomeka",), ("volga",)}
)


@dataclass(frozen=True, slots=True)
class Term:
    kind: str
    value: str
    fit: bool
    reason: str | None = None
    identifier_type: str | None = None


@dataclass(frozen=True, slots=True)
class AcronymContext:
    word_list: Set[Words]
    condition_terms: Set[Words]
    other_titles: Mapping[Words, int]
    max_other_titles: int


def acronym_rejection(acronym: str, context: AcronymContext) -> str | None:
    words = words_of(acronym)
    # Keep short initials eligible. A dictionary otherwise mistakes parts like EM
    # and MAT for the words of an ordinary phrase.
    ordinary_phrase = len(words) > 1 and all(
        len(word) >= 4 and word.isalpha() and (word,) in context.word_list for word in words
    )
    if words in context.word_list or words in AMBIGUOUS_ACRONYMS or ordinary_phrase:
        return "word_or_name"
    if words in context.condition_terms:
        return "condition_term"
    letters = sum(character.isalpha() for word in words for character in word)
    marked = "-" in acronym or any(character.isdigit() for word in words for character in word)
    if letters < 5 and (letters < 3 or not marked):
        return "too_short"
    if context.other_titles.get(words, 0) > context.max_other_titles:
        return "too_many_other_titles"
    return None


def fingerprint_of(
    registry_number: str,
    *,
    interventions: list[dict[str, Any]],
    protocol: dict[str, Any],
    lead_sponsor_name: str | None,
    context: AcronymContext,
    telling_names: Set[Words] = frozenset(),
) -> list[Term]:
    """Keep all the identifying terms, with the only ones fit to send marked.

    Telling substance names need the separate registry and headline-frequency checks.
    Use those results when available. A name held by this trial alone is not evidence.
    """
    identification = protocol.get("identificationModule", {})
    terms = [Term("registry_number", registry_number, True)]
    org_id = identification.get("orgStudyIdInfo", {}).get("id")
    if org_id:
        terms.append(Term("sponsor_identifier", org_id, False))
    for secondary in identification.get("secondaryIdInfos", []):
        if secondary.get("id"):
            terms.append(
                Term(
                    "secondary_identifier",
                    secondary["id"],
                    False,
                    identifier_type=secondary.get("type"),
                )
            )
    acronym = identification.get("acronym")
    if acronym:
        reason = acronym_rejection(acronym, context)
        terms.append(Term("acronym", acronym, reason is None, reason))
    terms.extend(Term("development_code", code, True) for code in codes_of(interventions))
    if telling_names:
        products = [item for item in interventions if item.get("type") in ("DRUG", "BIOLOGICAL")]
        terms.extend(
            Term("telling_name", name, True)
            for name in other_names_of(products, None)
            if words_of(name) in telling_names
        )
    sponsors = protocol.get("sponsorCollaboratorsModule", {})
    if lead_sponsor_name and not sponsored_by_a_person(sponsors):
        terms.append(Term("lead_sponsor", lead_sponsor_name, False))
    return list(dict.fromkeys(terms))
