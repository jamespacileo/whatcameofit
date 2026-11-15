"""How far a topic is covered: where the link leads that name it stand, and what each
claim for it holds. Behavior: openspec lead-reading, "Topic coverage".

Reads stored data only. It asks no source and changes nothing.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.topics import names_one, terms_of, title_names
from thenwhat.db.models import Claim, ClaimTerm, Entity, EntityMatch, LinkLead, SourceArticle
from thenwhat.domain import EntityType, ReviewState, ScreenOutcome
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.crossref import Crossref
from thenwhat.sources.europepmc import EuropePmc
from thenwhat.sources.openalex import OpenAlex

TRIAL_SOURCES = (ClinicalTrials.name,)
PAPER_SOURCES = (Crossref.name, EuropePmc.name, OpenAlex.name)

# Where a lead that names the topic stands, in the order the report lists them.
NOT_SCREENED = "not screened yet"
UNLISTED = "on an outlet that is not listed"
TRACKED = "already a source article"
NOT_SCORED = "in scope, not scored yet"
REJECTED = "rejected by triage"
TO_READ = "to be read"
STANDINGS = (NOT_SCREENED, UNLISTED, TRACKED, NOT_SCORED, REJECTED, TO_READ)


@dataclass(frozen=True, slots=True)
class TopicClaim:
    slug: str
    intervention: str
    indication: str
    review_state: str
    status: str
    published: bool
    articles: int
    trials: int
    papers: int
    cards: int


@dataclass(frozen=True, slots=True)
class TopicCoverage:
    topic: str
    named: int
    # How many of the leads that name the topic stand where, then how those that were
    # read came out, by the read's own outcome.
    standing: dict[str, int]
    read: dict[str, int]
    claims: list[TopicClaim]


def _standing(
    screen: ScreenOutcome | None,
    score: float | None,
    reject_below: float | None,
) -> str:
    if screen is None:
        return NOT_SCREENED
    if screen is ScreenOutcome.UNLISTED_OUTLET:
        return UNLISTED
    if screen is ScreenOutcome.ALREADY_TRACKED:
        return TRACKED
    if score is None:
        return NOT_SCORED
    if reject_below is not None and score < reject_below:
        return REJECTED
    return TO_READ


def _approved_matches(session: Session, claim_id: int, sources: tuple[str, ...]) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(EntityMatch)
            .join(Entity, Entity.id == EntityMatch.entity_id)
            .where(
                Entity.claim_id == claim_id,
                EntityMatch.source_name.in_(sources),
                EntityMatch.review_state == ReviewState.APPROVED,
            )
        )
        or 0
    )


def coverage(session: Session, topic: str, *, reject_below: float | None) -> TopicCoverage:
    """Where the leads that name the topic stand, and every claim whose intervention
    names it with what that claim holds: articles, approved trials, approved papers and
    approved background cards."""
    terms = terms_of(topic)
    standing = dict.fromkeys(STANDINGS, 0)
    read: dict[str, int] = {}
    named = 0
    condition = title_names(terms)
    assert condition is not None  # a topic always has words
    for screen, score, outcome in session.execute(
        select(LinkLead.screen_outcome, LinkLead.triage_score, LinkLead.read_outcome).where(
            condition
        )
    ):
        named += 1
        if outcome is not None:
            read[outcome.value] = read.get(outcome.value, 0) + 1
        else:
            standing[_standing(screen, score, reject_below)] += 1

    claims: list[TopicClaim] = []
    for claim, name, synonyms in session.execute(
        select(Claim, Entity.name, Entity.synonyms)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(Entity.type == EntityType.INTERVENTION, Claim.archived_at.is_(None))
        .order_by(Claim.slug)
    ):
        if not any(names_one(known, terms) for known in (name, *synonyms)):
            continue
        claims.append(
            TopicClaim(
                slug=claim.slug,
                intervention=name,
                indication=claim.indication,
                review_state=claim.review_state.value,
                status=claim.current_status.value,
                published=claim.published_at is not None,
                articles=session.scalar(
                    select(func.count())
                    .select_from(SourceArticle)
                    .where(SourceArticle.claim_id == claim.id)
                )
                or 0,
                trials=_approved_matches(session, claim.id, TRIAL_SOURCES),
                papers=_approved_matches(session, claim.id, PAPER_SOURCES),
                cards=session.scalar(
                    select(func.count())
                    .select_from(ClaimTerm)
                    .where(
                        ClaimTerm.claim_id == claim.id,
                        ClaimTerm.review_state == ReviewState.APPROVED,
                    )
                )
                or 0,
            )
        )
    return TopicCoverage(topic=topic, named=named, standing=standing, read=read, claims=claims)
