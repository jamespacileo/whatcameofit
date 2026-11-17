"""Setting a claim's approach by rule from the registry's intervention types.
Behavior: openspec health-areas, "Approach set by rule from registry intervention types".

The registry gives every intervention of a trial one type. When the claim's approved
trials list its intervention, by an equal name, under exactly one type, and the table
below maps that type, the claim gets that approach. No model is asked, and nothing else
fills an approach the rule leaves empty.

A rule only fills an empty approach or replaces one a rule set. One set by a person, the
seed or an assistant is never touched, nor one stored before who set it was recorded.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.mesh_areas import approved_trial_payloads
from thenwhat.db.models import Claim, Entity
from thenwhat.domain import Decider, EntityType
from thenwhat.terms.kinds import REGISTRY_LISTS_TYPE, registry_types

# Registry intervention type to approach. A type is listed only when it names one
# approach: BIOLOGICAL covers vaccines, cell therapies and antibodies; BEHAVIORAL covers
# talking therapies as well as habits; RADIATION, COMBINATION_PRODUCT, DIAGNOSTIC_TEST
# and OTHER have no approach of their own.
TYPE_APPROACHES: dict[str, str] = {
    "DRUG": "drug",
    "DEVICE": "device",
    "PROCEDURE": "surgery-or-procedure",
    "GENETIC": "gene-therapy",
    "DIETARY_SUPPLEMENT": "diet-or-lifestyle",
}

# Why the rule set no approach.
NOT_LISTED = "not_listed"
TYPES_DISAGREE = "types_disagree"
TYPE_NOT_MAPPED = "type_not_mapped"


@dataclass(frozen=True, slots=True)
class RuleAnswer:
    approach: str | None
    # The reason `registry_types` gave for the one type, when the rule answers.
    basis: dict[str, Any] | None
    # Why there is no approach, or None when there is one.
    reason: str | None
    # Every type found with its trial count, most trials first.
    types: tuple[tuple[str, int], ...]


def approach_from_registry(types: Sequence[Mapping[str, Any]]) -> RuleAnswer:
    """The approach the registry's types give, from the output of `registry_types`.
    Pure: the same types always give the same answer."""
    found = tuple((str(entry["type"]), int(entry["trials"])) for entry in types)
    if not found:
        return RuleAnswer(None, None, NOT_LISTED, found)
    if len(found) > 1:
        return RuleAnswer(None, None, TYPES_DISAGREE, found)
    kind, trials = found[0]
    approach = TYPE_APPROACHES.get(kind)
    if approach is None:
        return RuleAnswer(None, None, TYPE_NOT_MAPPED, found)
    basis = {"code": REGISTRY_LISTS_TYPE, "type": kind, "trials": trials}
    return RuleAnswer(approach, basis, None, found)


def _names(session: Session, claim: Claim) -> list[str]:
    names: list[str] = []
    for name, synonyms in session.execute(
        select(Entity.name, Entity.synonyms).where(
            Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION
        )
    ):
        names += [name, *synonyms]
    return names


def answer_for(session: Session, claim: Claim) -> RuleAnswer:
    """What the rule answers for the claim now, from its approved trials. Changes nothing."""
    return approach_from_registry(
        registry_types(approved_trial_payloads(session, claim), _names(session, claim))
    )


def is_the_rules(claim: Claim) -> bool:
    """Whether the rule may write the claim's approach: it is empty, or a rule set it."""
    return claim.approach is None or claim.approach_decided_by is Decider.RULE


def apply_rule(session: Session, claim: Claim) -> RuleAnswer:
    """Set, update or clear the claim's approach by rule, and return the rule's answer.
    An approach the rule did not set is left as it is."""
    answer = answer_for(session, claim)
    if is_the_rules(claim):
        claim.approach = answer.approach
        claim.approach_decided_by = Decider.RULE if answer.approach else None
        claim.approach_basis = answer.basis
    return answer
