"""The JSON export the site is built from. Behavior: openspec site-publishing.

Only approved, unarchived claims are exported, with their approved events, their
approved matches, a few candidates still awaiting review and their background cards.
The file is the single interface between pipeline and site; its schema is checked in at
site/export.schema.json.
"""

import base64
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import articles_of, promises_of
from thenwhat.claims.status import refresh_status, status_history
from thenwhat.claims.verticals import GROUPS, RETIRED_VERTICALS, VERTICAL_GROUPS, VERTICALS
from thenwhat.db.models import (
    Claim,
    ClaimTerm,
    Entity,
    EntityMatch,
    EvidenceEvent,
    FailureFlag,
    OutletIcon,
    PaperRecord,
    TermRecord,
)
from thenwhat.decide.steps import latest_scoring
from thenwhat.domain import (
    TRIAL_EVENT_TYPES,
    ClaimStatus,
    Decider,
    EntityType,
    EventType,
    EvidenceStage,
    RegulatoryOutcome,
    ReviewState,
    TermFit,
    TermRole,
    TrialPhase,
    TrialState,
)
from thenwhat.events.paper_facts import (
    PaperKind,
    StudiedIn,
    doi_of,
    pubmed_id_of,
    read_paper,
    record_page,
)
from thenwhat.events.paper_records import PUBMED_PREFIX, paper_reference, stored_paper
from thenwhat.events.trial_facts import (
    AgeGroup,
    Allocation,
    Comparator,
    HowListed,
    Masking,
    MeasureKind,
    ParticipantBasis,
    SponsorKind,
    StudyKind,
    TestKind,
    TrialStateCode,
    is_registry_record,
    read_trial,
    reported_state,
)
from thenwhat.outlets.icons import is_blank_icon, outlet_domain
from thenwhat.sources import mesh
from thenwhat.sources.base import SourceRecord, record_url
from thenwhat.sources.openalex import OpenAlex
from thenwhat.sources.ror import Ror
from thenwhat.sources.terms import SOURCES as LISTED_SOURCES
from thenwhat.terms.candidates import REASON_CODES

SCHEMA_VERSION = 1
# Registries the clients read. Always listed, as their terms ask for attribution.
SOURCES = [
    ("ClinicalTrials.gov", "https://clinicaltrials.gov/"),
    ("Europe PMC", "https://europepmc.org/"),
    ("Crossref", "https://www.crossref.org/"),
]
# Registries with no client yet, listed only when an exported event came from one.
OTHER_REGISTRIES = {"jRCT": "https://jrct.mhlw.go.jp/"}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExportedSource(Strict):
    name: str
    url: str


class ExportedGroup(Strict):
    slug: str
    title: str


class ExportedVertical(Strict):
    slug: str
    title: str
    # The broader area the vertical is filed under, when it has one.
    group: ExportedGroup | None = None


class ExportedRetiredVertical(Strict):
    """A vertical slug renamed or retired after launch, and the vertical that replaces it."""

    slug: str
    successor: str


class ExportedOutlet(Strict):
    """An outlet's own icon, stored by the pipeline so that no page fetches it."""

    # An article's host without a leading www, as the site shows it.
    domain: str
    # The image itself as a data URI; the site never receives an address to fetch.
    icon: str = Field(pattern=r"^data:image/(png|x-icon|gif|jpeg|webp);base64,[A-Za-z0-9+/]+=*$")
    fetched_at: datetime


class ExportedIntervention(Strict):
    name: str
    synonyms: list[str]


class ExportedStatusChange(Strict):
    """The day the status became `code`, by the rules run on what was dated up to then."""

    on: date
    code: ClaimStatus


class ExportedStatus(Strict):
    code: ClaimStatus
    overlay_years: int | None
    updated_at: datetime | None
    explained_by: list[int]
    # Oldest first; the last entry's code is `code`. Absent from exports made before
    # the history was added, so the site treats a missing history as none.
    history: list[ExportedStatusChange] = []


class ExportedArticle(Strict):
    url: str
    outlet: str
    title: str
    published_date: date
    archive_url: str | None


class ExportedPromise(Strict):
    description: str
    parsed_date: date | None
    article_url: str


class ExportedEvent(Strict):
    id: int
    type: EventType
    event_date: date
    date_basis: str | None
    summary: str
    source_name: str
    source_url: str
    trial_id: str | None
    trial_phases: list[TrialPhase]
    trial_state: TrialState | None
    regulatory_outcome: RegulatoryOutcome | None
    # How sure the pipeline is that the event is evidence for the claim, 0 to 1. Always
    # set; optional only so that an export made before it was added is still valid.
    confidence: float | None = None


class ExportedFailureFlag(Strict):
    trial_id: str
    source_url: str


class ExportedMatch(Strict):
    # A registry record matched to the claim, with how sure the pipeline is. The site owns
    # the words: it turns `score` into "High match · 92%" and `reading` into a reason.
    source_name: str
    external_id: str
    url: str | None
    # The probability, 0 to 1, that the record is evidence for the claim.
    score: float
    # "approved" counts toward the status; "candidate" is shown apart and does not.
    state: str
    # How the record was read: "match", "other_indication", "not_a_match", or None.
    reading: str | None
    # Who approved it: "human", "rule", "seed" or "assistant". None for a candidate.
    decided_by: str | None
    # What the record says, in one line: title, conditions, phase, state.
    summary: str | None


# Trial facts (openspec trial-facts): what a registry record says of its trial, read by
# rule. Codes only; the site owns the words. Registry numbers stay strings as written.


class ExportedParticipants(Strict):
    count: int
    basis: ParticipantBasis


class ExportedSponsor(Strict):
    # None when the sponsor is a person.
    name: str | None
    kind: SponsorKind | None


class ExportedPlannedOutcome(Strict):
    measure: str
    time_frame: str | None


class ExportedResultGroup(Strict):
    title: str
    analysed: str | None
    value: str | None
    spread: str | None
    lower: str | None
    upper: str | None


class ExportedComparison(Strict):
    # The titles of the groups compared.
    groups: list[str]
    p_value: str | None
    method: str | None
    test: TestKind | None


class ExportedResultOutcome(Strict):
    title: str
    time_frame: str | None
    unit: str | None
    measure: MeasureKind | None
    # The registry's own words, such as "Standard Deviation".
    spread_kind: str | None
    # How many rows the outcome is reported in. Groups and comparisons are carried only
    # for an outcome reported in one row.
    rows: int
    groups: list[ExportedResultGroup]
    comparisons: list[ExportedComparison]


class ExportedResults(Strict):
    # At most three posted primary outcomes, and how many the record posts.
    outcomes: list[ExportedResultOutcome]
    outcomes_total: int


class ExportedTrialFacts(Strict):
    study_kind: StudyKind | None
    participants: ExportedParticipants | None
    allocation: Allocation | None
    masking: Masking | None
    comparators: list[Comparator]
    healthy_volunteers: bool | None
    age_groups: list[AgeGroup]
    sponsor: ExportedSponsor | None
    # At most three planned primary outcomes, and how many the record plans.
    primary_outcomes: list[ExportedPlannedOutcome]
    primary_outcomes_total: int
    why_stopped: str | None
    results: ExportedResults | None


class ExportedTrial(Strict):
    """One trial behind the claim's approved events. Its match, if any, is the entry in
    `matches` with the same identifier."""

    trial_id: str
    source_name: str
    # The source link of the trial's newest approved event.
    url: str
    # The registry's brief title; None when no registry record is held.
    title: str | None
    phases: list[TrialPhase]
    state: TrialStateCode
    # When the record the facts were read from was fetched.
    facts_as_of: datetime | None
    # None when no registry record is held, as for a trial entered by hand.
    facts: ExportedTrialFacts | None
    # The identifiers of the papers the trial's registry record names for it, each an
    # entry in the claim's `papers`. Empty for a trial with no registry record.
    papers: list[str] = []


# Papers (openspec paper-facts): each paper a claim page lists, once, with the roles it
# plays for the claim and what its index record states. Codes only; the site owns the
# words. Never an abstract, an author or an affiliation.

PaperRole = Literal["origin", "trial_result", "follow_up", "related"]
# The order a paper's roles are listed in, and papers by their first role.
PAPER_ROLES: tuple[PaperRole, ...] = ("origin", "trial_result", "follow_up", "related")


class ExportedPaperRole(Strict):
    role: PaperRole
    # For "trial_result": the trial whose registry record names the paper, and whether
    # the sponsor listed it as reporting results or the registry linked it from PubMed.
    trial_id: str | None = None
    listed: HowListed | None = None
    # For "follow_up": the evidence event the paper is behind.
    event_id: int | None = None
    # For "related" (openspec related-research): the probability, 0 to 1, that the paper
    # is about the claim's intervention and indication, the reasons found by rule as
    # codes, who approved it, and what the search source says of it in one line.
    score: float | None = None
    reasons: list[str] = []
    decided_by: str | None = None
    summary: str | None = None


class ExportedPaperFacts(Strict):
    title: str | None
    journal: str | None
    year: int | None
    # Every kind the record gives, most specific first.
    kinds: list[PaperKind]
    open_access: bool | None
    retracted: bool
    # What the record's subject headings say the study was in; empty when they say
    # neither or the record has none.
    studied_in: list[StudiedIn]


class ExportedPaper(Strict):
    # The DOI in lower case, else "pmid:<number>", else the source's own identifier.
    identifier: str
    # Where a reader can open the paper.
    url: str
    # The index record the facts were read from, when the index holds the paper.
    record_url: str | None
    roles: list[ExportedPaperRole]
    # When the index record was fetched. None, with no facts, for a paper the index
    # does not hold or was not asked for.
    facts_as_of: datetime | None
    facts: ExportedPaperFacts | None


# Background cards (openspec knowledge-cards): what an open vocabulary says of a term
# tied to the claim. Never an input to the status.


class ExportedCardReason(Strict):
    """Why the term was a candidate, found by rule. The site owns the wording."""

    # "filed_by_registry" or "label_equals_name".
    code: str
    # For "filed_by_registry": how many of the claim's approved trials carry the term,
    # and how many trials there were.
    trials: int | None = None
    of: int | None = None
    # For "label_equals_name": the claim's name the term's label equals.
    name: str | None = None


class ExportedCard(Strict):
    # What the term is to the claim: its condition or its intervention.
    kind: TermRole
    # "exact" when the term is the claim's own condition or intervention, "broader"
    # when it names a wider group that includes it.
    fit: TermFit
    label: str
    # The vocabulary publisher's own words, never reworded. None when it gives none.
    definition: str | None
    # The term's record at its source.
    url: str
    # The source's name in `card_sources`.
    source: str
    external_id: str
    # The version of the vocabulary the record was read from, such as a year.
    version: str | None
    # The probability, 0 to 1, of the answer the term check chose for this term.
    score: float
    reasons: list[ExportedCardReason]
    # Who approved the link: "rule", "human" or "assistant".
    decided_by: str
    # When the term's record was read.
    read_at: datetime


class ExportedCardSource(Strict):
    """A source a published card comes from, with what its terms ask for."""

    name: str
    title: str
    # How the source asks to be credited.
    credit: str
    licence: str
    url: str
    terms_url: str
    # Whether its cards may be offered in the open data file under that file's licence.
    in_data_file: bool


class ExportedClaim(Strict):
    slug: str
    headline: str
    summary: str
    vertical: str
    # The kind of intervention, as a configured approach code. The site owns its wording.
    approach: str | None
    intervention: ExportedIntervention
    indication: str
    first_reported_date: date | None
    evidence_stage: EvidenceStage | None
    # True only when a person approved the claim and no assistant decision stands on
    # it, its matches or its events.
    checked_by_person: bool
    status: ExportedStatus
    articles: list[ExportedArticle]
    promises: list[ExportedPromise]
    events: list[ExportedEvent]
    failure_flags: list[ExportedFailureFlag]
    # Approved matches first, then up to five candidates, each with its confidence.
    matches: list[ExportedMatch] = []
    # One per registry identifier among the approved trial events, ordered by identifier.
    trials: list[ExportedTrial] = []
    # Each paper the page lists, once: the origin paper, results papers of the trials
    # above, papers behind approved follow-up events, and approved related papers.
    papers: list[ExportedPaper] = []
    # At most one card for the condition, then one for the intervention.
    background: list[ExportedCard] = []


class ExportedArchived(Strict):
    # A claim the operator took down. Its address answers 410; the reason stays private.
    slug: str
    on: date


class Export(Strict):
    schema_version: int
    generated_at: datetime
    last_checked_at: datetime | None
    # Always false since openspec auto-publish: every approved claim is published, and
    # `checked_by_person` on each claim says whether a person checked it. Kept so a site
    # built from an older export still reads it.
    preview: bool = False
    sources: list[ExportedSource]
    verticals: list[ExportedVertical]
    # Topic addresses that must keep working: each redirects to its successor's.
    retired_verticals: list[ExportedRetiredVertical] = []
    # Icons of the outlets whose articles are exported. An outlet without one is absent.
    outlets: list[ExportedOutlet]
    claims: list[ExportedClaim]
    archived: list[ExportedArchived] = []
    # The sources of the cards in `background`, each once.
    card_sources: list[ExportedCardSource] = []


def _group_of(vertical: str) -> ExportedGroup | None:
    slug = VERTICAL_GROUPS.get(vertical)
    return None if slug is None else ExportedGroup(slug=slug, title=GROUPS[slug])


def export_json_schema() -> dict[str, Any]:
    return Export.model_json_schema(mode="serialization")


def _decided_by_assistant(session: Session, claim: Claim) -> bool:
    """Whether the assistant made any decision that still stands on the claim, its
    matches or its events."""
    if claim.reviewed_by is Decider.ASSISTANT:
        return True
    match_ids = select(EntityMatch.id).join(Entity).where(Entity.claim_id == claim.id)
    return bool(
        session.scalar(
            select(EntityMatch.id).where(
                EntityMatch.id.in_(match_ids), EntityMatch.reviewed_by == Decider.ASSISTANT
            )
        )
        or session.scalar(
            select(EvidenceEvent.id).where(
                EvidenceEvent.claim_id == claim.id,
                EvidenceEvent.reviewed_by == Decider.ASSISTANT,
            )
        )
    )


CANDIDATES_SHOWN = 5


def _reading(session: Session, match: EntityMatch) -> str | None:
    scored = latest_scoring(session, match)
    if scored is None or scored.output is None:
        return None
    choice = scored.output.get("choice")
    return choice if isinstance(choice, str) else None


def _matches(session: Session, claim: Claim) -> list[ExportedMatch]:
    """The claim's approved matches, then its best pending candidates. Rejected ones are
    never exported. Openspec auto-publish: "Confidence is shown with every match"."""
    found = list(
        session.scalars(
            select(EntityMatch)
            .join(Entity)
            .where(
                Entity.claim_id == claim.id,
                EntityMatch.review_state.in_([ReviewState.APPROVED, ReviewState.PENDING]),
                # Papers found by search and organisations are not registry matches of
                # the claim. An approved paper is exported in `papers`, with the role
                # "related" (openspec related-research); organisations are not exported.
                EntityMatch.source_name.not_in([OpenAlex.name, Ror.name]),
            )
            .order_by(EntityMatch.score.desc(), EntityMatch.id)
        )
    )
    approved = [m for m in found if m.review_state is ReviewState.APPROVED]
    pending = [m for m in found if m.review_state is ReviewState.PENDING][:CANDIDATES_SHOWN]
    return [
        ExportedMatch(
            source_name=match.source_name,
            external_id=match.external_id,
            url=record_url(match.source_name, match.external_id),
            score=round(match.score, 4),
            state="approved" if match.review_state is ReviewState.APPROVED else "candidate",
            reading=_reading(session, match),
            decided_by=(
                match.reviewed_by.value
                if match.review_state is ReviewState.APPROVED and match.reviewed_by
                else None
            ),
            summary=match.record_summary,
        )
        for match in [*approved, *pending]
    ]


class _Papers:
    """The claim's papers as they are found, one per identifier. A paper referred to by
    its DOI in one place and by its PubMed number in another is one paper once its
    index record is stored, because the record gives both."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.found: dict[str, ExportedPaper] = {}

    def add(
        self,
        role: ExportedPaperRole,
        *,
        doi: str | None = None,
        pubmed_id: str | None = None,
        identifier: str | None = None,
        url: str | None = None,
    ) -> str | None:
        """Give the paper this role and return its identifier, or None when nothing
        identifies it."""
        row = stored_paper(self.session, doi=doi, pubmed_id=pubmed_id, identifier=identifier)
        key = _paper_identifier(row, doi=doi, pubmed_id=pubmed_id, identifier=identifier)
        if key is None:
            return None
        if key not in self.found:
            held = row is not None and row.payload is not None
            self.found[key] = ExportedPaper(
                identifier=key,
                url=_paper_url(key, url),
                record_url=record_page(row.payload) if row and row.payload else None,
                roles=[],
                facts_as_of=row.fetched_at if row and held else None,
                facts=ExportedPaperFacts.model_validate(asdict(read_paper(row.payload)))
                if row and row.payload
                else None,
            )
        self.found[key].roles.append(role)
        return key

    def listed(self) -> list[ExportedPaper]:
        """Each paper with its roles in their fixed order, and the papers by their
        first role, otherwise as found."""
        for paper in self.found.values():
            paper.roles.sort(key=lambda role: PAPER_ROLES.index(role.role))
        return sorted(self.found.values(), key=lambda p: PAPER_ROLES.index(p.roles[0].role))


def _paper_identifier(
    row: PaperRecord | None, *, doi: str | None, pubmed_id: str | None, identifier: str | None
) -> str | None:
    payload = row.payload if row is not None else None
    number = (pubmed_id_of(payload) if payload else None) or pubmed_id
    return (
        (doi_of(payload) if payload else None)
        or (doi.lower() if doi else None)
        or (f"{PUBMED_PREFIX}{number}" if number else None)
        or identifier
    )


def _paper_url(identifier: str, url: str | None) -> str:
    if identifier.startswith("10."):
        return f"https://doi.org/{identifier}"
    if identifier.startswith(PUBMED_PREFIX):
        return f"https://pubmed.ncbi.nlm.nih.gov/{identifier.removeprefix(PUBMED_PREFIX)}/"
    assert url is not None, "a paper with neither a DOI nor a PubMed number has its own link"
    return url


def _collect_papers(
    session: Session, claim: Claim, events: list[EvidenceEvent], papers: _Papers
) -> None:
    """The origin paper, the papers behind approved follow-up events and the approved
    related papers. Results papers are added as each trial is read."""
    for entity in session.scalars(
        select(Entity).where(Entity.claim_id == claim.id).order_by(Entity.id)
    ):
        approved = list(
            session.scalars(
                select(EntityMatch)
                .where(
                    EntityMatch.entity_id == entity.id,
                    EntityMatch.review_state == ReviewState.APPROVED,
                )
                .order_by(EntityMatch.score.desc(), EntityMatch.id)
            )
        )
        if entity.is_origin_paper and approved and approved[0].external_id.startswith("10."):
            papers.add(ExportedPaperRole(role="origin"), doi=approved[0].external_id)
        if entity.type is not EntityType.INTERVENTION:
            continue
        for match in approved:
            if match.source_name != OpenAlex.name:
                continue
            doi, _ = paper_reference(match.external_id)
            papers.add(
                ExportedPaperRole(
                    role="related",
                    score=round(match.score, 4),
                    reasons=list(match.reasons),
                    decided_by=match.reviewed_by.value if match.reviewed_by else None,
                    summary=match.record_summary,
                ),
                doi=doi,
                identifier=None if doi else f"openalex:{match.external_id}",
                url=record_url(match.source_name, match.external_id),
            )
    for event in events:
        if event.type is EventType.FOLLOWUP_PAPER:
            doi, pubmed_id = paper_reference(event.external_id)
            papers.add(
                ExportedPaperRole(role="follow_up", event_id=event.id),
                doi=doi,
                pubmed_id=pubmed_id,
                identifier=event.external_id,
                url=event.source_url,
            )


def _trials(events: list[EvidenceEvent], papers: _Papers) -> list[ExportedTrial]:
    """One entry per registry identifier among the claim's approved trial events, given
    oldest first. Openspec trial-facts: the facts are read from the most recently fetched
    registry record those events hold; a trial with none is listed without facts."""
    by_trial: dict[str, list[EvidenceEvent]] = {}
    for event in events:
        if event.type in TRIAL_EVENT_TYPES:
            by_trial.setdefault(event.external_id, []).append(event)
    trials: list[ExportedTrial] = []
    for trial_id, held in sorted(by_trial.items()):
        newest = held[-1]
        record = max(
            (event for event in held if is_registry_record(event.raw_payload)),
            key=lambda event: (event.fetched_at, event.id),
            default=None,
        )
        if record is None:
            changes = [event for event in held if event.type is EventType.TRIAL_STATUS_CHANGE]
            state = reported_state(changes[-1].trial_state if changes else None)
            title, facts, facts_as_of = None, None, None
            results: list[str] = []
        else:
            read = read_trial(record.raw_payload)
            state, title, facts_as_of = read.state, read.title, record.fetched_at
            facts = ExportedTrialFacts.model_validate(asdict(read.facts))
            results = [
                key
                for paper in read.results_papers
                if (
                    key := papers.add(
                        ExportedPaperRole(
                            role="trial_result", trial_id=trial_id, listed=paper.listed
                        ),
                        pubmed_id=paper.pubmed_id,
                    )
                )
            ]
        trials.append(
            ExportedTrial(
                trial_id=trial_id,
                source_name=newest.source_name,
                url=newest.source_url,
                title=title,
                phases=[TrialPhase(phase) for phase in newest.trial_phases or []],
                state=state,
                facts_as_of=facts_as_of,
                facts=facts,
                papers=list(dict.fromkeys(results)),
            )
        )
    return trials


def _background(session: Session, claim: Claim) -> list[ExportedCard]:
    """At most one card for the claim's condition and one for its intervention: the
    approved exact link with the highest score or, with none, the approved broader one.

    A link whose source is not accepted in the list of sources gives no card, nor does
    one whose term has no stored record, since a card states when its record was read.
    """
    approved = list(
        session.scalars(
            select(ClaimTerm)
            .where(
                ClaimTerm.claim_id == claim.id,
                ClaimTerm.review_state == ReviewState.APPROVED,
                ClaimTerm.fit.is_not(None),
                ClaimTerm.score.is_not(None),
            )
            .order_by(ClaimTerm.score.desc(), ClaimTerm.id)
        )
    )
    cards: list[ExportedCard] = []
    for role in TermRole:
        for fit in TermFit:  # exact before broader
            card = next(
                (
                    made
                    for term in approved
                    if term.role is role and term.fit is fit
                    if (made := _card(session, term)) is not None
                ),
                None,
            )
            if card is not None:
                cards.append(card)
                break
    return cards


def _card(session: Session, term: ClaimTerm) -> ExportedCard | None:
    listed = LISTED_SOURCES.get(term.source_name)
    record = session.get(TermRecord, (term.source_name, term.external_id))
    if listed is None or not listed.accepted or record is None:
        return None
    assert term.fit is not None and term.score is not None and term.reviewed_by is not None
    read = mesh.describe(
        SourceRecord(
            record.source_name, record.external_id, record.url, record.payload, record.fetched_at
        )
    )
    return ExportedCard(
        kind=term.role,
        fit=term.fit,
        label=read.label or term.label,
        definition=read.definition,
        url=record.url,
        source=term.source_name,
        external_id=term.external_id,
        version=read.version,
        score=round(term.score, 4),
        reasons=[
            ExportedCardReason.model_validate(reason)
            for reason in term.reasons
            if reason.get("code") in REASON_CODES
        ],
        decided_by=term.reviewed_by.value,
        read_at=record.fetched_at,
    )


def _card_sources(claims: list[ExportedClaim]) -> list[ExportedCardSource]:
    used = {card.source for claim in claims for card in claim.background}
    return [
        ExportedCardSource(
            name=listed.name,
            title=listed.title,
            credit=listed.credit,
            licence=listed.licence,
            url=listed.home_url,
            terms_url=listed.terms_url,
            in_data_file=listed.in_data_file,
        )
        for listed in LISTED_SOURCES.values()
        if listed.name in used
    ]


def _outlets(session: Session, claims: list[ExportedClaim]) -> list[ExportedOutlet]:
    domains = {outlet_domain(article.url) for claim in claims for article in claim.articles}
    return [
        ExportedOutlet(
            domain=icon.domain,
            icon=f"data:{icon.media_type};base64,{base64.b64encode(icon.content).decode()}",
            fetched_at=icon.fetched_at,
        )
        for icon in session.scalars(
            select(OutletIcon).where(OutletIcon.domain.in_(domains)).order_by(OutletIcon.domain)
        )
        if icon.content is not None and not is_blank_icon(icon.content)
    ]


def build_export(session: Session, *, now: datetime, no_signal_years: int = 3) -> Export:
    """Everything the site may show, as of now.

    Each claim's status is derived again first, because the no-signal overlay depends
    on today's date. A claim exported for the first time gets its published time.

    Every approved, unarchived claim is included, whoever decided it; a claim the
    assistant decided says it was not checked by a person.
    """
    claims: list[ExportedClaim] = []
    last_checked: datetime | None = None
    for claim in session.scalars(
        select(Claim)
        .where(Claim.review_state == ReviewState.APPROVED, Claim.archived_at.is_(None))
        .order_by(Claim.slug)
    ):
        # Every approved claim is published, whoever decided it (openspec auto-publish).
        # Whether a person checked it is still said, in `checked_by_person`.
        assistant = _decided_by_assistant(session, claim)
        derivation = refresh_status(
            session, claim, as_of=now.date(), now=now, no_signal_years=no_signal_years
        )
        if claim.published_at is None:
            claim.published_at = now
        events = list(
            session.scalars(
                select(EvidenceEvent)
                .where(
                    EvidenceEvent.claim_id == claim.id,
                    EvidenceEvent.review_state == ReviewState.APPROVED,
                )
                .order_by(EvidenceEvent.event_date, EvidenceEvent.id)
            )
        )
        for event in events:
            if last_checked is None or event.fetched_at > last_checked:
                last_checked = event.fetched_at
        articles = articles_of(session, claim)
        article_urls = {article.id: article.url for article in articles}
        intervention = session.scalars(
            select(Entity).where(
                Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION
            )
        ).first()
        assert intervention is not None, "every claim is created with its intervention entity"
        papers = _Papers(session)
        _collect_papers(session, claim, events, papers)
        trials = _trials(events, papers)
        claims.append(
            ExportedClaim(
                slug=claim.slug,
                headline=claim.headline,
                summary=claim.summary,
                vertical=claim.vertical,
                approach=claim.approach,
                intervention=ExportedIntervention(
                    name=intervention.name, synonyms=list(intervention.synonyms)
                ),
                indication=claim.indication,
                first_reported_date=claim.first_reported_date,
                evidence_stage=claim.evidence_stage,
                checked_by_person=claim.reviewed_by is Decider.HUMAN and not assistant,
                status=ExportedStatus(
                    code=derivation.status,
                    overlay_years=derivation.overlay_years,
                    updated_at=claim.status_updated_at,
                    explained_by=list(derivation.explaining_event_ids),
                    history=[
                        ExportedStatusChange(on=change.on, code=change.status)
                        for change in status_history(session, claim)
                    ],
                ),
                articles=[
                    ExportedArticle(
                        url=article.url,
                        outlet=article.outlet,
                        title=article.title,
                        published_date=article.published_date,
                        archive_url=article.archive_url,
                    )
                    for article in articles
                ],
                promises=[
                    ExportedPromise(
                        description=promise.description,
                        parsed_date=promise.parsed_date,
                        article_url=article_urls[promise.source_article_id],
                    )
                    for promise in promises_of(session, claim)
                ],
                events=[
                    ExportedEvent(
                        id=event.id,
                        type=event.type,
                        event_date=event.event_date,
                        date_basis=event.date_basis,
                        summary=event.summary,
                        source_name=event.source_name,
                        source_url=event.source_url,
                        trial_id=event.external_id if event.type in TRIAL_EVENT_TYPES else None,
                        trial_phases=[TrialPhase(phase) for phase in event.trial_phases or []],
                        trial_state=event.trial_state,
                        regulatory_outcome=event.regulatory_outcome,
                        confidence=round(event.confidence, 4),
                    )
                    for event in events
                ],
                matches=_matches(session, claim),
                trials=trials,
                papers=papers.listed(),
                background=_background(session, claim),
                failure_flags=[
                    ExportedFailureFlag(trial_id=flag.trial_external_id, source_url=flag.source_url)
                    for flag in session.scalars(
                        select(FailureFlag)
                        .where(FailureFlag.claim_id == claim.id)
                        .order_by(FailureFlag.id)
                    )
                ],
            )
        )
    session.flush()
    card_sources = _card_sources(claims)
    return Export(
        schema_version=SCHEMA_VERSION,
        generated_at=now,
        last_checked_at=last_checked,
        sources=[
            ExportedSource(name=name, url=url)
            for name, url in [
                *SOURCES,
                *(
                    (name, url)
                    for name, url in OTHER_REGISTRIES.items()
                    if any(event.source_name == name for claim in claims for event in claim.events)
                ),
                # A source a published card comes from is credited like the registries.
                *((source.title, source.url) for source in card_sources),
            ]
        ],
        verticals=[
            ExportedVertical(slug=slug, title=title, group=_group_of(slug))
            for slug, title in VERTICALS.items()
        ],
        retired_verticals=[
            ExportedRetiredVertical(slug=slug, successor=successor)
            for slug, successor in RETIRED_VERTICALS.items()
        ],
        outlets=_outlets(session, claims),
        claims=claims,
        archived=[
            ExportedArchived(slug=claim.slug, on=claim.archived_at.date())
            for claim in session.scalars(
                select(Claim)
                .where(Claim.archived_at.is_not(None), Claim.published_at.is_not(None))
                .order_by(Claim.slug)
            )
            if claim.archived_at is not None
        ],
        card_sources=card_sources,
    )


def write_export(
    session: Session,
    path: Path,
    *,
    now: datetime,
    no_signal_years: int = 3,
) -> Export:
    """Write the export to `path`, replacing any earlier file only once it is complete."""
    export = build_export(session, now=now, no_signal_years=no_signal_years)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(export.model_dump_json(indent=2) + "\n")
    partial.replace(path)
    return export


def write_schema(path: Path) -> None:
    path.write_text(json.dumps(export_json_schema(), indent=2) + "\n")
