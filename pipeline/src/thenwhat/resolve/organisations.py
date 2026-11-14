"""Looking up the institutions and companies a claim names. Behavior: openspec
entity-resolution, "Organisations are looked up by name" and "An organisation match is
approved by rule only on strong evidence".

No model scores or decides these: the score is the organisation registry's own measure
of how well the name matched. A match is approved by rule only when the registry marks
the record as its chosen answer and the name given is, exactly, one of the record's own
names; everything else stays pending and the organisation stays unidentified. No looser
match is tried. A person is never looked up, in any registry or directory.
"""

import re
import unicodedata
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import ORGANISATION_TYPES, entities_of
from thenwhat.db.models import Claim, EntityMatch, OrganisationRecord, PaperRecord
from thenwhat.domain import Decider, ReviewState
from thenwhat.resolve.service import MAX_SUMMARY_CHARACTERS
from thenwhat.review.decisions import record_decision
from thenwhat.sources import ror
from thenwhat.sources.base import SourceRecord


class OrganisationRegistry(Protocol):
    def organisations(self, name: str) -> list[SourceRecord]: ...


def organisation_line(record: SourceRecord) -> str:
    """One line on an organisation: its name, country and website."""
    organisation = ror.describe(record)
    parts = [organisation.name, organisation.country, organisation.website or ""]
    return ". ".join(part for part in parts if part)[:MAX_SUMMARY_CHARACTERS]


def normalised(text: str) -> str:
    """A name compared without regard to case, accents, punctuation or a leading
    "The"."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    words = re.sub(r"[^\w\s]", " ", text.casefold().replace("&", " and ")).split()
    return " ".join(words[1:] if words[:1] == ["the"] else words)


# A closing bracket such as "(UCSF)" after a name, or "(United States)" after a ROR
# company record's name.
_BRACKET_AFTER = re.compile(r"\s*\([^()]*\)\s*$")
# The record's own names that a name given may equal. Acronyms are compared as written.
_NAME_TYPES = {"ror_display", "label", "alias"}


def _names(organisation: dict[str, Any], types: set[str]) -> list[str]:
    return [
        str(name.get("value") or "").strip()
        for name in organisation.get("names") or []
        if set(name.get("types") or []) & types and name.get("value")
    ]


def is_named_exactly(name: str, organisation: dict[str, Any]) -> bool:
    """Whether the name given is one of the record's names, labels or aliases, compared
    by `normalised` and each with or without a closing bracket, or one of its acronyms
    as written. A one-word name must also appear among the record's names with the same
    letters and capitals, so that "Neuron" is not "NeurON"."""
    given = name.strip()
    names = _names(organisation, _NAME_TYPES)
    acronyms = _names(organisation, {"acronym"})
    if len(normalised(given).split()) == 1 and given not in names + acronyms:
        return False
    forms = {normalised(given), normalised(_BRACKET_AFTER.sub("", given))}
    held = {normalised(n) for n in names} | {normalised(_BRACKET_AFTER.sub("", n)) for n in names}
    return bool(forms & held - {""}) or given in acronyms


def states_country(name: str, organisation: dict[str, Any]) -> bool:
    """Whether the name given states the record's country: its name, or its two-letter
    code written as a word ("U.S." counts as "US")."""
    country = ((organisation.get("locations") or [{}])[0].get("geonames_details")) or {}
    words = f" {normalised(name.replace('.', ''))} "
    stated = [str(country.get("country_name") or ""), str(country.get("country_code") or "")]
    return any(form and f" {normalised(form)} " in words for form in stated)


def meets_the_bar(name: str, record: SourceRecord, journals: Iterable[str] = ()) -> bool:
    """Whether a registry answer is strong enough evidence to approve by rule. Openspec
    entity-resolution: the registry chose the record, the name given is exactly one of
    its names, the record is not of the registry's catch-all kind "other", the name is
    not the title of a journal the pipeline holds a paper from, and a government body's
    name, which is reused from country to country, states its country."""
    organisation = ror.organisation_of(record)
    kinds = {str(kind) for kind in organisation.get("types") or []}
    return (
        ror.is_chosen(record)
        and is_named_exactly(name, organisation)
        and "other" not in kinds
        and normalised(name) not in set(journals)
        and ("government" not in kinds or states_country(name, organisation))
    )


def journal_titles(session: Session) -> set[str]:
    """The titles and abbreviations of the journals of every paper record held,
    normalised. A name equal to one is a journal named in a report, not an organisation
    that did the work."""
    titles: set[str] = set()
    for payload in session.scalars(
        select(PaperRecord.payload).where(PaperRecord.payload.is_not(None))
    ):
        journal = (payload or {}).get("journalInfo", {}).get("journal") or {}
        for field in ("title", "isoabbreviation", "medlineAbbreviation"):
            if isinstance(journal.get(field), str) and journal[field].strip():
                titles.add(normalised(journal[field]))
    return titles


def keep_record(session: Session, record: SourceRecord) -> OrganisationRecord:
    """Store the organisation's own record, replacing an older copy, so the export can
    say what the registry says of it and when that was read."""
    kept = session.get(OrganisationRecord, (record.source_name, record.external_id))
    if kept is None:
        kept = OrganisationRecord(source_name=record.source_name, external_id=record.external_id)
        session.add(kept)
    if kept.fetched_at is None or record.fetched_at >= kept.fetched_at:
        kept.url = record.url
        kept.payload = ror.organisation_of(record)
        kept.fetched_at = record.fetched_at
    return kept


def match_organisations(
    session: Session, claim: Claim, *, registry: OrganisationRegistry, now: datetime
) -> list[EntityMatch]:
    """Store the organisation the registry matches to each institution and company
    entity of the claim, and approve it by rule when the answer `meets_the_bar`. Returns
    the matches this run added; one that does not meet the bar stays pending, and its
    organisation unidentified.

    A name the registry does not know adds nothing. A match that already exists keeps
    its decision: an approved or rejected one is left as it is, and a pending one is
    approved by rule when the registry's answer meets the bar on a later run.
    """
    journals = journal_titles(session)
    named = [entity for entity in entities_of(session, claim) if entity.type in ORGANISATION_TYPES]
    stored = {
        (match.entity_id, match.source_name, match.external_id): match
        for match in session.scalars(
            select(EntityMatch).where(EntityMatch.entity_id.in_([e.id for e in named]))
        )
    }
    added: list[EntityMatch] = []
    for entity in named:
        for record in registry.organisations(entity.name):
            keep_record(session, record)
            key = (entity.id, record.source_name, record.external_id)
            match = stored.get(key)
            if match is None:
                match = EntityMatch(
                    entity_id=entity.id,
                    source_name=record.source_name,
                    external_id=record.external_id,
                    score=ror.describe(record).name_match,
                    record_summary=organisation_line(record),
                    review_state=ReviewState.PENDING,
                )
                session.add(match)
                stored[key] = match
                added.append(match)
            if match.review_state is ReviewState.PENDING and meets_the_bar(
                entity.name, record, journals
            ):
                record_decision(match, ReviewState.APPROVED, by=Decider.RULE, now=now)
    session.flush()
    return added
