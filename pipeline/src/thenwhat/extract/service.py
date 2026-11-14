"""Drafting a claim from the text of a news article. Behavior: openspec claim-extraction.

The text is passed in, shown to the model, hashed and dropped. Nothing here
stores, caches or logs it.
"""

import hashlib
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import (
    ArticleNotFound,
    EntryError,
    add_article,
    add_claim,
    add_promise,
    check_new_claim,
    claim_by_slug,
    find_article,
    name_key,
    promises_of,
)
from thenwhat.db.models import Claim, Entity, SourceArticle
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.extract.names import is_a_name, is_a_search_phrase
from thenwhat.extract.schema import MAX_SEARCH_PHRASES, Draft
from thenwhat.llm.client import Llm
from thenwhat.review.decisions import record_decision

INSTRUCTIONS = """\
You read one news article about a medical research claim and return structured fields.
Report only what the article says. Do not add facts, and do not judge the claim.
Write the headline and summary in your own neutral words; never copy sentences from the article.
Keep the summary under 500 characters.
When the article gives the treatment no product name, give up to three search phrases:
the words a trial registry or a paper would use for it.
Give a DOI only if the article states it. List a promised timeline only if the article states one.
"""


class ClaimNotPending(EntryError):
    pass


def draft_claim_from_article(
    session: Session,
    llm: Llm,
    *,
    text: str,
    slug: str,
    vertical: str,
    url: str,
    outlet: str,
    title: str,
    published_date: date,
    archive_url: str | None = None,
    decide_by_rule_at: datetime | None = None,
) -> Claim:
    """Create a pending claim, with its article, entities and promises, from article text.

    Nothing is saved if the model's output never validates or an entry rule refuses it.
    With `decide_by_rule_at`, the draft is decided by rule at that time (openspec
    auto-publish): approved when the intervention it names is a name, else rejected and
    kept for the operator, since a description would be searched for as if it were one.
    """
    check_new_claim(session, slug, vertical)
    draft = _extract(llm, text)
    with session.begin_nested():
        claim = add_claim(
            session,
            slug=slug,
            headline=draft.headline,
            vertical=vertical,
            intervention=draft.intervention,
            indication=draft.indication,
            summary=draft.summary,
        )
        article = add_article(
            session, slug, url=url, outlet=outlet, title=title, published_date=published_date
        )
        _apply(session, claim, article, draft, text, archive_url)
        if decide_by_rule_at is not None:
            state = ReviewState.APPROVED if is_a_name(draft.intervention) else ReviewState.REJECTED
            record_decision(claim, state, by=Decider.RULE, now=decide_by_rule_at)
    return claim


def extract_into_claim(
    session: Session,
    llm: Llm,
    *,
    claim_slug: str,
    article_url: str,
    text: str,
    archive_url: str | None = None,
) -> Claim:
    """Add what an article says to a claim that is still pending.

    What the operator already entered is kept: the headline always, the summary if set.
    """
    claim = claim_by_slug(session, claim_slug)
    if claim.review_state is not ReviewState.PENDING:
        raise ClaimNotPending(
            f"Claim '{claim_slug}' has already been reviewed. Add to it by hand instead."
        )
    article = find_article(session, claim, article_url)
    if article is None:
        raise ArticleNotFound(f"Claim '{claim_slug}' has no article {article_url}.")

    draft = _extract(llm, text)
    if not claim.summary:
        claim.summary = draft.summary
    _apply(session, claim, article, draft, text, archive_url)
    return claim


def _extract(llm: Llm, text: str) -> Draft:
    return llm.run("extraction", instructions=INSTRUCTIONS, prompt=text, output_type=Draft)


def _apply(
    session: Session,
    claim: Claim,
    article: SourceArticle,
    draft: Draft,
    text: str,
    archive_url: str | None,
) -> None:
    """Record the draft's entities and promises on the claim, skipping what it already has."""
    article.content_hash = hashlib.sha256(text.encode()).hexdigest()
    if archive_url:
        article.archive_url = archive_url

    existing = list(session.scalars(select(Entity).where(Entity.claim_id == claim.id)))
    known = {(entity.type, name_key(entity.name)) for entity in existing}

    intervention = next(e for e in existing if e.type is EntityType.INTERVENTION)
    names = {name_key(intervention.name), *(name_key(s) for s in intervention.synonyms)}
    # A description the model returned as a name is dropped: it would be searched for.
    new_synonyms = [
        s for s in draft.intervention_synonyms if is_a_name(s) and name_key(s) not in names
    ]
    if new_synonyms:
        intervention.synonyms = [*intervention.synonyms, *new_synonyms]
    # A phrase is kept apart from the names: it is searched for, never shown as one.
    phrases = list(intervention.search_phrases)
    for phrase in draft.intervention_search_phrases:
        taken = names | {name_key(p) for p in phrases}
        if is_a_search_phrase(phrase) and name_key(phrase) not in taken:
            phrases.append(phrase)
    if phrases != intervention.search_phrases:
        intervention.search_phrases = phrases[:MAX_SEARCH_PHRASES]

    paper_name = draft.paper_title or draft.paper_doi
    known_dois = {entity.doi.lower() for entity in existing if entity.doi}
    paper_is_new = (EntityType.PAPER, name_key(paper_name or "")) not in known and (
        draft.paper_doi is None or draft.paper_doi.lower() not in known_dois
    )
    if paper_name and paper_is_new:
        session.add(
            Entity(
                claim_id=claim.id,
                type=EntityType.PAPER,
                name=paper_name,
                doi=draft.paper_doi,
                is_origin_paper=not any(entity.is_origin_paper for entity in existing),
            )
        )

    for named in draft.entities:
        entity_type = EntityType(named.type)
        if (entity_type, name_key(named.name)) not in known:
            known.add((entity_type, name_key(named.name)))
            session.add(Entity(claim_id=claim.id, type=entity_type, name=named.name))

    promised = {
        name_key(promise.description)
        for promise in promises_of(session, claim)
        if promise.source_article_id == article.id
    }
    for description in draft.promises:
        if name_key(description) not in promised:
            promised.add(name_key(description))
            add_promise(session, claim.slug, article_url=article.url, description=description)
    session.flush()
