"""Manual entry of claims, source articles and promises. Behavior: openspec claims."""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONPATH
from sqlalchemy.orm import Session

from thenwhat.claims.promises import parse_promise_date
from thenwhat.claims.verticals import APPROACHES, VERTICALS
from thenwhat.db.models import (
    Claim,
    ClaimChange,
    Entity,
    EntitySubstance,
    Promise,
    RegistryTrial,
    SourceArticle,
)
from thenwhat.domain import Decider, DraftedFrom, EntityType, ReviewState
from thenwhat.sources.clinicaltrials import NCT_ID, ClinicalTrials
from thenwhat.sources.rxnorm import not_searched

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


class AuditRefused(EntryError):
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


def owner_of_rule_slug(session: Session, intervention: str, indication: str) -> Claim | None:
    """The claim that has the slug the rule makes from this intervention and indication,
    when the rule makes that slug from the claim's own intervention name or a synonym and
    its own indication: then it is the same treatment and condition by their words,
    though one may write "alcohol-use" and the other "alcohol use". A claim given the
    slug by hand for something else is not its owner."""
    try:
        slug = slug_for(intervention, indication)
    except InvalidSlug:
        return None
    claim = find_claim(session, slug)
    if claim is None:
        return None
    names = session.execute(
        select(Entity.name, Entity.synonyms).where(
            Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION
        )
    ).all()
    for name, synonyms in names:
        for known in (name, *synonyms):
            try:
                if slug_for(known, claim.indication) == slug:
                    return claim
            except InvalidSlug:
                continue
    return None


def free_slug_for(session: Session, intervention: str, indication: str) -> str:
    """The slug the rule makes for a new claim. Refuses, naming the slug, when a claim
    already has it: no other slug is tried in its place."""
    slug = slug_for(intervention, indication)
    if slug_in_use(session, slug):
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


def slug_in_use(session: Session, slug: str) -> bool:
    """Whether a claim has this slug, or had it before a rename: a former slug stays
    taken, because its address leads to the renamed claim."""
    if find_claim(session, slug) is not None:
        return True
    former = session.scalar(select(ClaimChange.id).where(ClaimChange.former_slug == slug))
    return former is not None


def claim_by_slug(session: Session, slug: str) -> Claim:
    claim = find_claim(session, slug)
    if claim is None:
        raise ClaimNotFound(f"No claim has the slug '{slug}'.")
    return claim


def slug_of_claim_covering(session: Session, intervention: str, indication: str) -> str | None:
    """Slug of the claim for this intervention and indication, if one exists.

    The intervention matches on its entity's name or any synonym. A claim merged into
    another stands for nothing any more and is never the answer.
    """
    candidates = session.execute(
        select(Claim.slug, Entity.name, Entity.synonyms)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(Entity.type == EntityType.INTERVENTION, Claim.merged_into_id.is_(None))
        .order_by(Claim.id)
    )
    wanted = (name_key(intervention), name_key(indication))
    indications = dict(session.execute(select(Claim.slug, Claim.indication)).all())
    for slug, name, synonyms in candidates:
        known_names = {name_key(name), *(name_key(synonym) for synonym in synonyms)}
        if wanted[0] in known_names and name_key(indications[slug]) == wanted[1]:
            return slug
    return None


# What a name says about how a treatment is given, besides the treatment: a dose, how
# often, the form it comes in, and the therapy a drug is given alongside. Batch 1's audit
# (2026-11-16) found reads that drafted "semaglutide 2.4 mg once-weekly injections" and
# "MDMA-assisted psychotherapy" beside the live semaglutide and MDMA claims.
# Compared names are casefolded, which turns the micro sign into the Greek mu.
_DOSE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|μg|ug|g|ml|iu|units?|%)(?:/\s*kg)?(?![\w-])")
_COUNT = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve)"
_HOW_GIVEN = re.compile(
    r"\b(?:(?:once|twice|three times)[- ](?:a[- ])?(?:daily|weekly|monthly|day|week|month)"
    rf"|for {_COUNT} (?:days?|weeks?|months?)"
    r"|(?:high|low|standard)[- ]dose|daily|weekly|monthly"
    r"|injections?|doses?|dosing)\b"
)
_ASSISTED = re.compile(r"-assisted\b.*$")


def core_name(text: str) -> str:
    """The treatment a name names once its dose, schedule, form and any "-assisted ..."
    therapy are left out, in the compared form: "semaglutide 2.4 mg once-weekly
    injections" and "MDMA-assisted psychotherapy" give "semaglutide" and "mdma". A route
    or a form that makes another product ("nasal spray", "oral", "pill", "tablets",
    "extended release") is kept: oral semaglutide is not the injected drug. Used to find
    candidates and to refuse a duplicate, never to join one."""
    key = name_key(text)
    key = _ASSISTED.sub("", key)
    key = _HOW_GIVEN.sub(" ", _DOSE.sub(" ", key))
    return tidy(key.strip(" ,;-"))


_BRACKETED = re.compile(r"\([^)]*\)")
# A word that starts a phrase about someone or something else: "sleep apnoea in people
# with obesity" is not a kind of obesity.
_LINKING = {"in", "with", "after", "for", "of", "among", "without", "during", "from", "to", "at"}


def condition_words(text: str) -> list[str]:
    """A condition's words in the compared form: letter case, spacing and hyphens do not
    matter, so "Alcohol-use disorder" and "alcohol use disorder" have the same words."""
    return re.findall(r"[^\W_]+", name_key(text))


def _conditions_overlap(first: str, second: str) -> bool:
    """Whether one condition is the other, or the other with words that only narrow it
    put in front: "advanced pancreatic cancer" and "pancreatic cancer". Words in
    brackets are left out ("post-traumatic stress disorder (PTSD)"). A condition that
    only ends with the other after "in", "with" or the like is another condition."""
    short, long = sorted(
        (condition_words(_BRACKETED.sub(" ", text)) for text in (first, second)), key=len
    )
    if not short or long[len(long) - len(short) :] != short:
        return False
    return not _LINKING & set(long[: len(long) - len(short)])


def slug_of_claim_close_to(session: Session, intervention: str, indication: str) -> str | None:
    """Slug of a claim that stands for the same treatment and condition once dose,
    schedule and form are left out of the treatment's names, and one condition's words
    sit inside the other's. A rejected draft does not count. Only refuses a new claim:
    whether an article joins this one is still decided."""
    wanted = core_name(intervention)
    if not wanted:
        return None
    rows = session.execute(
        select(Claim.slug, Claim.indication, Entity.name, Entity.synonyms)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(
            Entity.type == EntityType.INTERVENTION,
            Claim.review_state != ReviewState.REJECTED,
            Claim.merged_into_id.is_(None),
        )
        .order_by(Claim.id)
    )
    for slug, condition, name, synonyms in rows:
        names = {core_name(known) for known in [name, *synonyms]}
        if wanted in names and _conditions_overlap(indication, condition):
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
    summary: str | None


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
            Claim.merged_into_id.is_(None),
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


def claims_sharing_a_name(
    session: Session, names: Sequence[str], *, indication: str = ""
) -> list[NamedClaim]:
    """Claims whose intervention shares a name with one of these names.

    A name is shared when a claim's intervention name or synonym is one of the names, or
    when one sits whole inside the other, word for word: "esketamine" inside "esketamine
    nasal spray". This finds candidates and decides nothing: two claims for one drug and
    two conditions both come back. Claims whose name is equal come first, then the oldest.
    The exact name and condition pair comes first so the limit cannot hide it.
    A rejected draft is never a candidate: it would only take the decision's votes from
    the claim that stands.
    """
    wanted = [words for name in names if (words := name_key(name).split())]
    if not wanted:
        return []
    found: list[tuple[bool, bool, int, NamedClaim]] = []
    wanted_condition = condition_words(indication)
    rows = session.execute(
        select(Claim.id, Claim.slug, Claim.indication, Entity.name, Entity.synonyms, Claim.summary)
        .join(Entity, Entity.claim_id == Claim.id)
        .where(
            Entity.type == EntityType.INTERVENTION,
            Claim.review_state != ReviewState.REJECTED,
            Claim.merged_into_id.is_(None),
        )
        .order_by(Claim.id)
    )
    for claim_id, slug, condition, name, synonyms, summary in rows:
        known = [name_key(known_name).split() for known_name in (name, *synonyms)]
        if not any(_one_within_the_other(mine, theirs) for mine in wanted for theirs in known):
            continue
        equal = any(mine == theirs for mine in wanted for theirs in known)
        exact = equal and condition_words(condition) == wanted_condition
        found.append((not exact, not equal, claim_id, NamedClaim(slug, name, condition, summary)))
    found.sort(key=lambda entry: entry[:3])
    return [claim for _, _, _, claim in found[:MAX_NAMED_CLAIMS]]


# Every name the registry of substances lists for a claim's substance, leaving out any
# it has withdrawn, from the record kept with the intervention.
_SUBSTANCE_NAMES = "$.names[*] ? (!(@.deprecated == true)).name"
# How many claims found only by their substance's names are offered to the same-claim
# decision, beside the claims `claims_sharing_a_name` gives: they are added to those,
# and never take the place of one.
MAX_SUBSTANCE_CLAIMS = 8


def claims_of_a_named_substance(
    session: Session, names: Sequence[str], *, indication: str = ""
) -> list[NamedClaim]:
    """Claims whose substance the registry of substances gives one of these names, in
    the record kept with the claim's intervention: what it calls the substance, a brand,
    another name it has not withdrawn, or a development code. A claim entered as
    lecanemab is found by Leqembi, and one entered as BAN2401 by either, though they
    share no word.

    The name is shared only whole: the registry's chemical names run to many words, and
    a word of one is no name for the treatment. This finds candidates and decides
    nothing. A claim for the same condition, or that condition narrowed, comes first,
    then the oldest. A rejected draft is never a candidate. Nor is a claim found only
    by the antigen a source of brands lists a vaccine under.
    """
    wanted = [words for name in names if (words := name_key(name).split())]
    if not wanted:
        return []
    found: list[tuple[bool, int, NamedClaim]] = []
    rows = session.execute(
        select(
            Claim.id,
            Claim.slug,
            Claim.indication,
            Entity.name,
            Claim.summary,
            # Only the names are read from the substance's record, which is large.
            EntitySubstance.payload["substance"]["_name"].astext,
            func.jsonb_path_query_array(EntitySubstance.payload, cast(_SUBSTANCE_NAMES, JSONPATH)),
            EntitySubstance.codes,
            EntitySubstance.source_name,
            EntitySubstance.payload["product_codes"],
        )
        .join(Entity, Entity.claim_id == Claim.id)
        .join(EntitySubstance, EntitySubstance.entity_id == Entity.id)
        .where(
            Entity.type == EntityType.INTERVENTION,
            Claim.review_state != ReviewState.REJECTED,
            Claim.merged_into_id.is_(None),
        )
        .order_by(Claim.id)
    )
    for (
        claim_id,
        slug,
        condition,
        name,
        summary,
        substance,
        listed,
        codes,
        source,
        products,
    ) in rows:
        # A vaccine's antigen is no name for it, and an ingredient whose brand is not
        # yet known to be no vaccine is not taken for one (`not_searched`).
        if not_searched(source, {} if products is None else {"product_codes": products}):
            continue
        registered = [
            name_key(other).split()
            for other in (substance, *(listed or ()), *(codes or ()))
            if isinstance(other, str)
        ]
        if not any(mine == theirs for mine in wanted for theirs in registered):
            continue
        same_condition = bool(indication) and _conditions_overlap(indication, condition)
        found.append((not same_condition, claim_id, NamedClaim(slug, name, condition, summary)))
    found.sort(key=lambda entry: entry[:2])
    return [claim for _, _, claim in found[:MAX_SUBSTANCE_CLAIMS]]


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
    drafted_from: str = DraftedFrom.OPERATOR,
) -> Claim:
    """Create a claim and its intervention entity. One claim per intervention and indication.

    An approach given here is recorded as a person's; the seed loader says otherwise."""
    try:
        origin = DraftedFrom(drafted_from)
    except ValueError as error:
        raise InvalidField(f"Unknown claim drafting source {drafted_from!r}.") from error
    if origin is DraftedFrom.REGISTRY:
        raise InvalidField("Use the registry drafting path for a claim with trial evidence.")
    return _add_claim(
        session,
        slug=slug,
        headline=_required("headline", headline),
        summary=tidy(summary),
        vertical=vertical,
        intervention=intervention,
        indication=indication,
        approach=approach,
        drafted_from=origin,
    )


def add_registry_claim(
    session: Session,
    *,
    slug: str,
    vertical: str,
    intervention: str,
    indication: str,
    trial_ids: Sequence[str],
) -> Claim:
    """Store a pending registry claim using the recorded trials as its drafting evidence."""
    identifiers = sorted({identifier.strip().upper() for identifier in trial_ids})
    if not identifiers:
        raise MissingField("A registry claim needs its drafting trial IDs.")
    if not all(NCT_ID.fullmatch(identifier) for identifier in identifiers):
        raise InvalidField("Drafting trials must be ClinicalTrials.gov identifiers.")
    stored = set(
        session.scalars(
            select(RegistryTrial.external_id).where(
                RegistryTrial.registry_name == ClinicalTrials.name,
                RegistryTrial.external_id.in_(identifiers),
            )
        )
    )
    if missing := set(identifiers) - stored:
        listed = ", ".join(sorted(missing))
        raise InvalidField(f"Drafting trial records missing from the registry: {listed}.")
    return _add_claim(
        session,
        slug=slug,
        headline=None,
        summary=None,
        vertical=vertical,
        intervention=intervention,
        indication=indication,
        approach=None,
        drafted_from=DraftedFrom.REGISTRY,
        drafting_trial_ids=identifiers,
    )


def _add_claim(
    session: Session,
    *,
    slug: str,
    headline: str | None,
    summary: str | None,
    vertical: str,
    intervention: str,
    indication: str,
    approach: str | None,
    drafted_from: DraftedFrom,
    drafting_trial_ids: Sequence[str] = (),
) -> Claim:
    _check_slug(slug)
    intervention = _required("intervention", intervention)
    indication = _required("indication", indication)
    _check_vertical(vertical)
    approach = _approach(approach)
    if slug_in_use(session, slug):
        raise SlugTaken(f"Slug '{slug}' is already taken.")
    existing = slug_of_claim_covering(session, intervention, indication)
    if existing is not None:
        raise DuplicateClaim(existing)

    claim = Claim(
        slug=slug,
        headline=headline,
        summary=summary,
        drafted_from=drafted_from,
        drafting_trial_ids=list(drafting_trial_ids),
        vertical=vertical,
        approach=approach,
        approach_decided_by=Decider.HUMAN if approach else None,
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


def unarchived_claims(session: Session) -> list[Claim]:
    """Every claim not taken off the site, by slug."""
    return list(
        session.scalars(select(Claim).where(Claim.archived_at.is_(None)).order_by(Claim.slug))
    )


def check_new_claim(session: Session, slug: str, vertical: str) -> None:
    """Refuse a slug or vertical that `add_claim` would refuse, before any costly work."""
    _check_slug(slug)
    _check_vertical(vertical)
    if slug_in_use(session, slug):
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

    An empty approach clears it, with who set it and what a rule set it on; a rule may
    then fill it again. An approach given here is recorded as a person's."""
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
        claim.approach_decided_by = Decider.HUMAN if claim.approach else None
        claim.approach_basis = None
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
    if slug_in_use(session, new_slug):
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
    if claim.merged_into_id is not None:
        kept = session.get(Claim, claim.merged_into_id)
        assert kept is not None
        raise ArchiveRefused(
            f"Claim '{slug}' was merged into '{kept.slug}': its articles are there, and"
            f" its address leads there. To undo the merge: thenwhat claim unmerge {slug}"
        )
    claim.archived_at = None
    claim.archive_reason = None
    session.flush()
    return claim


def awaiting_audit(session: Session) -> list[Claim]:
    """Claims approved by rule that are held off the site until their batch is audited,
    oldest hold first. Archived ones are included: unarchiving does not clear the hold."""
    return list(
        session.scalars(
            select(Claim)
            .where(Claim.awaiting_audit_at.is_not(None))
            .order_by(Claim.awaiting_audit_at, Claim.slug)
        )
    )


def clear_audit(session: Session, slugs: list[str]) -> list[Claim]:
    """Let claims whose audit passed be published from the next export on. Every slug is
    checked before any hold is cleared, so a refusal clears nothing."""
    claims = [claim_by_slug(session, slug) for slug in slugs]
    not_held = [claim.slug for claim in claims if claim.awaiting_audit_at is None]
    if not_held:
        raise AuditRefused(f"Not awaiting audit: {', '.join(not_held)}. Nothing was cleared.")
    for claim in claims:
        claim.awaiting_audit_at = None
    session.flush()
    return claims
