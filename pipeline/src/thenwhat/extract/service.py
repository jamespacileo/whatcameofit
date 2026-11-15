"""Drafting a claim from the text of a news article. Behavior: openspec claim-extraction.

The text is passed in, shown to the model, hashed and dropped. Nothing here
stores, caches or logs it. While it is in memory, the reported statements the model
proposes are checked against it (openspec reported-statements).
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import (
    ORGANISATION_TYPES,
    note_named_organisation,
    whole_intervention_names,
)
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
from thenwhat.statements.service import (
    StatementChecker,
    StatementsRun,
    keep_statements,
    statement_rules,
)

INSTRUCTIONS = """\
You read one news article about a medical research claim and return structured fields.
Report only what the article says. Do not add facts, and do not judge the claim.
Write the headline and summary in your own neutral words; never copy sentences from the article.
Keep the summary under 500 characters.
When the article gives the treatment no product name, give up to three search phrases:
the words a trial registry or a paper would use for it.
Record a person only when the article names them as carrying out or leading the research.
Never record a patient, a relative, a reporter or a commentator, by full name or by first name.
Record an institution or company only for a university, hospital, research institute, company,
funder or public body. A journal, a news outlet, a bank or an investment analyst is none of these.
Give a DOI only if the article states it. List a promised timeline only if the article states one.
"""


# The name an article's read is recorded under in the usage ledger.
EXTRACTION = "extraction"


class ClaimNotPending(EntryError):
    pass


@dataclass(frozen=True, slots=True)
class Extracted:
    """A claim drafted or added to from an article, and what became of the article's
    reported statements."""

    claim: Claim
    statements: StatementsRun


def draft_claim_from_article(
    session: Session,
    llm: Llm,
    checker: StatementChecker,
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
    now: datetime | None = None,
) -> Extracted:
    """Create a pending claim, with its article, entities, promises and reported
    statements, from article text.

    Nothing is saved if the model's output never validates or an entry rule refuses it.
    A statement the check cannot answer for is not stored; the claim still is.
    With `decide_by_rule_at`, the draft is decided by rule at that time (openspec
    auto-publish): approved when the intervention it names is a name, else rejected and
    kept for the operator, since a description would be searched for as if it were one.
    """
    check_new_claim(session, slug, vertical)
    return claim_from_draft(
        session,
        checker,
        read_article(llm, checker, text),
        text=text,
        slug=slug,
        vertical=vertical,
        url=url,
        outlet=outlet,
        title=title,
        published_date=published_date,
        archive_url=archive_url,
        decide_by_rule_at=decide_by_rule_at,
        now=now,
    )


def read_article(
    llm: Llm, checker: StatementChecker, text: str, *, purpose: str = EXTRACTION
) -> Draft:
    """What the model reads out of an article's text: the one model call of extraction.
    Nothing is saved, and the text is kept nowhere. `purpose` is the name the call's
    cost is recorded under."""
    return _extract(llm, text, checker, purpose)


def claim_from_draft(
    session: Session,
    checker: StatementChecker,
    draft: Draft,
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
    now: datetime | None = None,
) -> Extracted:
    """Create a claim from an article that has been read: the claim, its article, its
    entities, promises and reported statements, decided by rule when asked. Nothing is
    saved if an entry rule refuses it."""
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
        statements = keep_statements(
            session,
            checker,
            article=article,
            text=text,
            proposed=draft.statements,
            now=now or datetime.now(UTC),
        )
    return Extracted(claim, statements)


def article_from_draft(
    session: Session,
    checker: StatementChecker,
    claim: Claim,
    draft: Draft,
    *,
    text: str,
    url: str,
    outlet: str,
    title: str,
    published_date: date,
    archive_url: str | None = None,
    now: datetime | None = None,
) -> tuple[SourceArticle, StatementsRun]:
    """Add an article that has been read to a claim that exists: its reference, the hash
    of its text, any archive address and its reported statements, which are checked and
    approved by their own rule. Nothing else of the claim is changed, whatever its review
    state: not its headline, summary, names, entities or promises. Its first reported
    date moves when the article is earlier, as for any article added."""
    with session.begin_nested():
        article = add_article(
            session, claim.slug, url=url, outlet=outlet, title=title, published_date=published_date
        )
        article.content_hash = hashlib.sha256(text.encode()).hexdigest()
        if archive_url:
            article.archive_url = archive_url
        statements = keep_statements(
            session,
            checker,
            article=article,
            text=text,
            proposed=draft.statements,
            now=now or datetime.now(UTC),
        )
    return article, statements


def extract_into_claim(
    session: Session,
    llm: Llm,
    checker: StatementChecker,
    *,
    claim_slug: str,
    article_url: str,
    text: str,
    archive_url: str | None = None,
    now: datetime | None = None,
) -> Extracted:
    """Add what an article says to a claim that is still pending, its reported statements
    included.

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

    draft = _extract(llm, text, checker)
    if not claim.summary:
        claim.summary = draft.summary
    _apply(session, claim, article, draft, text, archive_url)
    statements = keep_statements(
        session,
        checker,
        article=article,
        text=text,
        proposed=draft.statements,
        now=now or datetime.now(UTC),
    )
    return Extracted(claim, statements)


def _extract(llm: Llm, text: str, checker: StatementChecker, purpose: str = EXTRACTION) -> Draft:
    return llm.run(
        purpose,
        instructions=INSTRUCTIONS + statement_rules(checker.per_article),
        prompt=text,
        output_type=Draft,
    )


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
    whole_names = set(
        whole_intervention_names(
            [intervention.name, *intervention.synonyms, *draft.intervention_synonyms]
        )
    )
    # A description the model returned as a name is dropped: it would be searched for.
    new_synonyms = [
        s
        for s in draft.intervention_synonyms
        if s in whole_names and is_a_name(s) and name_key(s) not in names
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
        if entity_type in ORGANISATION_TYPES:
            # Kept with the article that named it, once per organisation of the claim.
            note_named_organisation(session, claim, article, named.name, entity_type)
        elif (entity_type, name_key(named.name)) not in known:
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
