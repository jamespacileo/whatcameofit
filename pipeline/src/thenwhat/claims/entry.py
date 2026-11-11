"""Manual entry of claims, source articles and promises. Behavior: openspec claims."""

import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.claims.promises import parse_promise_date
from thenwhat.claims.verticals import VERTICALS
from thenwhat.db.models import Claim, Entity, Promise, SourceArticle
from thenwhat.domain import EntityType

MAX_SLUG_LENGTH = 60
SLUG_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class EntryError(Exception):
    """An entry the operator asked for was refused. The message is shown to the operator."""


class InvalidSlug(EntryError):
    pass


class SlugTaken(EntryError):
    pass


class UnknownVertical(EntryError):
    pass


class MissingField(EntryError):
    pass


class InvalidUrl(EntryError):
    pass


class ClaimNotFound(EntryError):
    pass


class DuplicateArticle(EntryError):
    pass


class ArticleNotFound(EntryError):
    pass


class SlugLocked(EntryError):
    pass


class DuplicateClaim(EntryError):
    """Another claim already covers this intervention and indication."""

    def __init__(self, existing_slug: str) -> None:
        self.existing_slug = existing_slug
        super().__init__(
            f"Claim '{existing_slug}' already covers this intervention and indication."
            " Add the article to that claim instead."
        )


def _tidy(text: str) -> str:
    return " ".join(text.split())


def _key(text: str) -> str:
    """Form used to compare names: spacing and letter case do not matter."""
    return _tidy(text).casefold()


def _required(field: str, value: str) -> str:
    value = _tidy(value)
    if not value:
        raise MissingField(f"{field} is required.")
    return value


def _check_slug(slug: str) -> None:
    if len(slug) > MAX_SLUG_LENGTH or not SLUG_PATTERN.fullmatch(slug):
        raise InvalidSlug(
            f"Slug '{slug}' is not valid. Use lowercase letters, digits and single hyphens,"
            f" at most {MAX_SLUG_LENGTH} characters."
        )


def find_claim(session: Session, slug: str) -> Claim | None:
    return session.scalars(select(Claim).where(Claim.slug == slug)).one_or_none()


def _claim(session: Session, slug: str) -> Claim:
    claim = find_claim(session, slug)
    if claim is None:
        raise ClaimNotFound(f"No claim has the slug '{slug}'.")
    return claim


def _slug_of_claim_covering(session: Session, intervention: str, indication: str) -> str | None:
    """Slug of the claim for this intervention and indication, if one exists.

    The intervention matches on its entity's name or any synonym.
    """
    candidates = session.execute(
        select(Claim.slug, Entity.name, Entity.synonyms)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(Entity.type == EntityType.INTERVENTION)
    )
    wanted = (_key(intervention), _key(indication))
    indications = dict(session.execute(select(Claim.slug, Claim.indication)).all())
    for slug, name, synonyms in candidates:
        known_names = {_key(name), *(_key(synonym) for synonym in synonyms)}
        if wanted[0] in known_names and _key(indications[slug]) == wanted[1]:
            return slug
    return None


def add_claim(
    session: Session,
    *,
    slug: str,
    headline: str,
    vertical: str,
    intervention: str,
    indication: str,
    summary: str = "",
) -> Claim:
    """Create a claim and its intervention entity. One claim per intervention and indication."""
    _check_slug(slug)
    headline = _required("headline", headline)
    intervention = _required("intervention", intervention)
    indication = _required("indication", indication)
    if vertical not in VERTICALS:
        valid = ", ".join(sorted(VERTICALS))
        raise UnknownVertical(f"Unknown vertical '{vertical}'. Valid verticals: {valid}.")
    if find_claim(session, slug) is not None:
        raise SlugTaken(f"Slug '{slug}' is already taken.")
    existing = _slug_of_claim_covering(session, intervention, indication)
    if existing is not None:
        raise DuplicateClaim(existing)

    claim = Claim(
        slug=slug,
        headline=headline,
        summary=_tidy(summary),
        vertical=vertical,
        indication=indication,
    )
    session.add(claim)
    session.flush()
    session.add(Entity(claim_id=claim.id, type=EntityType.INTERVENTION, name=intervention))
    session.flush()
    return claim


def add_article(
    session: Session,
    claim_slug: str,
    *,
    url: str,
    outlet: str,
    title: str,
    published_date: date,
) -> SourceArticle:
    """Attach a news article to a claim. Only its reference is stored, never its text."""
    claim = _claim(session, claim_slug)
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise InvalidUrl(f"Article URL must start with http:// or https://, got '{url}'.")
    outlet = _required("outlet", outlet)
    title = _required("title", title)
    if _find_article(session, claim, url) is not None:
        raise DuplicateArticle(f"Claim '{claim.slug}' already has the article {url}.")

    article = SourceArticle(
        claim_id=claim.id, url=url, outlet=outlet, title=title, published_date=published_date
    )
    session.add(article)
    session.flush()
    if claim.first_reported_date is None or published_date < claim.first_reported_date:
        claim.first_reported_date = published_date
    return article


def _find_article(session: Session, claim: Claim, url: str) -> SourceArticle | None:
    return session.scalars(
        select(SourceArticle).where(SourceArticle.claim_id == claim.id, SourceArticle.url == url)
    ).one_or_none()


def add_promise(
    session: Session,
    claim_slug: str,
    *,
    article_url: str,
    description: str,
    parsed_date: date | None = None,
) -> Promise:
    """Record a timeline promised in one of the claim's articles.

    The date is read from the wording unless the operator supplies one.
    """
    claim = _claim(session, claim_slug)
    article = _find_article(session, claim, article_url.strip())
    if article is None:
        raise ArticleNotFound(f"Claim '{claim.slug}' has no article {article_url}.")
    description = _required("description", description)

    promise = Promise(
        claim_id=claim.id,
        source_article_id=article.id,
        description=description,
        parsed_date=parsed_date or parse_promise_date(description, article.published_date),
    )
    session.add(promise)
    session.flush()
    return promise


def rename_slug(session: Session, slug: str, new_slug: str) -> Claim:
    """Change a claim's slug. Refused once the claim has been published, so links stay valid."""
    claim = _claim(session, slug)
    if claim.published_at is not None:
        raise SlugLocked(f"Claim '{slug}' has been published, so its slug can no longer change.")
    _check_slug(new_slug)
    if find_claim(session, new_slug) is not None:
        raise SlugTaken(f"Slug '{new_slug}' is already taken.")
    claim.slug = new_slug
    session.flush()
    return claim


def promises_of(session: Session, claim: Claim) -> list[Promise]:
    """A claim's promises, in the order their articles were published."""
    return list(
        session.scalars(
            select(Promise)
            .join(SourceArticle, SourceArticle.id == Promise.source_article_id)
            .where(Promise.claim_id == claim.id)
            .order_by(SourceArticle.published_date, Promise.id)
        )
    )


def articles_of(session: Session, claim: Claim) -> list[SourceArticle]:
    """A claim's source articles, oldest first."""
    return list(
        session.scalars(
            select(SourceArticle)
            .where(SourceArticle.claim_id == claim.id)
            .order_by(SourceArticle.published_date, SourceArticle.id)
        )
    )


def claim_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Claim)) or 0
