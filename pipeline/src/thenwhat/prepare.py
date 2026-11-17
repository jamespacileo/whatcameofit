"""Deciding a claim that a link lead's read drafted, by the rule for drafts, once it has
been prepared: the step `claim_decide` (`thenwhat.claimsteps.decide`) runs it."""

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
from thenwhat.sources.rxnorm import not_searched


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
    A vaccine filed under its antigen by the source of brands shares nothing either.
    Nor does one named in another form, such as an oral or nasal form of the substance.
    A combination never shares a substance with anything: "bimagrumab plus semaglutide"
    is not semaglutide, whatever single substance its names were filed under.
    """
    if _is_a_combination(session, claim.id):
        return None
    kept = session.execute(
        select(EntitySubstance.external_id, EntitySubstance.source_name, EntitySubstance.payload)
        .join(Entity, Entity.id == EntitySubstance.entity_id)
        .where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).first()
    # A vaccine's antigen is not its identity: two makers' vaccines can share one. Nor
    # is an ingredient whose brand is not yet known to be no vaccine (`not_searched`).
    if kept is None or not_searched(kept.source_name, kept.payload):
        return None
    substance = kept.external_id
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
