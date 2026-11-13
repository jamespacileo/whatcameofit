"""Which citing papers count as follow-ups, and retraction events. Pure.

A follow-up paper cites the origin paper (true of every paper passed in here) and
also shares an author with it or names the intervention in its title or abstract.
"""

from datetime import datetime

from thenwhat.domain import EventType
from thenwhat.events.draft import EventDraft
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.crossref import Notice
from thenwhat.sources.europepmc import PaperInfo, describe

BOTH_SIGNS = 0.9
ONE_SIGN = 0.6


def _key(text: str) -> str:
    return " ".join(text.split()).casefold()


def follow_up_confidence(
    citing: PaperInfo, origin: PaperInfo, intervention_names: list[str]
) -> float | None:
    """How sure we are that a citing paper follows up the origin paper, or None if
    it shows neither sign."""
    shares_author = bool({_key(a) for a in citing.authors} & {_key(a) for a in origin.authors})
    text = _key(f"{citing.title} {citing.abstract}")
    names_intervention = any(_key(name) in text for name in intervention_names if name.strip())
    if shares_author and names_intervention:
        return BOTH_SIGNS
    if shares_author or names_intervention:
        return ONE_SIGN
    return None


def follow_up_event(citing: SourceRecord, confidence: float) -> EventDraft | None:
    info = describe(citing)
    if info.published_date is None:
        return None
    return EventDraft(
        type=EventType.FOLLOWUP_PAPER,
        event_date=info.published_date,
        date_basis="first publication date",
        source_name=citing.source_name,
        source_url=citing.url,
        external_id=citing.external_id,
        summary=info.title,
        confidence=confidence,
        raw_payload=citing.payload,
        fetched_at=citing.fetched_at,
    )


def retraction_event(doi: str, title: str, notice: Notice, now: datetime) -> EventDraft:
    """A retraction of the paper with this DOI. The event names the retracted paper;
    its source link is the retraction notice."""
    return EventDraft(
        type=EventType.RETRACTION,
        event_date=notice.notice_date,
        date_basis="retraction notice date",
        source_name="crossref",
        source_url=f"https://doi.org/{notice.notice_doi}",
        external_id=doi.lower(),
        summary=f"Retraction notice issued for: {title}",
        confidence=1.0,
        raw_payload={"retracted_doi": doi.lower(), "notice": notice.raw or _plain(notice)},
        fetched_at=notice.fetched_at or now,
    )


def _plain(notice: Notice) -> dict[str, str]:
    return {
        "type": notice.type,
        "date": notice.notice_date.isoformat(),
        "DOI": notice.notice_doi,
    }
