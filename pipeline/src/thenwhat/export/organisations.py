"""The organisations a published claim names, for the export. Behavior: openspec
organisations.

Each organisation is listed once: one per approved registry record, else one per
entity under the name a source gave it. Its roles say what a source states (a report
named it, a trial's record names it as lead sponsor) and nothing more. What is said of
an identified organisation is five fields of its registry record, the match score and
the date the record was read. Organisations are never an input to the status.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict

from thenwhat.claims.entities import ORGANISATION_TYPES
from thenwhat.claims.entry import name_key
from thenwhat.db.models import Entity, EntityMatch, OrganisationRecord, SourceArticle
from thenwhat.domain import EntityType, NamedBy
from thenwhat.sources.base import SourceRecord, record_url
from thenwhat.sources.ror import Ror, describe

if TYPE_CHECKING:
    from thenwhat.export.records import Records

OrganisationRole = Literal["named_in_report", "sponsor"]
# The order an organisation's roles are listed in, and organisations by their first role.
ORGANISATION_ROLES: tuple[OrganisationRole, ...] = ("named_in_report", "sponsor")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExportedOrganisationRole(_Strict):
    role: OrganisationRole
    # For "named_in_report": the addresses of the claim's articles that named it, each an
    # entry in the claim's `articles`. Empty when which report named it was not recorded.
    article_urls: list[str] = []
    # For "sponsor": the trials whose registry record names it as lead sponsor, each an
    # entry in the claim's `trials`.
    trial_ids: list[str] = []


class ExportedOrganisationRecord(_Strict):
    """What the organisation registry's record says, and how the name was matched to it.
    No other field of the record is carried (docs/sources.md)."""

    # The registry's name in `sources`, such as "ror".
    source: str
    external_id: str
    # The record's own page.
    url: str
    # The registry's display name for the organisation.
    name: str
    # The registry's types, as lower-case codes such as "education" or "company". The
    # site owns their wording.
    kinds: list[str]
    country: str | None
    # Only an https address.
    website: str | None
    # The registry's own measure, 0 to 1, of how well the name matched the record: the
    # lowest among the names tied to it.
    score: float
    # When the record was read.
    read_at: datetime


class ExportedOrganisation(_Strict):
    # The registry's name when identified, else the name the source gave.
    name: str
    # Whether an approved match ties the organisation to a registry record.
    identified: bool
    # None when not identified.
    record: ExportedOrganisationRecord | None
    roles: list[ExportedOrganisationRole]


def host_of(url: str | None) -> str | None:
    """The host of an address in lower case, without a leading `www.`."""
    if not url:
        return None
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host.removeprefix("www.") or None


def is_on_website(article_url: str, website: str | None) -> bool:
    """Whether an article's address is on an organisation's website or a subdomain of
    it: its host equals the website's, ignoring a leading `www.`, or ends with a dot
    followed by it. Pure; it needs no list of public suffixes because it only ever
    compares with one organisation's own host."""
    article, site = host_of(article_url), host_of(website)
    if article is None or site is None:
        return False
    return article == site or article.endswith(f".{site}")


def publisher_of(article_url: str, organisations: Iterable[ExportedOrganisation]) -> str | None:
    """The record address of the identified organisation whose website holds the
    article, the most specific one when several do. None for any other article."""
    held = [
        (len(host_of(organisation.record.website) or ""), organisation.record.url)
        for organisation in organisations
        if organisation.record is not None
        and is_on_website(article_url, organisation.record.website)
    ]
    return max(held)[1] if held else None


@dataclass
class _Organisation:
    given_name: str
    record: ExportedOrganisationRecord | None
    article_urls: list[str] = field(default_factory=list)
    trial_ids: list[str] = field(default_factory=list)
    named_in_report: bool = False

    def exported(self) -> ExportedOrganisation | None:
        roles: list[ExportedOrganisationRole] = []
        if self.named_in_report:
            roles.append(
                ExportedOrganisationRole(
                    role="named_in_report", article_urls=list(dict.fromkeys(self.article_urls))
                )
            )
        if self.trial_ids:
            roles.append(
                ExportedOrganisationRole(
                    role="sponsor", trial_ids=sorted(dict.fromkeys(self.trial_ids))
                )
            )
        if not roles:
            return None
        return ExportedOrganisation(
            name=self.record.name if self.record else self.given_name,
            identified=self.record is not None,
            record=self.record,
            roles=roles,
        )


def _identified_by(
    records: "Records", entity: Entity
) -> tuple[EntityMatch, OrganisationRecord] | None:
    """The entity's approved organisation match, the most recent when there are several,
    with the record it points to. None when no approved match has a record read."""
    approved = [m for m in records.approved_matches(entity) if m.source_name == Ror.name]
    for match in sorted(approved, key=lambda m: m.id, reverse=True):
        kept = records.organisation_record(match.source_name, match.external_id)
        if kept is not None:
            return match, kept
    return None


def _record(match: EntityMatch, kept: OrganisationRecord) -> ExportedOrganisationRecord:
    read = describe(
        SourceRecord(
            kept.source_name,
            kept.external_id,
            kept.url,
            {"organization": kept.payload},
            kept.fetched_at,
        )
    )
    website = read.website if read.website and read.website.startswith("https://") else None
    kinds = [str(kind).lower() for kind in kept.payload.get("types") or [] if kind]
    return ExportedOrganisationRecord(
        source=kept.source_name,
        external_id=kept.external_id,
        url=record_url(kept.source_name, kept.external_id) or kept.url,
        name=read.name,
        kinds=list(dict.fromkeys(kinds)),
        country=read.country or None,
        website=website,
        score=round(match.score, 4),
        read_at=kept.fetched_at,
    )


def _names(entity: Entity) -> set[str]:
    return {name_key(entity.name), *(name_key(synonym) for synonym in entity.synonyms)}


def organisations_of(
    records: "Records",
    entities: list[Entity],
    *,
    articles: list[SourceArticle],
    sponsors: dict[str, str],
) -> list[ExportedOrganisation]:
    """The organisations among a claim's entities, ordered by role and then by name.

    `sponsors` maps each listed trial's identifier to its lead sponsor's name, for the
    trials whose sponsor is not a person. An organisation whose name is a person's
    recorded for the claim is never listed.
    """
    people = {
        key for entity in entities if entity.type is EntityType.PERSON for key in _names(entity)
    }
    article_urls = {article.id: article.url for article in articles}
    by_identity: dict[tuple[str, str] | int, _Organisation] = {}
    for entity in entities:
        if entity.type not in ORGANISATION_TYPES or _names(entity) & people:
            continue
        identified = _identified_by(records, entity)
        record = _record(*identified) if identified else None
        if record is not None and name_key(record.name) in people:
            continue
        key: tuple[str, str] | int = (record.source, record.external_id) if record else entity.id
        organisation = by_identity.get(key)
        if organisation is None:
            organisation = by_identity[key] = _Organisation(entity.name, record)
        elif record is not None and organisation.record is not None:
            # One record under several names: the lowest of their scores is shown.
            organisation.record = organisation.record.model_copy(
                update={"score": min(organisation.record.score, record.score)}
            )
        if NamedBy.ARTICLE in entity.named_by:
            organisation.named_in_report = True
            organisation.article_urls += [
                article_urls[link] for link in records.named_in(entity) if link in article_urls
            ]
        names = _names(entity)
        organisation.trial_ids += [
            trial_id for trial_id, sponsor in sponsors.items() if name_key(sponsor) in names
        ]
    order = {url: index for index, url in enumerate(article_urls.values())}
    listed: list[ExportedOrganisation] = []
    for organisation in by_identity.values():
        organisation.article_urls.sort(key=lambda url: order[url])
        exported = organisation.exported()
        if exported is not None:
            listed.append(exported)
    return sorted(
        listed,
        key=lambda organisation: (
            ORGANISATION_ROLES.index(organisation.roles[0].role),
            organisation.name.casefold(),
        ),
    )
