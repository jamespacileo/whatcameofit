"""Search phrases for a claim that is already decided. Behavior: openspec related-research.

A decided claim's article is never read again, so its intervention has search phrases
only if someone gives them. Here the model gives them from what the claim already says
of itself: its headline, summary, intervention and indication, all in our own words.
No article is fetched and no article text is shown to the model.
"""

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.claims.entry import name_key, tidy
from thenwhat.db.models import Claim, Entity
from thenwhat.domain import EntityType
from thenwhat.extract.names import is_a_search_phrase
from thenwhat.extract.schema import MAX_SEARCH_PHRASES, ShortText
from thenwhat.llm.client import Llm

INSTRUCTIONS = """\
You are given one tracked medical research claim: its headline, a summary, the
intervention as recorded, any other names, and the condition.
Give up to three short phrases a clinical trial registry or a paper would use for this
intervention, most specific first. Use them when the intervention is recorded as a
description, or under a name a registry would not file it under.
Give none when the recorded names are what a registry would use, such as a drug's
generic name or a development code.
Never give a bare word for a kind of thing, such as 'the device', and never the
condition alone.
"""


class Phrases(BaseModel):
    search_phrases: list[ShortText] = Field(
        default_factory=list,
        max_length=MAX_SEARCH_PHRASES,
        description="Up to three registry-style phrases for the intervention, or none.",
    )


def needs_phrases(session: Session, claim: Claim) -> Entity | None:
    """The claim's intervention when it has no search phrase yet, else None."""
    for entity in entities_of(session, claim):
        if entity.type is EntityType.INTERVENTION:
            return None if entity.search_phrases else entity
    return None


def backfill_search_phrases(session: Session, llm: Llm, claim: Claim) -> list[str]:
    """Ask the model for the claim's search phrases and store those that say which
    treatment. Returns what was stored; nothing when the intervention already has
    phrases or the model gives none worth keeping."""
    intervention = needs_phrases(session, claim)
    if intervention is None:
        return []
    also = f"\nOther names: {', '.join(intervention.synonyms)}" if intervention.synonyms else ""
    prompt = (
        f"Headline: {claim.headline}\nSummary: {claim.summary or 'none'}\n"
        f"Intervention: {intervention.name}{also}\nCondition: {claim.indication}"
    )
    answer = llm.run(
        "search-phrases", instructions=INSTRUCTIONS, prompt=prompt, output_type=Phrases
    )
    taken = {
        name_key(intervention.name),
        name_key(claim.indication),
        *(name_key(name) for name in intervention.synonyms),
    }
    kept: list[str] = []
    for phrase in answer.search_phrases:
        phrase = tidy(phrase)
        if is_a_search_phrase(phrase) and name_key(phrase) not in taken:
            taken.add(name_key(phrase))
            kept.append(phrase)
    if kept:
        intervention.search_phrases = kept[:MAX_SEARCH_PHRASES]
        session.flush()
    return kept[:MAX_SEARCH_PHRASES]
