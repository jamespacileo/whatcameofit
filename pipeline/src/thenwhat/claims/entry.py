"""Manual entry of claims, source articles and promises. Behavior: openspec claims."""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thenwhat.claims.promises import parse_promise_date
from thenwhat.claims.verticals import APPROACHES, VERTICALS
from thenwhat.db.models import Claim, Entity, Promise, SourceArticle
from thenwhat.domain import EntityType, ReviewState

MAX_SLUG_LENGTH = 60
MAX_SUMMARY_LENGTH = 500
SLUG_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class EntryError(Exception):
    """An entry the operator asked for was refused. The message is shown to the operator."""


class InvalidSlug(EntryError):
    pass


class SlugTaken(EntryError):
    pass


class UnknownVertical(EntryError):
    pass


class UnknownApproach(EntryError):
    pass


class MissingField(EntryError):
    pass


class InvalidUrl(EntryError):
    pass


class InvalidField(EntryError):
    pass


class ClaimNotFound(EntryError):
    pass


class DuplicateArticle(EntryError):
    pass


class ArticleNotFound(EntryError):
    pass


class SlugLocked(EntryError):
    pass


class ArchiveRefused(EntryError):
    pass


class DuplicateClaim(EntryError):
    """Another claim already covers this intervention and indication."""

    def __init__(self, existing_slug: str) -> None:
        self.existing_slug = existing_slug
        super().__init__(
            f"Claim '{existing_slug}' already covers this intervention and indication."
            " Add the article to that claim instead."
        )


def tidy(text: str) -> str:
    """The text with every run of whitespace made one space, and none at either end."""
    return " ".join(text.split())


def name_key(text: str) -> str:
    """Form used to compare names: spacing and letter case do not matter."""
    return tidy(text).casefold()


def _required(field: str, value: str) -> str:
    value = tidy(value)
    if not value:
        raise MissingField(f"{field} is required.")
    return value


def _check_slug(slug: str) -> None:
    if len(slug) > MAX_SLUG_LENGTH or not SLUG_PATTERN.fullmatch(slug):
        raise InvalidSlug(
            f"Slug '{slug}' is not valid. Use lowercase letters, digits and single hyphens,"
            f" at most {MAX_SLUG_LENGTH} characters."
        )


def slug_for(intervention: str, indication: str) -> str:
    """The slug a rule makes for a claim from its intervention and indication: their
    words in lower case, joined by hyphens, cut to the longest whole words that fit.
    Letters with accents lose them; any other character outside the slug's set is a
    break between words. Refuses when nothing usable is left."""
    plain = unicodedata.normalize("NFKD", f"{intervention} {indication}")
    plain = plain.encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", plain)
    slug = ""
    for word in words:
        longer = f"{slug}-{word}" if slug else word
        if len(longer) > MAX_SLUG_LENGTH:
            break
        slug = longer
    if not slug:
        raise InvalidSlug(
            f"No slug can be made from the intervention '{intervention}' and the "
            f"indication '{indication}'."
        )
    return slug


def free_slug_for(session: Session, intervention: str, indication: str) -> str:
    """The slug the rule makes for a new claim. Refuses, naming the slug, when a claim
    already has it: no other slug is tried in its place."""
    slug = slug_for(intervention, indication)
    if find_claim(session, slug) is not None:
        raise SlugTaken(
            f"The slug '{slug}', made by rule from the intervention '{intervention}' and "
            f"the indication '{indication}', belongs to another claim."
        )
    return slug


def _check_vertical(vertical: str) -> None:
    if vertical not in VERTICALS:
        valid = ", ".join(sorted(VERTICALS))
        raise UnknownVertical(f"Unknown vertical '{vertical}'. Valid verticals: {valid}.")


def _approach(approach: str | None) -> str | None:
    """The approach as stored: None for no approach. Refuses one outside the configured set."""
    approach = (approach or "").strip()
    if not approach:
        return None
    if approach not in APPROACHES:
        valid = ", ".join(APPROACHES)
        raise UnknownApproach(f"Unknown approach '{approach}'. Valid approaches: {valid}.")
    return approach


def find_claim(session: Session, slug: str) -> Claim | None:
    return session.scalars(select(Claim).where(Claim.slug == slug)).one_or_none()


def claim_by_slug(session: Session, slug: str) -> Claim:
    claim = find_claim(session, slug)
    if claim is None:
        raise ClaimNotFound(f"No claim has the slug '{slug}'.")
    return claim


def slug_of_claim_covering(session: Session, intervention: str, indication: str) -> str | None:
    """Slug of the claim for this intervention and indication, if one exists.

    The intervention matches on its entity's name or any synonym.
    """
    candidates = session.execute(
        select(Claim.slug, Entity.name, Entity.synonyms)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(Entity.type == EntityType.INTERVENTION)
    )
    wanted = (name_key(intervention), name_key(indication))
    indications = dict(session.execute(select(Claim.slug, Claim.indication)).all())
    for slug, name, synonyms in candidates:
        known_names = {name_key(name), *(name_key(synonym) for synonym in synonyms)}
        if wanted[0] in known_names and name_key(indications[slug]) == wanted[1]:
            return slug
    return None


# How many claims are offered to the decision that says whether an article reports one
# of them. An intervention with more claims than this is rare; the oldest are kept.
MAX_NAMED_CLAIMS = 8


@dataclass(frozen=True, slots=True)
class NamedClaim:
    """Claim identity and its own summary, never source article text."""

    slug: str
    intervention: str
    indication: str
    summary: str


def named_claims(session: Session, claim_ids: Sequence[int]) -> list[NamedClaim]:
    """These claims as the same-claim decision is shown them, oldest first. A rejected
    draft is left out: an article is not joined to a claim that will never be shown."""
    if not claim_ids:
        return []
    rows = session.execute(
        select(Claim.slug, Entity.name, Claim.indication, Claim.summary)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(
            Entity.type == EntityType.INTERVENTION,
            Claim.id.in_(claim_ids),
            Claim.review_state != ReviewState.REJECTED,
        )
        .order_by(Claim.id)
    )
    return [NamedClaim(slug, name, indication, summary) for slug, name, indication, summary in rows]


def _one_within_the_other(first: list[str], second: list[str]) -> bool:
    """Whether one run of words is the other, or sits whole inside it."""
    short, long = sorted((first, second), key=len)
    if not short:
        return False
    return any(
        long[start : start + len(short)] == short for start in range(len(long) - len(short) + 1)
    )


def claims_sharing_a_name(session: Session, names: Sequence[str]) -> list[NamedClaim]:
    """Claims whose intervention shares a name with one of these names.

    A name is shared when a claim's intervention name or synonym is one of the names, or
    when one sits whole inside the other, word for word: "esketamine" inside "esketamine
    nasal spray". This finds candidates and decides nothing: two claims for one drug and
    two conditions both come back. Claims whose name is equal come first, then the oldest.
    A rejected draft is never a candidate: it would only take the decision's votes from
    the claim that stands.
    """
    wanted = [words for name in names if (words := name_key(name).split())]
    if not wanted:
        return []
    found: list[tuple[bool, int, NamedClaim]] = []
    rows = session.execute(
        select(Claim.id, Claim.slug, Claim.indication, Entity.name, Entity.synonyms, Claim.summary)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(Entity.type == EntityType.INTERVENTION, Claim.review_state != ReviewState.REJECTED)
        .order_by(Claim.id)
    )
    for claim_id, slug, indication, name, synonyms, summary in rows:
        known = [name_key(known_name).split() for known_name in (name, *synonyms)]
        if not any(_one_within_the_other(mine, theirs) for mine in wanted for theirs in known):
            continue
        equal = any(mine == theirs for mine in wanted for theirs in known)
        found.append((not equal, claim_id, NamedClaim(slug, name, indication, summary)))
    found.sort(key=lambda entry: entry[:2])
    return [claim for _, _, claim in found[:MAX_NAMED_CLAIMS]]


def add_claim(
    session: Session,
    *,
    slug: str,
    headline: str,
    vertical: str,
    intervention: str,
    indication: str,
    summary: str = "",
    approach: str | None = None,
) -> Claim:
    """Create a claim and its intervention entity. One claim per intervention and indication."""
    _check_slug(slug)
    headline = _required("headline", headline)
    intervention = _required("intervention", intervention)
    indication = _required("indication", indication)
    _check_vertical(vertical)
    approach = _approach(approach)
    if find_claim(session, slug) is not None:
        raise SlugTaken(f"Slug '{slug}' is already taken.")
    existing = slug_of_claim_covering(session, intervention, indication)
    if existing is not None:
        raise DuplicateClaim(existing)

    claim = Claim(
        slug=slug,
        headline=headline,
        summary=tidy(summary),
        vertical=vertical,
        approach=approach,
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
    claim = claim_by_slug(session, claim_slug)
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise InvalidUrl(f"Article URL must start with http:// or https://, got '{url}'.")
    outlet = _required("outlet", outlet)
    title = _required("title", title)
    if find_article(session, claim, url) is not None:
        raise DuplicateArticle(f"Claim '{claim.slug}' already has the article {url}.")

    article = SourceArticle(
        claim_id=claim.id, url=url, outlet=outlet, title=title, published_date=published_date
    )
    session.add(article)
    session.flush()
    if claim.first_reported_date is None or published_date < claim.first_reported_date:
        claim.first_reported_date = published_date
    return article


def find_article(session: Session, claim: Claim, url: str) -> SourceArticle | None:
    return session.scalars(
        select(SourceArticle).where(SourceArticle.claim_id == claim.id, SourceArticle.url == url)
    ).one_or_none()


def check_new_claim(session: Session, slug: str, vertical: str) -> None:
    """Refuse a slug or vertical that `add_claim` would refuse, before any costly work."""
    _check_slug(slug)
    _check_vertical(vertical)
    if find_claim(session, slug) is not None:
        raise SlugTaken(f"Slug '{slug}' is already taken.")


def edit_claim(
    session: Session,
    slug: str,
    *,
    headline: str | None = None,
    summary: str | None = None,
    indication: str | None = None,
    intervention: str | None = None,
    vertical: str | None = None,
    approach: str | None = None,
) -> Claim:
    """Correct a claim's own fields. Changing its identity is checked against other claims.

    An empty approach clears it."""
    claim = claim_by_slug(session, slug)
    entity = session.scalars(
        select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).first()
    assert entity is not None, "every claim is created with its intervention entity"
    if vertical is not None:
        _check_vertical(vertical)
        claim.vertical = vertical
    if approach is not None:
        claim.approach = _approach(approach)
    if headline is not None:
        claim.headline = _required("headline", headline)
    if summary is not None:
        summary = _required("summary", summary)
        if len(summary) > MAX_SUMMARY_LENGTH:
            raise InvalidField(f"summary is longer than {MAX_SUMMARY_LENGTH} characters.")
        claim.summary = summary
    if indication is not None or intervention is not None:
        new_intervention = _required("intervention", intervention or entity.name)
        new_indication = _required("indication", indication or claim.indication)
        entity.name, old_name = "", entity.name  # so the claim does not match itself
        session.flush()
        other = slug_of_claim_covering(session, new_intervention, new_indication)
        if other is not None and other != claim.slug:
            entity.name = old_name
            raise DuplicateClaim(other)
        entity.name = new_intervention
        claim.indication = new_indication
    session.flush()
    return claim


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
    claim = claim_by_slug(session, claim_slug)
    article = find_article(session, claim, article_url.strip())
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
    claim = claim_by_slug(session, slug)
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


def archive_claim(session: Session, slug: str, *, reason: str, now: datetime) -> Claim:
    """Take a claim off the public site from the next export on. Nothing is deleted."""
    claim = claim_by_slug(session, slug)
    if claim.archived_at is not None:
        raise ArchiveRefused(f"Claim '{slug}' is already archived.")
    if not reason.strip():
        raise ArchiveRefused("Give a reason for archiving. It is kept, and never published.")
    claim.archived_at = now
    claim.archive_reason = reason.strip()
    session.flush()
    return claim


def unarchive_claim(session: Session, slug: str) -> Claim:
    """Put an archived claim back on the public site from the next export on."""
    claim = claim_by_slug(session, slug)
    if claim.archived_at is None:
        raise ArchiveRefused(f"Claim '{slug}' is not archived.")
    claim.archived_at = None
    claim.archive_reason = None
    session.flush()
    return claim
