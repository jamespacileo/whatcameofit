"""The reading step: a passed link lead's article is read once and becomes a source
article of the claim it reports, or a new claim. Behavior: openspec lead-reading.

Everything that can be settled without the model is settled first: an article that has
become tracked, a claim that has enough articles, an outlet with no name, a page the
page reader does not give, a page with no date or headline. The article's text is held
only while the model reads it. What the read makes is an ordinary source article or an
ordinary claim.

Several outlets report one story, each in its own words, so an article is joined to a
claim that exists whenever a decision says it reports that claim; only otherwise is a new
claim drafted. Reads that run side by side take turns at that point, so two articles on
one story cannot both draft a claim. A new claim with a name is not approved here: it
awaits `thenwhat prepare`, which searches the registries and then decides it by the rule
for drafts, so that no claim is published with a status no search stands behind.
"""

import re
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, and_, exists, func, or_, select
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key, without_tracking
from thenwhat.backfill.link_evaluation import reading_refusal
from thenwhat.backfill.link_screen import (
    CLAIM,
    REGISTRY_TRIAL,
    STRENGTH_TO_READ,
    STRONG,
    TITLE_NAMES_CLAIM,
)
from thenwhat.backfill.link_triage import is_passed
from thenwhat.backfill.outlet_hold import OUTLET_HOLD, asking, keep
from thenwhat.backfill.outlet_kinds import name_of
from thenwhat.backfill.topics import (
    names_one,
    names_only_a_class,
    other_names_of,
    title_names,
)
from thenwhat.backfill.trial_links import PHASE_3, at_least, held_and_linked, linked_to
from thenwhat.claims.entry import (
    MAX_NAMED_CLAIMS,
    EntryError,
    claim_by_slug,
    claims_of_a_named_substance,
    claims_sharing_a_name,
    core_name,
    find_article,
    find_claim,
    free_slug_for,
    named_claims,
    owner_of_rule_slug,
    slug_of_claim_close_to,
    slug_of_claim_covering,
)
from thenwhat.db.models import (
    Claim,
    LinkLead,
    LinkLeadLink,
    LinkShare,
    SourceArticle,
    WorkEntry,
)
from thenwhat.decide.core import Backend, DecisionFailed, stop_if_unreachable
from thenwhat.decide.steps import (
    ESTABLISHED_TREATMENT,
    choose_same_claim,
    choose_vertical,
    kind_of_treatment_report,
    lead_ref,
)
from thenwhat.domain import Decider, ReadOutcome, ReviewState, ScreenOutcome, WorkOutcome
from thenwhat.extract.names import (
    condition_refusal,
    is_a_class,
    is_a_name,
    names_no_product,
)
from thenwhat.extract.page import Page, published_day
from thenwhat.extract.retrieve import (
    READER,
    ArticleRetriever,
    NotAllowed,
    NotNow,
    NotServed,
    Retrieved,
    ThinPage,
)
from thenwhat.extract.schema import Draft
from thenwhat.extract.service import article_from_draft, claim_from_draft, read_article
from thenwhat.llm.client import Llm
from thenwhat.llm.errors import BudgetExceeded, LlmError
from thenwhat.resolve.named import candidates_named_in_article
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceError, SystemTime, Time
from thenwhat.statements.service import StatementChecker, StatementsRun
from thenwhat.work.allowance import Allowances, held_until, holds_under
from thenwhat.work.errors import BackfillError, CannotAsk, SpendCeilingReached
from thenwhat.work.ledger import due_records
from thenwhat.work.steps import TEXT_DOOR, Deferred, Failed, ModelSpend

NO_NAME = "its outlet has no display name"
NO_DATE = "the page gives no publication date"
NO_HEADLINE = "the page gives no headline"
NOT_ALLOWED = "the page reader does not allow the address"
NO_PAGE = "the page could not be retrieved"
# A site that answers "401 Unauthorized" to the page reader for page after page and has
# served it none is refusing the reader, not one page. Batch 1 (2026-11-16) spent 83 of
# its 300 requests on two such outlets. After this many such answers and no page served,
# the outlet's other leads are finished without asking it.
REFUSED_STATUS = 401
REFUSALS_BEFORE_STOPPING = 5
# How long an outlet's 401 answers count. `thenwhat backfill retry-outlet` asks again
# sooner.
REFUSALS_COUNT_FOR = timedelta(days=30)
OUTLET_REFUSES = "not asked: its outlet answered 401 to the page reader"
# The reader says "not now" for a page it could not get by any means. When it says so
# for this many of an outlet's pages in a row, the outlet's other leads are left for a
# later run without being asked. Batch 1 on the Mac mini (2026-11-16) began with forty
# requests for one outlet's pages, every one answered that way, with 300 more of its
# leads next in line: each costs a request of the reader's allowance and reads nothing.
NOT_NOW_BEFORE_LEAVING = 3
# A publisher that blocks automated reading by one route and the next was reached on
# 2026-11-16 by the one route left, with 340 of its leads first in line. A steady stream
# of one outlet's pages is the likeliest way to lose such a route.
OUTLET_JUST_ASKED = "not asked in this run: its outlet was asked a moment ago"
OUTLET_NOT_NOW = "not asked in this run: the page reader could not get its outlet's last pages"
# The reader states a wait with every "not now": seconds for a site it is pacing, hours
# for an outlet it has stopped because the outlet refuses it. Until that wait is over
# the outlet's leads are left without a request, in this run and in every later one.
# The backfill of 2026-11-16 asked two outlets that had banned the reader's machine
# three times in every run. The hold itself is `thenwhat.backfill.outlet_hold`.
OUTLET_STOPPED = "not asked: the page reader says its outlet cannot be asked before"
# Outcomes only a page the reader got can give.
READ_FROM_A_PAGE = (
    ReadOutcome.ADDED_TO_CLAIM,
    ReadOutcome.NEW_CLAIM,
    ReadOutcome.NEEDS_VERTICAL,
    ReadOutcome.NOT_ONE_TREATMENT,
    ReadOutcome.BUSINESS_NEWS,
    ReadOutcome.IDENTITY_UNRESOLVED,
)
# The name a lead's read is recorded under in the usage ledger, apart from articles an
# operator has read, so the funnel can say what reading leads has cost.
LEAD_READING = "extraction:link_lead"
# Held, until its transaction ends, by the one read that is settling which claim its
# article belongs to. A claim another read has just drafted is then there to be found.
CLAIM_IDENTITY_LOCK = 7_468_656_001
# An article joins a candidate claim only when the same-claim decision gives that claim
# more than every other answer together.
SAME_CLAIM_MAJORITY = 0.5


# How a read that would duplicate a claim names that claim in its detail.
NAMES_OVERLAP = "names overlap"
_OVERLAPPING = re.compile(rf"; {NAMES_OVERLAP} ([a-z0-9-]+),")


def reads_naming_claims(session: Session) -> list[tuple[LinkLead, Claim]]:
    """Leads whose read was left identity unresolved because its treatment and condition
    overlap a claim, with that claim, oldest lead first. Such a read is never retried, so
    an operator decides each: fix the claim, or attach or dismiss the article."""
    leads = session.scalars(
        select(LinkLead)
        .where(LinkLead.read_outcome == ReadOutcome.IDENTITY_UNRESOLVED)
        .order_by(LinkLead.id)
    )
    named = [
        (lead, found[1]) for lead in leads if (found := _OVERLAPPING.search(lead.read_detail or ""))
    ]
    claims = {
        claim.slug: claim
        for claim in session.scalars(
            select(Claim).where(Claim.slug.in_({slug for _, slug in named}))
        )
    }
    return [(lead, claims[slug]) for lead, slug in named if slug in claims]


def reads_naming_archived_claims(session: Session) -> list[tuple[LinkLead, Claim]]:
    """The reads `reads_naming_claims` gives whose claim is now archived. A claim
    archived at audit for a fault can then be fixed and unarchived, and its leads read
    again, instead of the reads staying unresolved."""
    return [(lead, claim) for lead, claim in reads_naming_claims(session) if claim.archived_at]


def reads_naming_live_claims(session: Session) -> list[tuple[LinkLead, Claim]]:
    """The reads `reads_naming_claims` gives whose claim is not archived: the article may
    belong to that claim, which only an operator can now say."""
    return [
        (lead, claim) for lead, claim in reads_naming_claims(session) if claim.archived_at is None
    ]


# How a read that the operator or an assistant judged is no report of the claim it
# overlaps says so in its detail. It no longer names the claim as overlapped, so it is
# not listed again.
NOT_A_REPORT_OF = "not a report of"
_DECIDED_BY = {Decider.HUMAN: "the operator", Decider.ASSISTANT: "the assistant"}


class NotAnOverlap(BackfillError):
    """The lead is not a read left unresolved because it overlaps a claim that is not
    archived, or it cannot be settled as asked."""


def overlapping_read(session: Session, lead_id: int) -> tuple[LinkLead, Claim]:
    """The lead, with the claim that is not archived whose treatment and condition its
    read overlaps: one of those `reads_naming_live_claims` lists. Refuses any other."""
    lead = session.get(LinkLead, lead_id)
    named = (
        _OVERLAPPING.search(lead.read_detail or "")
        if lead is not None and lead.read_outcome is ReadOutcome.IDENTITY_UNRESOLVED
        else None
    )
    claim = find_claim(session, named[1]) if named else None
    if lead is None or claim is None:
        raise NotAnOverlap(
            f"Lead {lead_id} is not a read left unresolved because it overlaps a claim."
        )
    if claim.archived_at is not None:
        raise NotAnOverlap(
            f"Lead {lead_id} overlaps {claim.slug}, which is archived: fix and unarchive"
            " the claim, then read the lead again."
        )
    return lead, claim


def _decided(by: Decider, now: datetime) -> str:
    """Who settled an overlapping read and on what day, for the lead's detail. Only the
    operator or an assistant settles one, and an assistant is never recorded as the
    operator."""
    if by not in _DECIDED_BY:
        raise ValueError("An overlapping read is settled by the operator or by an assistant.")
    return f"by {_DECIDED_BY[by]} on {now:%Y-%m-%d}"


def _drafted(lead: LinkLead) -> str:
    """What the lead's read drafted, as its detail says before naming the overlap."""
    return (lead.read_detail or "").split(f"; {NAMES_OVERLAP} ", 1)[0]


def dismiss_overlap(
    session: Session, lead_id: int, *, reason: str, by: Decider, now: datetime
) -> tuple[LinkLead, Claim]:
    """Record that an overlapping read's article is no report of the claim it overlaps,
    as the operator or an assistant judged, with the reason. The lead stays identity
    unresolved, is never read again, points at no claim, and is no longer listed."""
    lead, claim = overlapping_read(session, lead_id)
    decided = _decided(by, now)
    reason = " ".join(reason.split())
    if not reason:
        raise NotAnOverlap("Give a reason for dismissing. It is kept, and never published.")
    lead.read_detail = (
        f"{_drafted(lead)}; {NOT_A_REPORT_OF} {claim.slug}, decided {decided}: {reason}"
    )
    session.flush()
    return lead, claim


@dataclass(frozen=True, slots=True)
class Attached:
    """An overlapping read's article, now a source article of the claim it overlaps."""

    claim: Claim
    article: SourceArticle
    # False when the claim had the address already: the lead was pointed at that article
    # and the page reader was not asked.
    added: bool
    statements: StatementsRun | None = None


@dataclass(frozen=True, slots=True)
class NotAttached:
    """Why an overlapping read's article was not attached. The lead is left as it was."""

    reason: str


@dataclass(frozen=True, slots=True)
class _NoPage:
    """Why the page reader gave no page for a lead, or a page that cannot be used, in
    the words a lead's detail keeps."""

    detail: str


class NothingToRetry(BackfillError):
    pass


def retry_outlet(session: Session, outlet: str) -> int:
    """Put the outlet's leads that it refused with 401, or that were not asked because
    of those refusals, back to not read, and mark their reading stale, so the next run
    asks the page reader for them again. Returns how many. Refuses when the outlet has no
    such lead."""
    refused = or_(
        LinkLead.read_detail == f"{NO_PAGE} (the site answered {REFUSED_STATUS})",
        LinkLead.read_detail.startswith(OUTLET_REFUSES),
    )
    ids = list(
        session.scalars(
            select(LinkLead.id).where(
                LinkLead.outlet == outlet,
                LinkLead.read_outcome == ReadOutcome.CANNOT_BE_READ,
                refused,
            )
        )
    )
    if not ids:
        raise NothingToRetry(f"No lead of '{outlet}' was refused with 401 or left unasked.")
    for lead in session.scalars(select(LinkLead).where(LinkLead.id.in_(ids))):
        lead.read_outcome = None
        lead.read_detail = None
    # Marked stale, as the ledger marks a record whose inputs changed: the entry stays,
    # with its last attempt, until the next run reads the lead again.
    for entry in session.scalars(
        select(WorkEntry).where(
            WorkEntry.record_kind == LinkRead.record_kind,
            WorkEntry.step == LinkRead.name,
            WorkEntry.record_id.in_(ids),
        )
    ):
        entry.stale = True
    session.flush()
    return len(ids)


@dataclass(frozen=True, slots=True)
class HeldOutlet:
    """An outlet the page reader said cannot be asked before a time, and how many of its
    leads are due and wait for that."""

    outlet: str
    until: datetime
    leads: int


def held_outlets(
    session: Session, step: "LinkRead", attempt_limit: int, now: datetime
) -> list[HeldOutlet]:
    """The outlets held now that have leads due, the one with most leads first. Asks
    nothing: the plan says what a run would leave alone."""
    holds = holds_under(session, OUTLET_HOLD, now)
    if not holds:
        return []
    due = dict(
        session.execute(
            due_records(step, attempt_limit)
            .with_only_columns(LinkLead.outlet, func.count())
            .where(LinkLead.outlet.in_(holds))
            .order_by(None)
            .group_by(LinkLead.outlet)
        ).all()
    )
    held = [HeldOutlet(outlet, holds[outlet], leads) for outlet, leads in due.items()]
    return sorted(held, key=lambda one: (-one.leads, one.outlet))


class NotMeasured(BackfillError):
    """No lead may be read yet: triage has not been measured, or a threshold is unset."""


@dataclass(slots=True)
class ReadClient:
    """What the reading step asks through: the page reader for the page, and the model for
    the read. The model's doors are made for the session at hand, because they record
    each call and its cost there."""

    retriever: ArticleRetriever
    allowances: Allowances
    make_llm: Callable[[Session], Llm]
    make_checker: Callable[[Session], StatementChecker]
    make_backend: Callable[[Session], Backend]
    # The registry and the literature source, read by identifier for the trials and
    # papers a page names. None leaves what a page names unrecorded.
    make_research: Callable[[Session], Any] | None = None
    requests_made: int = 0


class LinkRead:
    name = "link_read"
    version = 1
    record_kind = "link_lead"
    model = LinkLead
    # Every page is asked of the page reader, under its one allowance.
    source = READER
    requests_per_record = 1
    # An estimate for the plan: an article's text and the instructions in, a draft out.
    model_spend = ModelSpend(input_tokens=3000, output_tokens=700, door=TEXT_DOOR)
    # Reading publishes, so a run always says how many leads it may read.
    needs_limit = True

    def __init__(
        self,
        *,
        pass_above: float | None,
        reject_below: float | None,
        triage_version: int,
        min_labels: int,
        reads_per_claim: int,
        vertical_accept_above: float,
        approve_drafts_by_rule: bool,
        same_claim_accept_above: float = 0.6,
        treatment_accept_above: float = 0.5,
        topic_terms: Sequence[str] = (),
        match_reject_below: float = 0.0,
        match_accept_above: float = 0.0,
        outlet_gap_seconds: float = 0.0,
        read_since: date | None = None,
        trial_set: str | None = None,
        only_trial_set: bool = False,
        least_strength: str = STRONG,
        time: Time | None = None,
    ) -> None:
        # The set of trials being worked, if the operator named one (openspec
        # trial-report-links). A held lead linked to it by an exact or strong link is
        # read, and the leads so linked are read first, phase 3 before the rest. With
        # `only_trial_set`, no other lead is read: only those linked to the set at
        # `least_strength` or better. A lead triage rejected is never read.
        self.trial_set = trial_set
        self.only_trial_set = only_trial_set and trial_set is not None
        self._set_strengths = at_least(least_strength)
        if trial_set is not None:
            linked_to(STRENGTH_TO_READ, trial_set, year=0)  # refuses a set it does not know
        self.pass_above = pass_above
        self.reject_below = reject_below
        self.triage_version = triage_version
        self.min_labels = min_labels
        self.reads_per_claim = reads_per_claim
        self.vertical_accept_above = vertical_accept_above
        self.same_claim_accept_above = same_claim_accept_above
        self.treatment_accept_above = treatment_accept_above
        # The words of the operator's topics. A lead whose title names one is read first,
        # and is read when triage held it as well as when triage passed it.
        self._names_a_topic = title_names(topic_terms)
        self._topic_terms = tuple(topic_terms)
        self.approve_drafts_by_rule = approve_drafts_by_rule
        # The rules `thenwhat resolve` decides candidates by, for those a page names.
        self.match_reject_below = match_reject_below
        self.match_accept_above = match_accept_above
        self._time = time or SystemTime()
        # How many of each outlet's pages the reader has just said it cannot get, one
        # after another, in this run. Kept for the run only.
        self._not_now: dict[str, int] = {}
        # Only leads first shared on or after this day are read; None reads any.
        self.read_since = read_since
        # The least time between two pages asked of one outlet in this run, and when
        # each outlet was last asked.
        self._outlet_gap = outlet_gap_seconds
        self._last_asked: dict[str, float] = {}
        # A run's workers share this step, so they share what it knows of each outlet.
        self._outlets = threading.Lock()

    # --- which leads, and in what order ---------------------------------------------

    def scope(self) -> ColumnElement[bool]:
        """Leads that screening left in scope and triage passed at the two thresholds,
        and leads whose title names one of the operator's topics that triage held: the
        topic is to be covered in full, and the check after the read says what each
        article turned out to be. A lead triage rejected is never read. While either
        threshold is unset, none."""
        readable = is_passed(self.pass_above, self.reject_below)
        if (
            self._names_a_topic is not None
            and self.pass_above is not None
            and self.reject_below is not None
        ):
            held_on_a_topic = and_(
                self._names_a_topic,
                LinkLead.triage_score.is_not(None),
                LinkLead.triage_score >= self.reject_below,
            )
            readable = or_(readable, held_on_a_topic)
        if (
            self.trial_set is not None
            and self.pass_above is not None
            and self.reject_below is not None
        ):
            readable = or_(
                readable, held_and_linked(self.trial_set, self.reject_below, year=self._year())
            )
        in_scope = and_(LinkLead.screen_outcome == ScreenOutcome.IN_SCOPE, readable)
        if self.only_trial_set:
            in_scope = and_(
                in_scope, linked_to(self._set_strengths, self.trial_set, year=self._year())
            )
        if self.read_since is not None:
            since = datetime.combine(self.read_since, datetime.min.time(), tzinfo=UTC)
            in_scope = and_(in_scope, LinkLead.first_shared_at >= since)
        return in_scope

    def inputs(self, record: LinkLead) -> dict[str, Any]:
        return {"key": record.url_key}

    def _year(self) -> int:
        """The calendar year the rolling set of trials is chosen in: the step's clock's."""
        return self._time.now().year

    def first(self) -> ColumnElement[bool] | None:
        """The leads whose title names one of the operator's topics come first."""
        return self._names_a_topic

    def order(self) -> list[ColumnElement[Any]]:
        """After those of a topic: the leads with an exact or strong link to a trial of
        the set being worked, those to its phase 3 trials first; then those so linked
        to any other trial; then the leads with any link to a registry trial; then the
        most shared."""
        linked = exists().where(
            LinkLeadLink.link_lead_id == LinkLead.id,
            LinkLeadLink.record_kind == REGISTRY_TRIAL,
        )
        shared = (
            select(func.coalesce(func.sum(LinkShare.score), 0))
            .where(LinkShare.link_lead_id == LinkLead.id)
            .scalar_subquery()
        )
        of_the_set: list[ColumnElement[Any]] = []
        if self.trial_set is not None:
            of_the_set = [
                linked_to(
                    STRENGTH_TO_READ, self.trial_set, phase=PHASE_3, year=self._year()
                ).desc(),
                linked_to(STRENGTH_TO_READ, self.trial_set, year=self._year()).desc(),
            ]
            if self._set_strengths != STRENGTH_TO_READ:
                of_the_set.append(
                    linked_to(
                        self._set_strengths, self.trial_set, phase=PHASE_3, year=self._year()
                    ).desc()
                )
        return [*of_the_set, linked_to(STRENGTH_TO_READ).desc(), linked.desc(), shared.desc()]

    def check_ready(self, session: Session) -> None:
        """Refuse to read anything until triage has been measured (openspec
        lead-evaluation): enough leads carry a person's label at the current version of
        triage, and both thresholds are set."""
        refusal = reading_refusal(
            session,
            version=self.triage_version,
            min_labels=self.min_labels,
            pass_above=self.pass_above,
            reject_below=self.reject_below,
        )
        if refusal is not None:
            raise NotMeasured(refusal)

    # --- one lead ---------------------------------------------------------------------

    def _finish(
        self, record: LinkLead, outcome: ReadOutcome, detail: str | None = None
    ) -> WorkOutcome:
        record.read_outcome = outcome
        record.read_detail = detail
        made = outcome in (ReadOutcome.ADDED_TO_CLAIM, ReadOutcome.NEW_CLAIM)
        return WorkOutcome.DONE if made else WorkOutcome.NOTHING_FOUND

    def _tracked_claim(self, session: Session, record: LinkLead) -> int | None:
        """The claim that has this address as a source article, looked for again now:
        screening's answer may be old."""
        for claim_id, url in session.execute(select(SourceArticle.claim_id, SourceArticle.url)):
            if article_key(url) == record.url_key:
                return claim_id
        return None

    def _outlet_refusals(self, session: Session, outlet: str, now: datetime) -> int | None:
        """How many of the outlet's pages answered 401 to the page reader in the last
        REFUSALS_COUNT_FOR, when that is at least REFUSALS_BEFORE_STOPPING and the reader
        got none of its pages. None while the outlet may still be asked. Pages refused
        for another reason, or answered with another status, do not count either way.
        Older answers lapse, so a site that starts serving the reader is asked again."""
        refused_detail = f"{NO_PAGE} (the site answered {REFUSED_STATUS})"
        refused = (
            session.scalar(
                select(func.count())
                .select_from(LinkLead)
                .join(
                    WorkEntry,
                    and_(
                        WorkEntry.record_kind == self.record_kind,
                        WorkEntry.record_id == LinkLead.id,
                        WorkEntry.step == self.name,
                    ),
                )
                .where(
                    LinkLead.outlet == outlet,
                    LinkLead.read_detail == refused_detail,
                    WorkEntry.last_attempt_at >= now - REFUSALS_COUNT_FOR,
                )
            )
            or 0
        )
        if refused < REFUSALS_BEFORE_STOPPING:
            return None
        served = session.scalar(
            select(LinkLead.id)
            .where(LinkLead.outlet == outlet, LinkLead.read_outcome.in_(READ_FROM_A_PAGE))
            .limit(1)
        )
        return refused if served is None else None

    def _has_enough(self, session: Session, record: LinkLead) -> str | None:
        """Why the lead is held, when every claim its title names already has enough
        articles and the lead was shared no earlier than the claim was first reported."""
        claim_ids = list(
            session.scalars(
                select(LinkLeadLink.record_id).where(
                    LinkLeadLink.link_lead_id == record.id,
                    LinkLeadLink.record_kind == CLAIM,
                    LinkLeadLink.reason == TITLE_NAMES_CLAIM,
                )
            )
        )
        if not claim_ids:
            return None
        shared = record.first_shared_at.date()
        held: list[str] = []
        for claim_id in claim_ids:
            claim = session.get(Claim, claim_id)
            if claim is None:
                return None
            articles = session.scalar(
                select(func.count())
                .select_from(SourceArticle)
                .where(SourceArticle.claim_id == claim_id)
            )
            earlier = claim.first_reported_date is None or shared < claim.first_reported_date
            if (articles or 0) < self.reads_per_claim or earlier:
                return None
            held.append(claim.slug)
        return f"the claim it names has enough articles: {', '.join(held)}"

    def _named_on_the_page(
        self, session: Session, claim: Claim, page: Page | None, client: ReadClient, now: datetime
    ) -> str | None:
        """Record the trials and papers the article's page names as candidates of the
        claim, read by their identifiers and decided by the resolver's own rules. Being
        named approves nothing. Returns why they were not recorded, when they were not:
        the claim and its article stand either way."""
        if page is None or client.make_research is None:
            return None
        if not (page.registry_numbers or page.dois):
            return None
        research = client.make_research(session)
        try:
            candidates_named_in_article(
                session,
                claim,
                registry_numbers=page.registry_numbers,
                # With no literature source configured, papers are left unrecorded.
                dois=page.dois if research.papers is not None else (),
                registry=research.registry,
                papers=research.papers,
                backend=client.make_backend(session),
                now=now,
                reject_below=self.match_reject_below,
                accept_trial_above=self.match_accept_above,
                accept_paper_above=self.match_accept_above,
            )
        except CannotAsk:
            raise
        except (DecisionFailed, SourceError) as failure:
            session.flush()
            return f"the records its page names were not recorded: {failure}"
        return None

    def _claim_it_reports(
        self, session: Session, record: LinkLead, draft: Draft, client: ReadClient, now: datetime
    ) -> tuple[str | None, str | None]:
        """Choose among named candidates using their summaries as well as their names.

        Even equal names are candidates only: a generic category can hide different
        products. The single bounded decision is logged either way.
        """
        names = [draft.intervention, *draft.intervention_synonyms]
        # A topic's list knows a drug's brand and generic names; a claim under any of
        # them is a candidate, though the names share no word. A name's core, without
        # its dose, schedule, form or "-assisted ..." therapy, finds candidates too:
        # "MDMA-assisted psychotherapy" shares no whole word with "MDMA".
        cores = [core for name in names if (core := core_name(name))]
        looked_for = [*names, *cores, *other_names_of(names)]
        candidates = claims_sharing_a_name(session, looked_for, indication=draft.indication)
        linked_by_title = named_claims(
            session,
            list(
                session.scalars(
                    select(LinkLeadLink.record_id).where(
                        LinkLeadLink.link_lead_id == record.id,
                        LinkLeadLink.record_kind == CLAIM,
                        LinkLeadLink.reason == TITLE_NAMES_CLAIM,
                    )
                )
            ),
        )
        offered = {claim.slug for claim in candidates}
        candidates += [claim for claim in linked_by_title if claim.slug not in offered]
        candidates = candidates[:MAX_NAMED_CLAIMS]
        # A claim filed under a substance the registry of substances gives one of these
        # names (a brand, a code) is a candidate too. These are added after the cut, so
        # none takes the place of a claim offered without them.
        offered = {claim.slug for claim in candidates}
        candidates += [
            claim
            for claim in claims_of_a_named_substance(
                session, looked_for, indication=draft.indication
            )
            if claim.slug not in offered
        ]
        # The claim with the slug a new claim would be given has this treatment and
        # condition by its own words, written alike or not ("alcohol-use" and "alcohol
        # use"), so it is always offered, beyond any cut.
        # An archived owner is never joined, whichever way it was found: the read is
        # left overlapping it, and listed with it, until it is fixed and unarchived.
        owner = owner_of_rule_slug(session, draft.intervention, draft.indication)
        if owner is not None and owner.archived_at is not None:
            candidates = [claim for claim in candidates if claim.slug != owner.slug]
        elif owner is not None and owner.slug not in {claim.slug for claim in candidates}:
            candidates += named_claims(session, [owner.id])
        if not candidates:
            return None, None
        answer = choose_same_claim(
            session,
            client.make_backend(session),
            ref=lead_ref(record.id),
            intervention=draft.intervention,
            indication=draft.indication,
            summary=draft.summary,
            candidates=candidates,
            now=now,
        )
        # Two tests, both measured on the first reads (openspec lead-reading). That the
        # article reports one of the candidates must be likely enough: the decision
        # gives "none of these" 0.99 when the condition is another one and 0.40 or less
        # when it is the same story, whatever it gives each candidate. And one candidate
        # must be likelier than all other answers together, so that two claims for two
        # conditions of one drug are never settled by a near tie.
        one_of_them = 1 - answer.none_probability
        if (
            answer.likeliest is None
            or one_of_them < self.same_claim_accept_above
            or answer.likeliest_probability < SAME_CLAIM_MAJORITY
        ):
            return None, None
        return answer.likeliest, (
            f"read as {draft.intervention} for {draft.indication}; the same claim by "
            f"decision at {answer.likeliest_probability:.2f}, none of the candidates at "
            f"{answer.none_probability:.2f}"
        )

    def run(
        self, session: Session, record: LinkLead, client: ReadClient
    ) -> WorkOutcome | Failed | Deferred:
        now = self._time.now()
        claim_id = self._tracked_claim(session, record)
        if claim_id is not None:
            # No longer a lead to read: it leaves the step's scope as already tracked.
            record.screen_outcome = ScreenOutcome.ALREADY_TRACKED
            record.claim_id = claim_id
            return WorkOutcome.NOTHING_FOUND
        enough = self._has_enough(session, record)
        if enough is not None:
            return self._finish(record, ReadOutcome.ENOUGH_ARTICLES, enough)
        outlet = name_of(record.outlet)
        if outlet is None:
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, NO_NAME)

        refusals = self._outlet_refusals(session, record.outlet, now)
        if refusals is not None:
            return self._finish(
                record,
                ReadOutcome.CANNOT_BE_READ,
                f"{OUTLET_REFUSES} for {refusals} pages and served none",
            )

        # One request at a time for an outlet, in this process or any other, from the
        # look at its hold to the reader's answer: a worker never asks an outlet while
        # another's request may be about to stop it.
        with asking(session, record.outlet):
            page = self._ask_for_the_page(session, record, client, now)
        if isinstance(page, _NoPage):
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, page.detail)
        if isinstance(page, Deferred):
            return page
        return self._read(session, record, client, now, outlet, page)

    def _ask_for_the_page(
        self, session: Session, record: LinkLead, client: ReadClient, now: datetime
    ) -> Retrieved | _NoPage | Deferred:
        """The lead's page from the page reader, or why there is none: the reader gave
        none (`_NoPage`), or the outlet may not be asked for now (`Deferred`). Nothing
        is written on the lead. Run while this worker holds the outlet's turn."""
        held = held_until(session, OUTLET_HOLD + record.outlet, now)
        if held is not None:
            # The reader said when this outlet may be asked again, in this run or an
            # earlier one. Until then: no request, no allowance, no attempt.
            return Deferred(f"{OUTLET_STOPPED} {held:%Y-%m-%d %H:%M} UTC: {record.outlet}")

        # The page reader is asked for the page. Whether the outlet may be asked, and how
        # often, is the reader's to decide; the pipeline acts on its answer.
        # Decided and noted in one step: two workers must not both find the outlet free.
        with self._outlets:
            if self._not_now.get(record.outlet, 0) >= NOT_NOW_BEFORE_LEAVING:
                # The reader could not get this outlet's last pages. Its other leads are
                # left for a later run without asking: no request, no allowance, no
                # attempt.
                return Deferred(f"{OUTLET_NOT_NOW}: {record.outlet}")
            asked_at = self._last_asked.get(record.outlet)
            if (
                self._outlet_gap > 0
                and asked_at is not None
                and self._time.monotonic() - asked_at < self._outlet_gap
            ):
                # One outlet's pages are not asked for back to back. The lead stays due.
                return Deferred(f"{OUTLET_JUST_ASKED}: {record.outlet}")
            self._last_asked[record.outlet] = self._time.monotonic()
        client.allowances.claim(READER)
        client.requests_made += 1
        try:
            retrieved = client.retriever.retrieve(record.url)
        except NotNow as later:
            # The site has not refused: it cannot be asked just now. The lead stays due
            # with no attempt counted, and the run goes on with other leads.
            with self._outlets:
                self._not_now[record.outlet] = self._not_now.get(record.outlet, 0) + 1
            if later.retry_after_seconds:
                # Kept in its own short transaction, as a claim on an allowance is, and
                # before the outlet's turn is given up: the next worker finds it.
                keep(client.allowances, record.outlet, now, later.retry_after_seconds)
            return Deferred(str(later))
        except NotAllowed as refused:
            return _NoPage(f"{NOT_ALLOWED}: {refused.reason}")
        except NotServed as missing:
            return _NoPage(f"{NO_PAGE} (the site answered {missing.status})")
        except ThinPage:
            return _NoPage("too little article text")
        # The reader got a page from this outlet: it can be asked again.
        with self._outlets:
            self._not_now.pop(record.outlet, None)
        return retrieved

    def _read(
        self,
        session: Session,
        record: LinkLead,
        client: ReadClient,
        now: datetime,
        outlet: str,
        retrieved: Retrieved,
    ) -> WorkOutcome | Failed | Deferred:
        """What the page the reader gave becomes: a source article, a new claim, or the
        reason it is neither."""
        page = retrieved.page
        dated = _date_and_headline(retrieved)
        if isinstance(dated, _NoPage):
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, dated.detail)
        day, headline = dated

        # The one model read. From here a failure is returned, not raised, so that the
        # call's cost and any logged decision stay recorded.
        checker = client.make_checker(session)
        try:
            draft = read_article(
                client.make_llm(session), checker, retrieved.text, purpose=LEAD_READING
            )
        except BudgetExceeded as ceiling:
            raise SpendCeilingReached(str(ceiling)) from None
        except CannotAsk:
            raise
        except LlmError as failure:
            return Failed(str(failure))
        # A class of treatments is every member of it, not one: "GLP-1 receptor agonists".
        # The name the read gave says so by rule, so no decision is paid for.
        if (
            is_a_class(draft.intervention)
            or names_only_a_class([draft.intervention])
            or names_no_product(draft.intervention, draft.indication)
        ):
            return self._finish(
                record,
                ReadOutcome.NOT_ONE_TREATMENT,
                f"{draft.intervention} for {draft.indication}; a class of treatments, not one",
            )
        # A claim is about one condition of people: not "Cancer", not a cat's illness.
        refused_condition = condition_refusal(draft.indication)
        if refused_condition is not None:
            return self._finish(
                record,
                ReadOutcome.NOT_ONE_TREATMENT,
                f"{draft.intervention} for {draft.indication}; {refused_condition}",
            )
        # A claim is one treatment for one condition. Triage sees only a headline, so what
        # the article turned out to be is asked here, of the read's own headline and
        # summary, before anything is joined or drafted. A treatment long in use is
        # wanted as much as a new one: its trials and approval are what came of it.
        try:
            report = kind_of_treatment_report(
                session,
                client.make_backend(session),
                ref=lead_ref(record.id),
                headline=draft.headline,
                summary=draft.summary,
                intervention=draft.intervention,
                indication=draft.indication,
                now=now,
            )
        except DecisionFailed as refused:
            stop_if_unreachable(refused)
            session.flush()
            return Failed(str(refused))
        if report.one_treatment_probability < self.treatment_accept_above:
            return self._finish(
                record,
                ReadOutcome.NOT_ONE_TREATMENT,
                f"{draft.intervention} for {draft.indication}; about one treatment for "
                f"one condition at {report.one_treatment_probability:.2f}",
            )
        # Business news is about one treatment, but not about what it does: its price,
        # supply, sales, a lawsuit. Two rules, both the operator's (2026-11-15). It never
        # starts a claim: a claim rests on something reported of the treatment. And a
        # topic is covered by evidence, safety, new uses and approvals only, so on a
        # topic it does not join a claim either. The lead is on a topic when its title
        # or the treatment the read names holds one of the topic's words: a link is
        # often shared under a title that names nothing.
        business = report.evidence_probability < self.treatment_accept_above
        on_a_topic = any(
            names_one(text, self._topic_terms)
            for text in (record.title, draft.intervention, *draft.intervention_synonyms)
        )
        if business and on_a_topic:
            return self._finish(
                record,
                ReadOutcome.BUSINESS_NEWS,
                f"{draft.intervention} for {draft.indication}; on a topic, and about what "
                f"the treatment does at {report.evidence_probability:.2f}",
            )
        if business:
            established = "business news about a treatment"
        elif report.kind == ESTABLISHED_TREATMENT:
            established = "an established treatment in the news"
        else:
            established = None
        address = without_tracking(record.url)
        # One read at a time from here to the end of its transaction: whichever claim
        # another read has just made for this story is found, not made again.
        session.execute(select(func.pg_advisory_xact_lock(CLAIM_IDENTITY_LOCK)))
        try:
            existing, how = self._claim_it_reports(session, record, draft, client, now)
            if existing is not None:
                claim = claim_by_slug(session, existing)
                _, _, note = self._join(
                    session, record, client, now, claim, draft, checker, retrieved, outlet, dated
                )
                detail = "; ".join(part for part in (established, how, note) if part) or None
                return self._finish(record, ReadOutcome.ADDED_TO_CLAIM, detail)

            # A claim for the same treatment and condition, as named or once dose,
            # schedule and form are left out, means a new claim would duplicate it.
            # So does a claim that has the slug the rule would give it: the slug is made
            # from the same words. The backfill of 2026-11-16 recorded such a read as
            # failed when the slug was refused.
            owner = owner_of_rule_slug(session, draft.intervention, draft.indication)
            collision = (
                slug_of_claim_covering(session, draft.intervention, draft.indication)
                or slug_of_claim_close_to(session, draft.intervention, draft.indication)
                or (owner.slug if owner is not None else None)
            )
            if collision is not None:
                # The names are already taken, but identity was not established. Neither
                # force the article onto that claim nor pay to retry an unchanged read.
                return self._finish(
                    record,
                    ReadOutcome.IDENTITY_UNRESOLVED,
                    f"{draft.intervention} for {draft.indication}; {NAMES_OVERLAP} {collision}, "
                    "but the same treatment and condition were not established, so no "
                    "claim was drafted",
                )
            if business:
                return self._finish(
                    record,
                    ReadOutcome.BUSINESS_NEWS,
                    f"{draft.intervention} for {draft.indication}; no claim to join, and "
                    f"about what the treatment does at {report.evidence_probability:.2f}",
                )
            slug = free_slug_for(session, draft.intervention, draft.indication)
            vertical, probability = choose_vertical(
                session,
                client.make_backend(session),
                ref=lead_ref(record.id),
                intervention=draft.intervention,
                indication=draft.indication,
                summary=draft.summary,
                now=now,
            )
            if probability < self.vertical_accept_above:
                return self._finish(
                    record,
                    ReadOutcome.NEEDS_VERTICAL,
                    f"{draft.intervention} for {draft.indication}; the nearest vertical was "
                    f"{vertical} at {probability:.2f}",
                )
            extracted = claim_from_draft(
                session,
                checker,
                draft,
                text=retrieved.text,
                slug=slug,
                vertical=vertical,
                url=address,
                outlet=outlet,
                title=headline,
                published_date=day,
                archive_url=retrieved.archive_url,
                now=now,
            )
            if self.approve_drafts_by_rule and not is_a_name(draft.intervention):
                # A description in place of a name is rejected now, as for any draft: no
                # registry search would change that. A named claim stays pending until
                # `thenwhat prepare` has searched the registries and decides it.
                record_decision(extracted.claim, ReviewState.REJECTED, by=Decider.RULE, now=now)
        except (EntryError, DecisionFailed) as refused:
            if isinstance(refused, DecisionFailed):
                stop_if_unreachable(refused)
            session.flush()
            return Failed(str(refused))
        article = find_article(session, extracted.claim, address)
        record.claim_id = extracted.claim.id
        record.source_article_id = article.id if article else None
        note = self._named_on_the_page(session, extracted.claim, page, client, now)
        detail = "; ".join(part for part in (established, note) if part) or None
        return self._finish(record, ReadOutcome.NEW_CLAIM, detail)

    def _join(
        self,
        session: Session,
        record: LinkLead,
        client: ReadClient,
        now: datetime,
        claim: Claim,
        draft: Draft,
        checker: StatementChecker,
        retrieved: Retrieved,
        outlet: str,
        dated: tuple[date, str],
    ) -> tuple[SourceArticle, StatementsRun, str | None]:
        """Make the article that was read a source article of a claim that exists, and
        point the lead at both: the outlet's display name, the page's own headline and
        publication day, the hash of its text, its reported statements, and the trials
        and papers its page names. Returns the article, what became of its statements,
        and why what the page names was not recorded, when it was not."""
        day, headline = dated
        article, statements = article_from_draft(
            session,
            checker,
            claim,
            draft,
            text=retrieved.text,
            url=without_tracking(record.url),
            outlet=outlet,
            title=headline,
            published_date=day,
            archive_url=retrieved.archive_url,
            now=now,
        )
        record.claim_id, record.source_article_id = claim.id, article.id
        note = self._named_on_the_page(session, claim, retrieved.page, client, now)
        return article, statements, note

    def attach(
        self,
        session: Session,
        record: LinkLead,
        claim: Claim,
        client: ReadClient,
        *,
        by: Decider,
    ) -> Attached | NotAttached | Deferred:
        """Attach an overlapping read's article to the claim it overlaps, as the read
        would have had the decision said the article reports that claim: the operator or
        an assistant has said so instead (openspec lead-reading).

        Nothing of the first read's page was kept, so the page reader is asked again,
        under the rules of any read: the outlet's hold and turn, the gap between two of
        its pages, an outlet that refuses the reader, and the reader's allowance. The
        headline and the publication day are the page's own, never the title the link
        was shared under or the time it was shared. The claim's review state and audit
        hold are left as they are. A lead that cannot be attached is left as it was."""
        now = self._time.now()
        decided = _decided(by, now)
        if claim.review_state is not ReviewState.APPROVED or claim.archived_at is not None:
            state = "archived" if claim.archived_at is not None else claim.review_state.value
            return NotAttached(
                f"{claim.slug} is {state}: an article is attached only to an approved claim"
                " that is not archived"
            )
        drafted = _drafted(record)
        for article in session.scalars(
            select(SourceArticle).where(SourceArticle.claim_id == claim.id)
        ):
            if article_key(article.url) == record.url_key:
                record.claim_id, record.source_article_id = claim.id, article.id
                self._finish(
                    record,
                    ReadOutcome.ADDED_TO_CLAIM,
                    f"{drafted}; {NAMES_OVERLAP} {claim.slug}, which had the article: joined"
                    f" to it {decided}",
                )
                session.flush()
                return Attached(claim, article, added=False)
        outlet = name_of(record.outlet)
        if outlet is None:
            return NotAttached(NO_NAME)
        refusals = self._outlet_refusals(session, record.outlet, now)
        if refusals is not None:
            return NotAttached(f"{OUTLET_REFUSES} for {refusals} pages and served none")
        with asking(session, record.outlet):
            page = self._ask_for_the_page(session, record, client, now)
        if isinstance(page, Deferred):
            return page
        if isinstance(page, _NoPage):
            return NotAttached(page.detail)
        dated = _date_and_headline(page)
        if isinstance(dated, _NoPage):
            return NotAttached(dated.detail)
        # The one model read, for the article's reported statements, as in any read.
        checker = client.make_checker(session)
        try:
            draft = read_article(client.make_llm(session), checker, page.text, purpose=LEAD_READING)
        except BudgetExceeded as ceiling:
            raise SpendCeilingReached(str(ceiling)) from None
        except CannotAsk:
            raise
        except LlmError as failure:
            return NotAttached(str(failure))
        try:
            article, statements, note = self._join(
                session, record, client, now, claim, draft, checker, page, outlet, dated
            )
        except EntryError as refused:
            session.flush()
            return NotAttached(str(refused))
        attached = f"{drafted}; {NAMES_OVERLAP} {claim.slug}: attached to it {decided}"
        self._finish(
            record, ReadOutcome.ADDED_TO_CLAIM, "; ".join(part for part in (attached, note) if part)
        )
        session.flush()
        return Attached(claim, article, added=True, statements=statements)


def _date_and_headline(retrieved: Retrieved) -> tuple[date, str] | _NoPage:
    """The publication day and the headline the page itself gives, or which one it lacks:
    an article is never dated or titled from anything else."""
    page = retrieved.page
    day = published_day(page.published if page else None)
    if day is None:
        return _NoPage(NO_DATE)
    headline = (page.headline or "").strip() if page else ""
    if not headline:
        return _NoPage(NO_HEADLINE)
    return day, headline
