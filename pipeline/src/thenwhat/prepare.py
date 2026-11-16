"""Working out what each claim needs before it can be reviewed, and deciding a claim
that a link lead's read drafted once it has been prepared.

Planning: which articles are unread, and the commands to run. Running them is the
command's job.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import (
    _conditions_overlap,
    claim_by_slug,
    find_article,
    find_claim,
    name_key,
)
from thenwhat.db.models import (
    Claim,
    Entity,
    EntityArticle,
    EntitySubstance,
    LinkLead,
    Promise,
    ReportedStatement,
    SourceArticle,
)
from thenwhat.domain import Decider, EntityType, ReadOutcome, ReviewState
from thenwhat.extract.names import is_a_name
from thenwhat.resolve.service import combination_search
from thenwhat.review.decisions import record_decision


@dataclass(frozen=True, slots=True)
class ClaimPlan:
    slug: str
    # Articles the model has not read yet. Only a claim still awaiting review has any:
    # a decided claim is never redrafted.
    unread_articles: list[str]


def plan_claims(session: Session, slugs: list[str] | None) -> list[ClaimPlan]:
    """A plan for each named claim, or for every claim awaiting review when none is named."""
    if slugs is None:
        claims = list(
            session.scalars(
                select(Claim).where(Claim.review_state == ReviewState.PENDING).order_by(Claim.slug)
            )
        )
    else:
        claims = [claim_by_slug(session, slug) for slug in slugs]

    plans: list[ClaimPlan] = []
    for claim in claims:
        unread: list[str] = []
        if claim.review_state is ReviewState.PENDING:
            unread = list(
                session.scalars(
                    select(SourceArticle.url)
                    .where(SourceArticle.claim_id == claim.id, SourceArticle.content_hash.is_(None))
                    .order_by(SourceArticle.published_date, SourceArticle.id)
                )
            )
        plans.append(ClaimPlan(claim.slug, unread))
    return plans


def steps_for(plan: ClaimPlan) -> list[list[str]]:
    """The commands that prepare one claim, in order: read its unread articles, search the
    registries, read the registries for whatever matches are already approved, have the
    stored trial records read into record readings, then propose the claim's subject
    terms, kind and drug record, which its background cards come from."""
    return [
        # An outlet the page reader has stopped is not asked: the article is left for
        # later (`--unless-held`), and the claim's other steps still run.
        *(
            ["extract", "article", plan.slug, "--article-url", url, "--unless-held"]
            for url in plan.unread_articles
        ),
        ["resolve", plan.slug],
        ["fetch", plan.slug],
        ["readings", plan.slug],
        ["terms", plan.slug],
    ]


# A claim's background cards describe its terms and are not evidence: a claim whose
# terms could not be proposed is still decided once the other steps have succeeded.
NOT_NEEDED_TO_DECIDE = {"terms"}


def decide_prepared_lead_claim(session: Session, slug: str, *, now: datetime) -> ReviewState | None:
    """Decide, by the rule for drafts, a claim that a link lead's read drafted and that has
    now been prepared: approved when its intervention is a name, rejected when it is a
    description or when another claim stands for its substance and condition. Returns the
    decision, or None when there is nothing to decide: the claim is not awaiting review,
    or no lead's read drafted it (a claim the operator entered keeps waiting for the
    operator).

    The read leaves such a claim pending so that it is not published before its registries
    have been searched (openspec lead-reading). Call this only after that search succeeded.
    An approved claim is also marked awaiting audit, which keeps it out of every export
    until the audit of its batch clears it.
    """
    claim = find_claim(session, slug)
    if claim is None or claim.review_state is not ReviewState.PENDING:
        return None
    drafted_by_a_read = session.scalar(
        select(LinkLead.id)
        .where(LinkLead.claim_id == claim.id, LinkLead.read_outcome == ReadOutcome.NEW_CLAIM)
        .limit(1)
    )
    if drafted_by_a_read is None:
        return None
    intervention = session.scalar(
        select(Entity.name).where(
            Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION
        )
    )
    twin = claim_sharing_its_substance(session, claim)
    state = (
        ReviewState.APPROVED
        if intervention is not None and is_a_name(intervention) and twin is None
        else ReviewState.REJECTED
    )
    record_decision(claim, state, by=Decider.RULE, now=now)
    if twin is not None:
        join_articles(session, claim, claim_by_slug(session, twin))
    if state is ReviewState.APPROVED:
        claim.awaiting_audit_at = now
    return state


def claim_sharing_its_substance(session: Session, claim: Claim) -> str | None:
    """Slug of another claim, not rejected and not archived, whose intervention the
    registry of substances lists under the same substance as this claim's, for a
    condition that is this claim's or this one narrowed by words in front: Wegovy and
    semaglutide for obesity, BNT162b2 and the Pfizer vaccine for COVID-19 prevention.
    None when this claim's intervention has no substance, or no such claim exists.

    An archived claim does not count, so a claim archived for a fault can be replaced.
    Nor does one named in another form, such as an oral or nasal form of the substance.
    A combination never shares a substance with anything: "bimagrumab plus semaglutide"
    is not semaglutide, whatever single substance its names were filed under.
    """
    if _is_a_combination(session, claim.id):
        return None
    substance = session.scalar(
        select(EntitySubstance.external_id)
        .join(Entity, Entity.id == EntitySubstance.entity_id)
        .where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    )
    if substance is None:
        return None
    others = session.execute(
        select(Claim.slug, Claim.id, Claim.indication)
        .join(Entity, Entity.claim_id == Claim.id)
        .join(EntitySubstance, EntitySubstance.entity_id == Entity.id)
        .where(
            EntitySubstance.external_id == substance,
            Entity.type == EntityType.INTERVENTION,
            Claim.id != claim.id,
            Claim.review_state != ReviewState.REJECTED,
            Claim.archived_at.is_(None),
        )
        .order_by(Claim.id)
    )
    forms = _forms(session, claim)
    for slug, other_id, indication in others:
        if (
            _conditions_overlap(claim.indication, indication)
            and forms == _forms_of(session, other_id)
            and not _is_a_combination(session, other_id)
        ):
            return slug
    return None


def _is_a_combination(session: Session, claim_id: int) -> bool:
    """Whether the claim's intervention names several treatments, by its name or by any
    of its other names."""
    row = session.execute(
        select(Entity.name, Entity.synonyms).where(
            Entity.claim_id == claim_id, Entity.type == EntityType.INTERVENTION
        )
    ).first()
    if row is None:
        return False
    return any(combination_search(name) is not None for name in [row.name, *row.synonyms])


# Words that name a route or a form that makes another product of one substance: oral
# semaglutide and the Wegovy pill are not the injected drug (review of PR 216).
FORM_WORDS = {
    "oral", "pill", "pills", "tablet", "tablets", "capsule", "capsules",
    "nasal", "spray", "inhaled", "inhaler", "patch", "topical", "cream", "gel",
}  # fmt: skip


def _forms_of(session: Session, claim_id: int) -> set[str]:
    name = session.scalar(
        select(Entity.name).where(
            Entity.claim_id == claim_id, Entity.type == EntityType.INTERVENTION
        )
    )
    return {word for word in name_key(name or "").replace("-", " ").split() if word in FORM_WORDS}


def _forms(session: Session, claim: Claim) -> set[str]:
    return _forms_of(session, claim.id)


def join_articles(session: Session, duplicate: Claim, claim: Claim) -> None:
    """Move the articles of a read's claim rejected as a duplicate to the claim that
    stands for its substance and condition, with what was read from them, so no article
    is lost. A lead that drafted the duplicate is recorded as added to that claim. An
    article the claim already has stays with the duplicate, and its lead points at the
    claim's own copy."""
    for article in session.scalars(
        select(SourceArticle).where(SourceArticle.claim_id == duplicate.id)
    ):
        kept = find_article(session, claim, article.url)
        if kept is None:
            article.claim_id = claim.id
            for table in (Promise, ReportedStatement):
                for row in session.scalars(
                    select(table).where(table.source_article_id == article.id)
                ):
                    row.claim_id = claim.id
            for link in session.scalars(
                select(EntityArticle).where(EntityArticle.source_article_id == article.id)
            ):
                session.delete(link)
            if (
                claim.first_reported_date is None
                or article.published_date < claim.first_reported_date
            ):
                claim.first_reported_date = article.published_date
            kept = article
        for lead in session.scalars(
            select(LinkLead).where(LinkLead.source_article_id == article.id)
        ):
            lead.claim_id, lead.source_article_id = claim.id, kept.id
            lead.read_outcome = ReadOutcome.ADDED_TO_CLAIM
            lead.read_detail = (
                f"joined {claim.slug} after the registry search: the same substance,"
                f" form and condition (the draft {duplicate.slug} was rejected by rule)"
            )
    session.flush()
