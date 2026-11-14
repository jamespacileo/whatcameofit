"""The reading step: a passed link lead's article is read once and becomes a source
article of the claim it reports, or a new claim. Behavior: openspec lead-reading.

Everything that can be settled without the model is settled first: an article that has
become tracked, a claim that has enough articles, an outlet with no name, a page the
outlet does not let us fetch, a page with no date or headline. The article's text is held
only while the model reads it. What the read makes is an ordinary source article or an
ordinary claim, decided by the rules that govern any other.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, and_, exists, func, select
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key, without_tracking
from thenwhat.backfill.allowance import Allowances, outlet_source
from thenwhat.backfill.errors import BackfillError, SpendCeilingReached
from thenwhat.backfill.link_evaluation import reading_refusal
from thenwhat.backfill.link_screen import CLAIM, REGISTRY_TRIAL, TITLE_NAMES_CLAIM
from thenwhat.backfill.link_triage import is_passed
from thenwhat.backfill.outlet_kinds import name_of
from thenwhat.backfill.steps import MODEL, TEXT_DOOR, Failed, ModelSpend
from thenwhat.claims.entry import (
    EntryError,
    claim_by_slug,
    find_article,
    free_slug_for,
    slug_of_claim_covering,
)
from thenwhat.db.models import Claim, LinkLead, LinkLeadLink, LinkShare, SourceArticle
from thenwhat.decide.core import Backend, DecisionFailed
from thenwhat.decide.steps import choose_vertical, lead_ref
from thenwhat.domain import ReadOutcome, ScreenOutcome, WorkOutcome
from thenwhat.extract.page import published_day
from thenwhat.extract.retrieve import ArticleRetriever, PasteNeeded
from thenwhat.extract.service import article_from_draft, claim_from_draft, read_article
from thenwhat.llm.client import Llm
from thenwhat.llm.errors import BudgetExceeded, LlmError
from thenwhat.sources.base import SystemTime, Time
from thenwhat.statements.service import StatementChecker

NO_NAME = "its outlet has no display name"
NO_DATE = "the page gives no publication date"
NO_HEADLINE = "the page gives no headline"
REFUSED_BY_ROBOTS = "the outlet's robots.txt does not allow the fetch"
NO_PAGE = "the page could not be retrieved and no archived snapshot was found"
# The name a lead's read is recorded under in the usage ledger, apart from articles an
# operator has read, so the funnel can say what reading leads has cost.
LEAD_READING = "extraction:link_lead"


class NotMeasured(BackfillError):
    """No lead may be read yet: triage has not been measured, or a threshold is unset."""


@dataclass(slots=True)
class ReadClient:
    """What the reading step asks through: the outlet for the page, and the model for
    the read. The model's doors are made for the session at hand, because they record
    each call and its cost there."""

    retriever: ArticleRetriever
    allowances: Allowances
    make_llm: Callable[[Session], Llm]
    make_checker: Callable[[Session], StatementChecker]
    make_backend: Callable[[Session], Backend]
    requests_made: int = 0


class LinkRead:
    name = "link_read"
    version = 1
    record_kind = "link_lead"
    model = LinkLead
    source = MODEL
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
        time: Time | None = None,
    ) -> None:
        self.pass_above = pass_above
        self.reject_below = reject_below
        self.triage_version = triage_version
        self.min_labels = min_labels
        self.reads_per_claim = reads_per_claim
        self.vertical_accept_above = vertical_accept_above
        self.approve_drafts_by_rule = approve_drafts_by_rule
        self._time = time or SystemTime()

    # --- which leads, and in what order ---------------------------------------------

    def scope(self) -> ColumnElement[bool]:
        """Leads that screening left in scope and triage passed at the two thresholds.
        While either threshold is unset, none."""
        return and_(
            LinkLead.screen_outcome == ScreenOutcome.IN_SCOPE,
            is_passed(self.pass_above, self.reject_below),
        )

    def inputs(self, record: LinkLead) -> dict[str, Any]:
        return {"key": record.url_key}

    def order(self) -> list[ColumnElement[Any]]:
        """First the leads linked to a registry trial, then the most shared."""
        linked = exists().where(
            LinkLeadLink.link_lead_id == LinkLead.id,
            LinkLeadLink.record_kind == REGISTRY_TRIAL,
        )
        shared = (
            select(func.coalesce(func.sum(LinkShare.score), 0))
            .where(LinkShare.link_lead_id == LinkLead.id)
            .scalar_subquery()
        )
        return [linked.desc(), shared.desc()]

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

    def run(self, session: Session, record: LinkLead, client: ReadClient) -> WorkOutcome | Failed:
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

        # The outlet is asked: robots.txt first, then the page, a set interval apart.
        if not client.retriever.allowed(record.url):
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, REFUSED_BY_ROBOTS)
        client.allowances.claim(
            outlet_source(record.outlet),
            at_least_seconds=client.retriever.crawl_delay(record.url),
        )
        client.requests_made += 1
        try:
            retrieved = client.retriever.retrieve(record.url)
        except PasteNeeded:
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, NO_PAGE)
        page = retrieved.page
        day = published_day(page.published if page else None)
        if day is None:
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, NO_DATE)
        headline = (page.headline or "").strip() if page else ""
        if not headline:
            return self._finish(record, ReadOutcome.CANNOT_BE_READ, NO_HEADLINE)

        # The one model read. From here a failure is returned, not raised, so that the
        # call's cost and any logged decision stay recorded.
        checker = client.make_checker(session)
        try:
            draft = read_article(
                client.make_llm(session), checker, retrieved.text, purpose=LEAD_READING
            )
        except BudgetExceeded as ceiling:
            raise SpendCeilingReached(str(ceiling)) from None
        except LlmError as failure:
            return Failed(str(failure))
        address = without_tracking(record.url)
        try:
            existing = slug_of_claim_covering(session, draft.intervention, draft.indication)
            if existing is not None:
                claim = claim_by_slug(session, existing)
                article, _ = article_from_draft(
                    session,
                    checker,
                    claim,
                    draft,
                    text=retrieved.text,
                    url=address,
                    outlet=outlet,
                    title=headline,
                    published_date=day,
                    archive_url=retrieved.archive_url,
                    now=now,
                )
                record.claim_id, record.source_article_id = claim.id, article.id
                return self._finish(record, ReadOutcome.ADDED_TO_CLAIM)

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
                decide_by_rule_at=now if self.approve_drafts_by_rule else None,
                now=now,
            )
        except (EntryError, DecisionFailed) as refused:
            session.flush()
            return Failed(str(refused))
        article = find_article(session, extracted.claim, address)
        record.claim_id = extracted.claim.id
        record.source_article_id = article.id if article else None
        return self._finish(record, ReadOutcome.NEW_CLAIM)
